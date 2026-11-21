import csv
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = (
    REPO_ROOT / "skills" / "video-filmstrip" / "scripts" / "generate_filmstrip.py"
)

_SPEC = importlib.util.spec_from_file_location("generate_filmstrip", SCRIPT_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules["generate_filmstrip"] = _MODULE
_SPEC.loader.exec_module(_MODULE)
probe_image_size = _MODULE._probe_image_dimensions


def create_synthetic_video(
    output_path: Path,
    *,
    duration_sec: float,
    width: int,
    height: int,
    fps: int = 30,
    source: str = "testsrc2",
) -> None:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"{source}=size={width}x{height}:rate={fps}:duration={duration_sec}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def create_lossless_black_video(
    output_path: Path,
    *,
    duration_sec: float,
    width: int,
    height: int,
    fps: int = 10,
) -> None:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"color=c=#000000:s={width}x{height}:r={fps}:duration={duration_sec},format=rgb24",
        "-c:v",
        "ffv1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def sample_rgb_region(
    image_path: Path, x: int, y: int, width: int, height: int
) -> list[tuple[int, int, int]]:
    """Read raw RGB24 pixel triples from a rectangular region of an image via FFmpeg."""
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(image_path),
        "-vf",
        f"crop={width}:{height}:{x}:{y},format=rgb24",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "pipe:1",
    ]
    res = subprocess.run(cmd, check=True, capture_output=True)
    raw = res.stdout
    return [(raw[i], raw[i + 1], raw[i + 2]) for i in range(0, len(raw), 3)]


class FilmstripExtractionAndGridTests(unittest.TestCase):
    def test_extracts_frames_and_builds_4k_4col_grid_with_partial_final_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "sample_clip.mp4"
            create_synthetic_video(video, duration_sec=5.0, width=1280, height=720)

            res = run_cli(str(video))
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            out_dir = tmp_dir / "sample_clip_filmstrip"
            frames_dir = out_dir / "frames"
            frames = sorted(frames_dir.glob("sample_clip-*.jpeg"))
            self.assertEqual(len(frames), 5)
            self.assertEqual(
                [p.name for p in frames],
                [f"sample_clip-{i:03d}.jpeg" for i in range(1, 6)],
            )
            self.assertEqual(probe_image_size(frames[0]), (1280, 720))

            grid_path = out_dir / "sample_clip_grid.jpeg"
            self.assertTrue(grid_path.is_file(), "Expected single grid sheet")
            # 5 frames -> 2 rows x 4 cols; each 16:9 tile is 960x540 -> 3840x1080
            self.assertEqual(probe_image_size(grid_path), (3840, 1080))

    def test_handles_portrait_aspect_ratio_and_fewer_than_four_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "portrait.mp4"
            create_synthetic_video(video, duration_sec=3.0, width=720, height=1280)

            res = run_cli(str(video))
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            out_dir = tmp_dir / "portrait_filmstrip"
            frames = sorted((out_dir / "frames").glob("portrait-*.jpeg"))
            self.assertEqual(len(frames), 3)
            self.assertEqual(probe_image_size(frames[0]), (720, 1280))

            grid_path = out_dir / "portrait_grid.jpeg"
            self.assertTrue(grid_path.is_file())
            grid_w, grid_h = probe_image_size(grid_path)
            self.assertEqual(grid_w, 3840)
            # 960 * 1280 / 720 = 1706.67 -> single row, even tile height 1706 or 1708
            self.assertIn(grid_h, (1706, 1708))


