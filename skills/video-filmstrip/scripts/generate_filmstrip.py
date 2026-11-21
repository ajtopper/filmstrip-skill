#!/usr/bin/env python3
"""Generate Extracted Frames, 4-column Filmstrip Grid sheets, an Average Color Barcode, and an Average RGB CSV using FFmpeg."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

JPEG_MAX_DIMENSION = 65500
BADGE_FONT_SIZE = 16
BADGE_BASE_DIAMETER = 26
BADGE_EXTRA_DIGIT_PX = 8
BADGE_MARGIN = 10

_WINDOWS_FONT_NAMES = ("arialbd.ttf", "arial.ttf", "segoeui.ttf", "calibrib.ttf")
_POSIX_FONT_CANDIDATES = (
    Path("/System/Library/Fonts/Helvetica.ttc"),
    Path("/Library/Fonts/Arial.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
)


@dataclass(frozen=True)
class FilmstripConfig:
    """Validated configuration options for filmstrip generation."""

    output_dir: Path | None = None
    prefix: str | None = None
    fps: float = 1.0
    cols: int = 4
    grid_width: int = 3840
    barcode_height: int = 715
    barcode_stripe_width: int = 1
    quality: int = 2
    start: float | None = None
    duration: float | None = None

    def validate(self) -> None:
        """Validate configuration bounds and numeric finiteness."""
        if not math.isfinite(self.fps) or self.fps <= 0:
            raise ValueError("--fps must be a finite number greater than 0.")
        if self.cols < 1:
            raise ValueError("--cols must be at least 1.")
        if self.grid_width < self.cols * 2:
            raise ValueError("--grid-width must allow at least 2 pixels per column.")
        if self.grid_width % self.cols != 0:
            raise ValueError(
                f"--grid-width ({self.grid_width}) must be divisible by --cols ({self.cols})."
            )
        if self.barcode_height < 1:
            raise ValueError("--barcode-height must be at least 1.")
        if self.barcode_stripe_width < 1:
            raise ValueError("--barcode-stripe-width must be at least 1.")
        if not (2 <= self.quality <= 31):
            raise ValueError("--quality must be between 2 (best) and 31 (smallest).")
        if self.start is not None and (not math.isfinite(self.start) or self.start < 0):
            raise ValueError("--start must be a finite non-negative number.")
        if self.duration is not None and (
            not math.isfinite(self.duration) or self.duration <= 0
        ):
            raise ValueError("--duration must be a finite number greater than 0.")


@dataclass(frozen=True)
class GridGeometry:
    """Grid layout dimensions shared across sheet builders."""

    cols: int
    tile_width: int
    tile_height: int
    quality: int


@dataclass(frozen=True)
class FrameAverages:
    """Packed 8-bit RGB frame averages ordered by extracted frame index."""

    raw_rgb: bytes
    frame_count: int

    def iter_rgb(self):
        """Yield (frame_index_1based, r, g, b) tuples for every frame."""
        for idx in range(self.frame_count):
            offset = idx * 3
            yield idx + 1, self.raw_rgb[offset], self.raw_rgb[offset + 1], self.raw_rgb[offset + 2]


def _require_tool(name: str) -> None:
    """Verify that a required CLI binary is available on PATH."""
    if shutil.which(name) is None:
        raise RuntimeError(
            f"Required tool '{name}' was not found on PATH. Install FFmpeg and ensure '{name}' is accessible."
        )


def _run_subprocess(
    cmd: list[str],
    *,
    error_context: str,
    stdin_bytes: bytes | None = None,
) -> bytes:
    """Execute a CLI command without shell interpolation and return stdout bytes."""
    result = subprocess.run(cmd, input=stdin_bytes, capture_output=True)
    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"{error_context}: {stderr_text}")
    return result.stdout


def _escape_image2_pattern(path: Path) -> str:
    """Escape literal '%' characters for FFmpeg's image2 muxer/demuxer."""
    return str(path).replace("%", "%%")


def _concat_escape(path: Path) -> str:
    """Escape a filesystem path for FFmpeg's concat demuxer on Windows/POSIX."""
    return str(path).replace("\\", "/").replace("'", "'\\''")


def _filter_escape_path(path: Path) -> str:
    """Escape a filesystem path for FFmpeg filter option strings such as fontfile."""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def _badge_diameter_for_total_frames(total_frames: int) -> int:
    """Size the circular badge to fit the widest frame index at BADGE_FONT_SIZE."""
    digits = len(str(max(1, total_frames)))
    if digits <= 2:
        return BADGE_BASE_DIAMETER
    return BADGE_BASE_DIAMETER + (digits - 2) * BADGE_EXTRA_DIGIT_PX


