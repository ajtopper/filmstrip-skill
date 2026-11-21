---
name: video-filmstrip
description: Extract video frames and generate a 4K 4-column filmstrip grid, average-color barcode image, and average RGB CSV using FFmpeg and Python.
disable-model-invocation: true
---

# Video Filmstrip

Generate an extracted-frame archive, a 4-column 4K filmstrip grid, an average-color barcode image, and an average RGB CSV from any video file using FFmpeg and the Python standard library (zero third-party packages required).

## Prerequisites

Confirm `ffmpeg`, `ffprobe`, and `python` are available on `PATH` before running:

```powershell
ffmpeg -version; ffprobe -version; python --version
```

## Steps

1. Resolve the input video path and confirm whether the user wants custom options (frame rate, output directory, prefix, start/duration trim, or custom dimensions).
2. Run [generate_filmstrip.py](./scripts/generate_filmstrip.py) with the input video path:

```powershell
python "<skill_dir>/scripts/generate_filmstrip.py" "<input_video>"
```

Pass optional flags only when overriding defaults:

- `--output-dir <dir>`: Destination directory (default: `<prefix>_filmstrip` next to the input video)
- `--prefix <name>`: Output filename prefix (default: input video stem)
- `--fps <rate>`: Frames per second to extract (default: `1.0`)
- `--cols <count>`: Grid column count (default: `4`)
- `--grid-width <px>`: Total grid width in pixels (default: `3840`)
- `--barcode-height <px>`: Average-color barcode height in pixels (default: `715`)
- `--barcode-stripe-width <px>`: Barcode width per frame in pixels (default: `1`)
- `--quality <2-31>`: FFmpeg MJPEG quality, lower is better (default: `2`)
- `--start <sec>`: Start offset in seconds (`-ss`)
- `--duration <sec>`: Clip duration in seconds (`-t`)

3. Verify the generated artifacts inside the output folder:
   - `frames/<prefix>-001.jpeg` ... (kept Extracted Frames at original video resolution)
   - `<prefix>_grid.jpeg` or numbered `<prefix>_grid-001.jpeg` ... (4-column Filmstrip Grid sheets, auto-split at FFmpeg's `65500px` JPEG height cap)
   - `<prefix>_averagesRGB.jpeg` (Average Color Barcode)
   - `<prefix>_averagesRGB.csv` (`frame,timestamp_sec,r,g,b` rows matching the extracted frame count)
4. Report the output directory and clickable links for the generated grid sheet(s), barcode, CSV, and frames folder.