class FrameBadgeTests(unittest.TestCase):
    def test_renders_bottom_left_white_circle_black_text_badge_on_populated_tiles_only(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "dark_five.mkv"
            create_lossless_black_video(video, duration_sec=5.0, width=320, height=180)

            res = run_cli(str(video))
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            out_dir = tmp_dir / "dark_five_filmstrip"
            grid_path = out_dir / "dark_five_grid.jpeg"
            self.assertTrue(grid_path.is_file())
            self.assertEqual(probe_image_size(grid_path), (3840, 1080))

            # Tile 1 (col 0, row 0): bottom-left corner region (0..44, 496..540)
            tile1_badge = sample_rgb_region(grid_path, x=0, y=540 - 44, width=44, height=44)
            bright_pixels = [p for p in tile1_badge if p[0] > 220 and p[1] > 220 and p[2] > 220]
            self.assertGreater(
                len(bright_pixels), 150, "Expected white circular badge in tile 1 bottom-left"
            )
            # Check inner circle center region has dark glyph pixels ('1') surrounded by white
            tile1_inner = sample_rgb_region(grid_path, x=14, y=540 - 30, width=16, height=16)
            inner_dark = [p for p in tile1_inner if p[0] < 60 and p[1] < 60 and p[2] < 60]
            inner_bright = [p for p in tile1_inner if p[0] > 220 and p[1] > 220 and p[2] > 220]
            self.assertGreater(len(inner_dark), 10, "Expected black 16px digit inside white circle")
            self.assertGreater(len(inner_bright), 40, "Expected white circle background around digit")

            # Tile 5 (col 0, row 1): bottom-left corner region (0..44, 1080-44..1080)
            tile5_badge = sample_rgb_region(grid_path, x=0, y=1080 - 44, width=44, height=44)
            self.assertGreater(
                len([p for p in tile5_badge if p[0] > 220 and p[1] > 220 and p[2] > 220]),
                150,
                "Expected badge on 5th tile",
            )

            # Unused trailing cell (col 1, row 1: x=960..1004, y=1080-44..1080) must stay black
            empty_cell = sample_rgb_region(grid_path, x=960, y=1080 - 44, width=44, height=44)
            self.assertTrue(
                all(p[0] < 15 and p[1] < 15 and p[2] < 15 for p in empty_cell),
                "Unused trailing cell must remain plain black with no badge",
            )

            # Kept Extracted Frame 1 must remain unbadged (plain black at bottom-left)
            raw_frame_1 = out_dir / "frames" / "dark_five-001.jpeg"
            frame1_bl = sample_rgb_region(raw_frame_1, x=0, y=180 - 44, width=44, height=44)
            self.assertTrue(
                all(p[0] < 15 and p[1] < 15 and p[2] < 15 for p in frame1_bl),
                "Kept Extracted Frames must remain unbadged",
            )

            # Average RGB CSV and Average Color Barcode must stay pure black unaffected by white badge
            with (out_dir / "dark_five_averagesRGB.csv").open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(rows[1][2:], ["0", "0", "0"])

            barcode_pixels = sample_rgb_region(
                out_dir / "dark_five_averagesRGB.jpeg", x=0, y=0, width=5, height=715
            )
            self.assertTrue(
                all(p[0] < 15 and p[1] < 15 and p[2] < 15 for p in barcode_pixels),
                "Average Color Barcode must remain pure black unaffected by Frame Badges",
            )

    def test_continues_badge_numbering_across_multi_sheet_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "tall_dark.mkv"
            # 120x2700 -> tile_h = 21600 -> 12 frames/sheet. 13s -> sheet 1 (1..12), sheet 2 (13).
            create_lossless_black_video(
                video, duration_sec=13.0, width=120, height=2700, fps=2
            )

            res = run_cli(str(video))
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            out_dir = tmp_dir / "tall_dark_filmstrip"
            sheet1 = out_dir / "tall_dark_grid-001.jpeg"
            sheet2 = out_dir / "tall_dark_grid-002.jpeg"
            self.assertTrue(sheet1.is_file())
            self.assertTrue(sheet2.is_file())

            # Compare inner badge pixels of tile 1 ('1') vs sheet 2 tile 1 ('13')
            sheet1_badge_inner = sample_rgb_region(sheet1, x=14, y=21600 - 32, width=18, height=18)
            sheet2_badge_inner = sample_rgb_region(sheet2, x=14, y=21600 - 32, width=18, height=18)
            self.assertGreater(
                len([p for p in sheet2_badge_inner if p[0] > 220 and p[1] > 220 and p[2] > 220]),
                50,
                "Expected badge on sheet 2 tile 1",
            )
            diffs = sum(
                1 for a, b in zip(sheet1_badge_inner, sheet2_badge_inner) if abs(a[0] - b[0]) > 60
            )
            self.assertGreater(diffs, 15, "Sheet 2 tile 1 ('13') must differ from sheet 1 tile 1 ('1')")

            # Sheet 2 unused col 1 must stay black
            sheet2_empty_cell = sample_rgb_region(sheet2, x=960, y=21600 - 44, width=44, height=44)
            self.assertTrue(all(p[0] < 15 and p[1] < 15 and p[2] < 15 for p in sheet2_empty_cell))

    def test_fits_three_digit_frame_numbers_inside_white_circle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "hundred_plus.mkv"
            create_lossless_black_video(
                video, duration_sec=1.05, width=160, height=90, fps=100
            )

            res = run_cli(str(video), "--fps", "100", "--grid-width", "640")
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            grid_path = tmp_dir / "hundred_plus_filmstrip" / "hundred_plus_grid.jpeg"
            # Frame 105 is at index 104 -> row 26 (0-based), col 0; tile size 160x90
            tile_y_bottom = 27 * 90
            badge_region = sample_rgb_region(
                grid_path, x=10, y=tile_y_bottom - 44, width=36, height=34
            )
            bright_count = sum(1 for p in badge_region if p[0] > 220 and p[1] > 220 and p[2] > 220)
            self.assertGreater(
                bright_count,
                550,
                f"Expected expanded white circle for 3-digit badge ('105'), got {bright_count} bright pixels",
            )

    def test_custom_cols_and_trim_keep_badges_aligned_to_populated_tiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "trimmed.mkv"
            create_lossless_black_video(video, duration_sec=5.0, width=320, height=180)

            res = run_cli(
                str(video), "--cols", "2", "--grid-width", "640", "--start", "1", "--duration", "3"
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            grid_path = tmp_dir / "trimmed_filmstrip" / "trimmed_grid.jpeg"
            # 3 frames in 2 cols -> 2 rows of 320x180 tiles (640x360 total); col 1 row 1 is empty
            self.assertEqual(probe_image_size(grid_path), (640, 360))
            tile3_badge = sample_rgb_region(grid_path, x=0, y=360 - 44, width=44, height=44)
            self.assertGreater(
                len([p for p in tile3_badge if p[0] > 220 and p[1] > 220 and p[2] > 220]),
                150,
            )
            empty_cell = sample_rgb_region(grid_path, x=320, y=360 - 44, width=44, height=44)
            self.assertTrue(all(p[0] < 15 and p[1] < 15 and p[2] < 15 for p in empty_cell))


class MultiSheetGridTests(unittest.TestCase):
    def test_splits_into_numbered_grid_sheets_when_height_exceeds_jpeg_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "tall_long.mp4"
            # 120x2700 -> at 960px tile width, tile_h = 21600px.
            # max_rows_per_sheet = 65500 // 21600 = 3 rows (12 frames).
            # 13s at 1fps -> 13 frames -> sheet 1 (12 frames, 3 rows = 64800px), sheet 2 (1 frame, 1 row = 21600px).
            create_synthetic_video(
                video, duration_sec=13.0, width=120, height=2700, fps=5
            )

            res = run_cli(str(video))
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            out_dir = tmp_dir / "tall_long_filmstrip"
            self.assertFalse((out_dir / "tall_long_grid.jpeg").exists())

            sheets = sorted(out_dir.glob("tall_long_grid-*.jpeg"))
            self.assertEqual(
                [p.name for p in sheets],
                ["tall_long_grid-001.jpeg", "tall_long_grid-002.jpeg"],
            )
            self.assertEqual(probe_image_size(sheets[0]), (3840, 64800))
            self.assertEqual(probe_image_size(sheets[1]), (3840, 21600))


class AverageColorBarcodeTests(unittest.TestCase):
    def test_generates_average_rgb_csv_and_barcode_for_solid_and_split_frames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "color_bars.mkv"
            # Lossless rgb24 ffv1 video:
            # Frame 1: solid red (255, 0, 0)
            # Frame 2: solid green (0, 255, 0)
            # Frame 3: spatially split half red + half blue -> mean (128, 0, 128)
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "color=c=#FF0000:s=160x90:r=10:d=1,format=rgb24",
                "-f",
                "lavfi",
                "-i",
                "color=c=#00FF00:s=160x90:r=10:d=1,format=rgb24",
                "-f",
                "lavfi",
                "-i",
                "color=c=#FF0000:s=80x90:r=10:d=1,format=rgb24",
                "-f",
                "lavfi",
                "-i",
                "color=c=#0000FF:s=80x90:r=10:d=1,format=rgb24",
                "-filter_complex",
                "[2:v][3:v]hstack=inputs=2[split_rb];"
                "[0:v][1:v][split_rb]concat=n=3:v=1:a=0[v]",
                "-map",
                "[v]",
                "-c:v",
                "ffv1",
                str(video),
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)

            res = run_cli(str(video))
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            out_dir = tmp_dir / "color_bars_filmstrip"
            csv_path = out_dir / "color_bars_averagesRGB.csv"
            barcode_path = out_dir / "color_bars_averagesRGB.jpeg"
            self.assertTrue(csv_path.is_file())
            self.assertTrue(barcode_path.is_file())
            self.assertEqual(probe_image_size(barcode_path), (3, 715))

            with csv_path.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))

            self.assertEqual(rows[0], ["frame", "timestamp_sec", "r", "g", "b"])
            self.assertEqual(len(rows), 4)
            expected = [
                (1, 0.0, (255, 0, 0)),
                (2, 1.0, (0, 255, 0)),
                (3, 2.0, (128, 0, 128)),
            ]
            for row, (exp_frame, exp_ts, exp_rgb) in zip(rows[1:], expected):
                self.assertEqual(int(row[0]), exp_frame)
                self.assertAlmostEqual(float(row[1]), exp_ts, places=3)
                actual_rgb = (int(row[2]), int(row[3]), int(row[4]))
                for a, e in zip(actual_rgb, exp_rgb):
                    self.assertLessEqual(
                        abs(a - e), 1, msg=f"got {actual_rgb}, expected {exp_rgb}"
                    )