def _find_sans_serif_font() -> Path | None:
    """Locate a reliable sans-serif TrueType/OpenType font across OSes."""
    if os.name == "nt":
        win_root = Path(os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows")
        fonts_dir = win_root / "Fonts"
        for font_name in _WINDOWS_FONT_NAMES:
            candidate = fonts_dir / font_name
            if candidate.is_file():
                return candidate

    fc_match = shutil.which("fc-match")
    if fc_match is not None:
        result = subprocess.run(
            [fc_match, "-f", "%{file}", "sans:bold"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode == 0:
            candidate = Path(result.stdout.strip())
            if candidate.is_file():
                return candidate

    for candidate in _POSIX_FONT_CANDIDATES:
        if candidate.is_file():
            return candidate
    return None


def _write_circle_badge_pam(pam_path: Path, diameter: int) -> None:
    """Write a white anti-aliased RGBA circular badge image in P7 PAM format."""
    radius = diameter / 2.0
    center = (diameter - 1) / 2.0
    pixels = bytearray(diameter * diameter * 4)
    pos = 0
    for y in range(diameter):
        dy = y - center
        for x in range(diameter):
            dx = x - center
            dist = math.hypot(dx, dy)
            alpha = max(0, min(255, round(255 * (radius - dist + 0.5))))
            pixels[pos] = 255
            pixels[pos + 1] = 255
            pixels[pos + 2] = 255
            pixels[pos + 3] = alpha
            pos += 4
    header = (
        f"P7\nWIDTH {diameter}\nHEIGHT {diameter}\nDEPTH 4\n"
        f"MAXVAL 255\nTUPLTYPE RGB_ALPHA\nENDHDR\n"
    ).encode("ascii")
    pam_path.write_bytes(header + pixels)


def _list_extracted_frames(frames_dir: Path, prefix: str) -> list[Path]:
    """List extracted frame files matching '<prefix>-<digits>.jpeg' without glob pitfalls."""
    if not frames_dir.is_dir():
        return []
    head = f"{prefix}-"
    matched: list[tuple[int, Path]] = []
    for entry in frames_dir.iterdir():
        if not entry.is_file() or entry.suffix != ".jpeg":
            continue
        stem = entry.stem
        if not stem.startswith(head):
            continue
        index_part = stem[len(head) :]
        if index_part.isdigit():
            matched.append((int(index_part), entry))
    matched.sort(key=lambda item: item[0])
    return [item[1] for item in matched]


def _probe_image_dimensions(image_path: Path) -> tuple[int, int]:
    """Return (width, height) of an image file via ffprobe."""
    stdout = _run_subprocess(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(image_path),
        ],
        error_context=f"ffprobe failed on {image_path}",
    )
    stream = json.loads(stdout.decode("utf-8", errors="replace"))["streams"][0]
    return int(stream["width"]), int(stream["height"])


def _even_tile_height(src_width: int, src_height: int, tile_width: int) -> int:
    """Compute an even tile height preserving the source aspect ratio."""
    raw_height = tile_width * src_height / src_width
    return max(2, round(raw_height / 2) * 2)


def _extract_frames_and_averages(
    video_path: Path,
    frames_dir: Path,
    prefix: str,
    config: FilmstripConfig,
) -> tuple[list[Path], FrameAverages]:
    """Extract JPEG frames and compute 1x1 rgb24 averages in a single FFmpeg pass."""
    frames_dir.mkdir(parents=True, exist_ok=True)
    for existing in _list_extracted_frames(frames_dir, prefix):
        existing.unlink()

    output_pattern = f"{_escape_image2_pattern(frames_dir / prefix)}-%03d.jpeg"
    filter_complex = (
        f"[0:v]fps={config.fps},split=2[v_frames][v_avg];"
        f"[v_avg]format=rgb24,scale=1:1:flags=area+accurate_rnd[avg]"
    )
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    if config.start is not None:
        cmd.extend(["-ss", str(config.start)])
    if config.duration is not None:
        cmd.extend(["-t", str(config.duration)])
    cmd.extend(
        [
            "-i",
            str(video_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v_frames]",
            "-q:v",
            str(config.quality),
            output_pattern,
            "-map",
            "[avg]",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ]
    )
    result = subprocess.run(cmd, input=None, capture_output=True)
    if result.returncode != 0:
        stderr_text = result.stderr.decode("utf-8", errors="replace").strip()
        if "received no packets" in stderr_text.lower():
            raise RuntimeError(
                f"No frames were extracted from {video_path} (check --start, --duration, or input video)."
            )
        raise RuntimeError(f"FFmpeg frame extraction failed: {stderr_text}")

    frames = _list_extracted_frames(frames_dir, prefix)
    if not frames:
        raise RuntimeError(f"No frames were extracted from {video_path}.")
    raw_rgb = result.stdout
    if len(raw_rgb) != 3 * len(frames):
        raise RuntimeError(
            f"RGB byte stream length ({len(raw_rgb)}) does not match extracted frame count ({len(frames)})."
        )
    return frames, FrameAverages(raw_rgb=raw_rgb, frame_count=len(frames))


def _build_grid_sheet(
    sheet_frames: list[Path],
    geometry: GridGeometry,
    output_path: Path,
    *,
    start_frame_number: int = 1,
    badge_diameter: int = BADGE_BASE_DIAMETER,
) -> None:
    """Assemble sheet_frames into a single Filmstrip Grid sheet with Frame Badges."""
    min_tile_size = badge_diameter + 2 * BADGE_MARGIN
    if geometry.tile_width < min_tile_size or geometry.tile_height < min_tile_size:
        raise ValueError(
            f"Tile size ({geometry.tile_width}x{geometry.tile_height}px) is too small "
            f"for a {badge_diameter}px Frame Badge (minimum {min_tile_size}x{min_tile_size}px)."
        )

    rows = math.ceil(len(sheet_frames) / geometry.cols)
    font_path = _find_sans_serif_font()
    font_opt = f"fontfile='{_filter_escape_path(font_path)}':" if font_path else ""
    filter_complex = (
        f"[0:v]scale={geometry.tile_width}:{geometry.tile_height}:force_original_aspect_ratio=decrease,"
        f"pad={geometry.tile_width}:{geometry.tile_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1[tile_base];"
        f"[tile_base][1:v]overlay=x={BADGE_MARGIN}:y=H-h-{BADGE_MARGIN}:eof_action=repeat,"
        f"drawtext={font_opt}text='%{{eif\\:n+{start_frame_number}\\:d}}':"
        f"fontsize={BADGE_FONT_SIZE}:fontcolor=black:"
        f"x={BADGE_MARGIN}+({badge_diameter}-tw)/2:"
        f"y=h-{BADGE_MARGIN}-{badge_diameter}+({badge_diameter}-th)/2,"
        f"tile={geometry.cols}x{rows}:color=black[out]"
    )
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        concat_file = tmp_path / "frames.txt"
        lines = [f"file '{_concat_escape(frame)}'\n" for frame in sheet_frames]
        concat_file.write_text("".join(lines), encoding="utf-8")

        badge_pam = tmp_path / "badge.pam"
        _write_circle_badge_pam(badge_pam, badge_diameter)

        _run_subprocess(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_file),
                "-i",
                str(badge_pam),
                "-filter_complex",
                filter_complex,
                "-map",
                "[out]",
                "-q:v",
                str(geometry.quality),
                str(output_path),
            ],
            error_context="FFmpeg grid assembly failed",
        )


