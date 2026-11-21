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


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


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