class CliOptionsAndErrorHandlingTests(unittest.TestCase):
    def test_custom_cli_flags_trim_dimensions_and_output_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            video = tmp_dir / "source.mp4"
            create_synthetic_video(video, duration_sec=5.0, width=1280, height=720)
            custom_out = tmp_dir / "custom_out"

            res = run_cli(
                str(video),
                "--output-dir",
                str(custom_out),
                "--prefix",
                "s01e02",
                "--fps",
                "2",
                "--cols",
                "2",
                "--grid-width",
                "1920",
                "--barcode-height",
                "200",
                "--barcode-stripe-width",
                "4",
                "--quality",
                "5",
                "--start",
                "1",
                "--duration",
                "2",
            )
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            frames = sorted((custom_out / "frames").glob("s01e02-*.jpeg"))
            self.assertEqual(len(frames), 4)
            self.assertEqual(probe_image_size(custom_out / "s01e02_grid.jpeg"), (1920, 1080))
            self.assertEqual(probe_image_size(custom_out / "s01e02_averagesRGB.jpeg"), (16, 200))

            with (custom_out / "s01e02_averagesRGB.csv").open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
            self.assertEqual(len(rows), 5)
            self.assertEqual([float(r[1]) for r in rows[1:]], [1.0, 1.5, 2.0, 2.5])

    def test_handles_paths_with_spaces_apostrophes_and_brackets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            tricky_dir = tmp_dir / "sub dir's"
            tricky_dir.mkdir()
            video = tricky_dir / "my clip's [1080p].mp4"
            create_synthetic_video(video, duration_sec=5.0, width=640, height=360)

            res = run_cli(str(video))
            self.assertEqual(res.returncode, 0, msg=res.stderr)

            out_dir = tricky_dir / "my clip's [1080p]_filmstrip"
            self.assertTrue((out_dir / "my clip's [1080p]_grid.jpeg").is_file())
            self.assertTrue((out_dir / "my clip's [1080p]_averagesRGB.jpeg").is_file())
            self.assertTrue((out_dir / "my clip's [1080p]_averagesRGB.csv").is_file())

    def test_error_handling_for_missing_video_zero_frames_invalid_flags_and_missing_ffmpeg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            missing = tmp_dir / "does_not_exist.mp4"
            res_missing = run_cli(str(missing))
            self.assertNotEqual(res_missing.returncode, 0)
            self.assertIn("not found", res_missing.stderr.lower())

            video = tmp_dir / "ok.mp4"
            create_synthetic_video(video, duration_sec=2.0, width=320, height=180)

            res_zero = run_cli(str(video), "--start", "99")
            self.assertNotEqual(res_zero.returncode, 0)
            self.assertIn("no frames", res_zero.stderr.lower())

            for bad_args in (
                ["--fps", "0"],
                ["--fps", "nan"],
                ["--cols", "0"],
                ["--grid-width", "2"],
                ["--grid-width", "1001", "--cols", "4"],
                ["--barcode-height", "0"],
                ["--barcode-stripe-width", "0"],
                ["--quality", "40"],
                ["--start", "-1"],
                ["--start", "nan"],
                ["--duration", "0"],
                ["--duration", "inf"],
            ):
                res_bad = run_cli(str(video), *bad_args)
                self.assertNotEqual(res_bad.returncode, 0, msg=f"Expected failure for {bad_args}")

            empty_path_env = {k: v for k, v in os.environ.items() if k.upper() != "PATH"}
            empty_path_env["PATH"] = ""
            res_no_ffmpeg = run_cli(str(video), env=empty_path_env)
            self.assertNotEqual(res_no_ffmpeg.returncode, 0)
            self.assertIn("ffmpeg", res_no_ffmpeg.stderr.lower())


if __name__ == "__main__":
    unittest.main()