def _write_grid_sheets(
    frames: list[Path],
    out_dir: Path,
    prefix: str,
    geometry: GridGeometry,
) -> list[Path]:
    """Write one Grid Sheet or split into numbered Grid Sheets below JPEG_MAX_DIMENSION."""
    if geometry.tile_height > JPEG_MAX_DIMENSION:
        raise ValueError(
            f"Single tile height ({geometry.tile_height}px) exceeds JPEG limit ({JPEG_MAX_DIMENSION}px)."
        )

    max_rows_per_sheet = JPEG_MAX_DIMENSION // geometry.tile_height
    total_rows = math.ceil(len(frames) / geometry.cols)
    badge_diameter = _badge_diameter_for_total_frames(len(frames))

    single_grid = out_dir / f"{prefix}_grid.jpeg"
    if single_grid.is_file():
        single_grid.unlink()
    head = f"{prefix}_grid-"
    for entry in out_dir.iterdir():
        if entry.is_file() and entry.suffix == ".jpeg" and entry.stem.startswith(head):
            entry.unlink()

    if total_rows <= max_rows_per_sheet:
        _build_grid_sheet(
            sheet_frames=frames,
            geometry=geometry,
            output_path=single_grid,
            badge_diameter=badge_diameter,
        )
        return [single_grid]

    frames_per_sheet = geometry.cols * max_rows_per_sheet
    sheets: list[Path] = []
    for idx in range(0, len(frames), frames_per_sheet):
        sheet_num = idx // frames_per_sheet + 1
        sheet_path = out_dir / f"{prefix}_grid-{sheet_num:03d}.jpeg"
        _build_grid_sheet(
            sheet_frames=frames[idx : idx + frames_per_sheet],
            geometry=geometry,
            output_path=sheet_path,
            start_frame_number=idx + 1,
            badge_diameter=badge_diameter,
        )
        sheets.append(sheet_path)
    return sheets


def _write_averages_csv(
    averages: FrameAverages,
    fps: float,
    start_offset: float,
    csv_path: Path,
) -> None:
    """Write per-frame average RGB values to an Average RGB CSV."""
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["frame", "timestamp_sec", "r", "g", "b"])
        for frame_num, r, g, b in averages.iter_rgb():
            timestamp_sec = round(start_offset + (frame_num - 1) / fps, 3)
            writer.writerow([frame_num, timestamp_sec, r, g, b])


def _write_barcode_image(
    averages: FrameAverages,
    config: FilmstripConfig,
    barcode_path: Path,
) -> None:
    """Render the Average Color Barcode JPEG from packed rgb24 frame averages."""
    out_width = averages.frame_count * config.barcode_stripe_width
    if out_width > JPEG_MAX_DIMENSION or config.barcode_height > JPEG_MAX_DIMENSION:
        raise ValueError(
            f"Barcode dimensions ({out_width}x{config.barcode_height}) exceed JPEG limit ({JPEG_MAX_DIMENSION}px)."
        )
    _run_subprocess(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-video_size",
            f"{averages.frame_count}x1",
            "-i",
            "pipe:0",
            "-vf",
            f"scale={out_width}:{config.barcode_height}:flags=neighbor",
            "-q:v",
            str(config.quality),
            str(barcode_path),
        ],
        error_context="FFmpeg barcode rendering failed",
        stdin_bytes=averages.raw_rgb,
    )


def generate_filmstrip(video_path: Path, config: FilmstripConfig | None = None) -> Path:
    """Run the filmstrip generation pipeline for video_path."""
    cfg = config or FilmstripConfig()
    cfg.validate()
    _require_tool("ffmpeg")
    _require_tool("ffprobe")
    if not video_path.is_file():
        raise FileNotFoundError(f"Input video not found: {video_path}")

    effective_prefix = cfg.prefix or video_path.stem
    out_dir = (
        cfg.output_dir
        if cfg.output_dir is not None
        else video_path.parent / f"{effective_prefix}_filmstrip"
    )
    frames_dir = out_dir / "frames"

    frames, averages = _extract_frames_and_averages(
        video_path, frames_dir, effective_prefix, cfg
    )
    if not frames:
        raise RuntimeError(f"No frames were extracted from {video_path}")

    src_w, src_h = _probe_image_dimensions(frames[0])
    tile_w = cfg.grid_width // cfg.cols
    geometry = GridGeometry(
        cols=cfg.cols,
        tile_width=tile_w,
        tile_height=_even_tile_height(src_w, src_h, tile_w),
        quality=cfg.quality,
    )

    _write_grid_sheets(
        frames=frames,
        out_dir=out_dir,
        prefix=effective_prefix,
        geometry=geometry,
    )
    _write_averages_csv(
        averages=averages,
        fps=cfg.fps,
        start_offset=cfg.start or 0.0,
        csv_path=out_dir / f"{effective_prefix}_averagesRGB.csv",
    )
    _write_barcode_image(
        averages=averages,
        config=cfg,
        barcode_path=out_dir / f"{effective_prefix}_averagesRGB.jpeg",
    )
    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Extract video frames and generate a 4-column filmstrip grid, "
            "an average-color barcode image, and an average RGB CSV."
        )
    )
    parser.add_argument("input_video", type=Path, help="Path to the input video file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Destination folder (default: <prefix>_filmstrip next to input video).",
    )
    parser.add_argument(
        "--prefix",
        type=str,
        default=None,
        help="Filename prefix for outputs (default: input video stem).",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="Frames per second to extract (default: 1.0).",
    )
    parser.add_argument(
        "--cols",
        type=int,
        default=4,
        help="Number of columns in the filmstrip grid (default: 4).",
    )
    parser.add_argument(
        "--grid-width",
        type=int,
        default=3840,
        help="Total width in pixels of the filmstrip grid (default: 3840).",
    )
    parser.add_argument(
        "--barcode-height",
        type=int,
        default=715,
        help="Height in pixels of the average-color barcode image (default: 715).",
    )
    parser.add_argument(
        "--barcode-stripe-width",
        type=int,
        default=1,
        help="Width in pixels per frame stripe in the barcode (default: 1).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=2,
        help="FFmpeg MJPEG quality scale 2-31, lower is higher quality (default: 2).",
    )
    parser.add_argument(
        "--start",
        type=float,
        default=None,
        help="Start offset in seconds (-ss equivalent).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Clip duration in seconds (-t equivalent).",
    )
    args = parser.parse_args(argv)
    config = FilmstripConfig(
        output_dir=args.output_dir.resolve() if args.output_dir is not None else None,
        prefix=args.prefix,
        fps=args.fps,
        cols=args.cols,
        grid_width=args.grid_width,
        barcode_height=args.barcode_height,
        barcode_stripe_width=args.barcode_stripe_width,
        quality=args.quality,
        start=args.start,
        duration=args.duration,
    )
    try:
        out_dir = generate_filmstrip(args.input_video.resolve(), config=config)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Filmstrip outputs written to: {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
