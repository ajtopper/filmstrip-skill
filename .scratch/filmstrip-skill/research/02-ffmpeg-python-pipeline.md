# Research: FFmpeg 9.0.2 + Python 3.15.2 Stdlib Zero-Dependency Pipeline

**Environment verified:**
- `ffmpeg version 9.0.2-full_build-www.gyan.dev` (`libavutil 61.1.102`, `libavcodec 63.1.102`, `libavformat 63.1.102`, `libavfilter 12.1.102`, `libswscale 10.1.102`)
- `Python 3.15.2` (standard library only; no `Pillow`, `numpy`, or `cv2`)
- Windows (PowerShell)

---

## 1. Frame Extraction & Scaling

### `-vsync` Removed — Use `-vf fps=<rate>` and `-fps_mode`
- **Local binary check (`ffmpeg -hide_banner ... -vsync 0`)**: `-vsync` has been removed in FFmpeg 9.0.2 and fails immediately with `Unrecognized option 'vsync' (Option not found)`.
- **Replacement (`ffmpeg -h long`, FFmpeg `ffmpeg-all` docs)**: `-fps_mode[:stream_spec]` replaces `-vsync` (`passthrough`, `cfr`, `vfr`, `auto`) at the output muxer layer.
- **Filter vs. output `-r` (`ffmpeg -h filter=fps`, `ffmpeg-all` docs, local `lavfi` test)**:
  - Placing `fps=<rate>` inside `-vf` / `-filter_complex` produces a strictly constant-framerate (CFR) stream inside the filtergraph before splitting or encoding.
  - On a `5.4s`, `30 fps` `testsrc2` input, `-vf "fps=1"` produced **5 frames** (`001`..`005`), whereas output `-r 1` produced **7 frames** (`001`..`007`) due to output-boundary timestamp rounding/duplication. On a `5s`, `30000/1001` (`29.97 fps`) input, `-vf "fps=1"` produced **5 frames**.
  - `fps` filter options (`ffmpeg -h filter=fps`): `fps` (default `"25"`), `start_time`, `round` (`zero`, `inf`, `down`, `up`, `near` [default]), `eof_action` (`round` [default], `pass`).

### JPEG Quality & `image2` Muxer Output
- **`-q:v` / `-qscale` (`ffmpeg -h full`, `ffmpeg -h encoder=mjpeg`)**: Fixed VBR quality scale for `mjpeg` (`2`–`31`, lower = higher quality; `-q:v 2` is standard near-visually-lossless JPEG quality).
- **`mjpeg` pixel format (`ffmpeg -h encoder=mjpeg`)**: Supports `yuvj420p`, `yuvj422p`, `yuvj444p`, `yuv420p`, `yuv422p`, `yuv444p`. In FFmpeg 9.0.2, encoding `yuv420p` input via `-vf fps=1` to `.jpeg` automatically selects `yuvj420p` / `yuv444p(pc, progressive)` with exit code `0` and no deprecation error.
- **`image2` sequence numbering (`ffmpeg -h muxer=image2`, `ffmpeg-formats` docs)**:
  - Default `-start_number` is `1`.
  - Pattern `<stem>-%03d.jpeg` writes `<stem>-001.jpeg`, `<stem>-002.jpeg`, ...; verified locally that when index reaches `>= 1000`, `image2` naturally expands to 4 digits (`seq-1000.jpeg`, `seq-1001.jpeg`) and `-start_number 1 -i "<stem>-%03d.jpeg"` reads sequences spanning `<1000` and `>=1000` back cleanly (`rc=0`).
  - Literal `%` in filenames/paths must be escaped as `%%` for `image2` (`ffmpeg-formats` docs).

### Scaling (`ffmpeg -h filter=scale`)
- Supports `force_original_aspect_ratio=decrease` (or `increase`), `force_divisible_by`, and `flags` passed to `libswscale` (`bicubic` default, `lanczos`, `area`, `neighbor`, `accurate_rnd`, etc.).
- For uniform grid tiles across arbitrary/portrait aspect ratios:
  ```text
  scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1
  ```
  Verified on `1080x1920` portrait `testsrc2` into `960x540` tiles + `tile=4x1` -> `3840x540` (`rc=0`).

---

## 2. 4-Column Grid Assembly (`tile` Filter)

### Filter Options (`ffmpeg -h filter=tile`, `ffmpeg-filters` docs)
- `layout <image_size>`: `COLUMNSxROWS` (e.g., `4x<rows>`; default `6x5`).
- `nb_frames <int>`: Max frames per output grid (`0`..`INT_MAX`, default `0` = all `cols * rows` cells).
- `margin <int>`: Outer border around entire grid in pixels (`0`..`1024`, default `0`).
- `padding <int>`: Inner gap between tiles in pixels (`0`..`1024`, default `0`).
- `color <color>`: Background color for margins, padding, and unused trailing cells (default `"black"`).

### Behavior Verified on `lavfi` Inputs
- **Incomplete final row**: `tile=4x3` fed 9 frames (`nb_frames=0`) renders 1 output grid image at EOF with the 3 unused trailing cells filled with `color` (`rc=0`).
- **Over-sized `rows` allocates blank rows**: Passing `tile=4x999` on 5 frames (`160x90`, `padding=0`, `margin=0`) allocated all 999 rows (outputting `640x89910` in PNG), rather than shrinking to `ceil(N / 4)` rows. Therefore `rows` **must** be computed from the actual frame count `N` as `ceil(N / 4)` (or `rows_per_sheet` when splitting).
- **Multi-sheet splitting**: Feeding 13 frames into `tile=4x2` (8 cells per sheet) with an `image2` output pattern (`sheet-%03d.jpg`) automatically emits `sheet-001.jpg` (8 frames) and `sheet-002.jpg` (5 frames + 3 trailing black cells) (`rc=0`).
- **Output dimensions formula**:
  - `width = 2 * margin + 4 * tile_w + 3 * padding`
  - `height = 2 * margin + rows * tile_h + (rows - 1) * padding`
  - Verified locally: `160x90`, `tile=4x3`, `padding=4`, `margin=8` -> `668x294` (`2*8 + 4*160 + 3*4 = 668`; `2*8 + 3*90 + 2*4 = 294`).

### Hard Pixel / Encoder Dimension Limits
- **FFmpeg `mjpeg` encoder limit (verified locally)**: FFmpeg's `mjpeg` encoder rejects any dimension above **`65500`** (even below the JPEG SOF0 16-bit container limit of `65535`):
  - `64x65536` JPEG -> fails (`rc != 0`)
  - `64x65535` JPEG -> fails (`rc != 0`)
  - `64x65520` JPEG -> fails (`rc != 0`)
  - `64x65500` JPEG -> succeeds (`rc=0`)
  - Exact stderr message observed: `[mjpeg @ ...] JPEG does not support resolutions above 65500x65500`.
- **`png` encoder**: `64x65536` PNG succeeds (`rc=0`); `640x89910` PNG (`tile=4x999`) also succeeds (`rc=0`), constrained only by RAM/time.
- **Architectural consequence**: Knowing `N` before running `tile` (via a 2-pass flow where Pass 1 extracts frames + computes average RGB, and Pass 2 runs `tile` from the extracted frames) lets Python compute exact `rows = ceil(N / 4)` and detect when `height > 65500` before invoking the JPEG encoder.

---

## 3. Average RGB Calculation & Barcode Rendering

### Computing Per-Frame Average RGB via `scale=1:1` + `rawvideo`
Tested on `640x360` and `1920x1080` synthetic frames (`half_red_blue`, `quarter_white`, `testsrc2`) against exact full-resolution `rgb24` pixel arithmetic means in Python:

| Filter Chain | `quarter_white_1920x1080` (true: `63.75, 63.75, 63.75`) | `testsrc2_1920x1080` (true: `123.91, 130.17, 125.11`) | Notes |
| --- | --- | --- | --- |
| `scale=1:1:flags=area,format=rgb24` | `(64, 61, 65)` | `(124, 132, 125)` | Downscales in YUV before RGB conversion; up to ~3 LSB chroma/rounding drift |
| `format=rgb24,scale=1:1:flags=area` | `(67, 59, 69)` | `(125, 131, 125)` | Default fixed-point rounding without `accurate_rnd` drifts up to ~5 LSB |
| **`format=rgb24,scale=1:1:flags=area+accurate_rnd`** | **`(64, 64, 64)`** | **`(124, 131, 125)`** | **Matches rounded true `rgb24` mean within <= 1 LSB** |

- **Why single-pass `split` beats decoding extracted JPEGs**:
  - Single-pass `-filter_complex "[0:v]fps=<rate>,split=2[v_frames][v_avg];[v_avg]format=rgb24,scale=1:1:flags=area+accurate_rnd[avg]"` decodes the source video **once**, writes `-map "[v_frames]"` JPEGs (`-q:v 2`), and streams `-map "[avg]" -f rawvideo -pix_fmt rgb24 pipe:1` directly to Python's `subprocess.run(..., capture_output=True).stdout`.
  - Avoids JPEG compression loss in the color averages, avoids spawning `N` decoders or writing a giant uncompressed `W*H*3*N` pipe to Python, and guarantees exact 1:1 correspondence between the `N` extracted frame files and the `N * 3` bytes received on `stdout` (`N = len(stdout) // 3`).

### Piping Barcode Bytes Back to `ffmpeg`
- Python packs the `N` `(R, G, B)` triples (`bytes` of length `3 * N`) and pipes them via `stdin` (`input=raw_bar`) into `ffmpeg`:
  ```text
  ffmpeg -hide_banner -y -f rawvideo -pix_fmt rgb24 -video_size {N}x1 -i pipe:0 \
    -vf "scale={W}:{H}:flags=neighbor" [-q:v 2] <barcode_output>
  ```
- **Verified locally**: Works cleanly for both `.png` and `.jpg` (`rc=0`).
- **Critical flag**: `flags=neighbor` (nearest-neighbor scaling) prevents `libswscale`'s default `bicubic` scaler from blurring adjacent 1px frame columns together. (For crisp un-blurred pixel stripes without chroma subsampling bleed, PNG is lossless; if JPEG is requested, note `mjpeg` chroma subsampling still applies at 2x2 block boundaries unless `yuv444p` / PNG is used.)

---

## 4. Windows & Python 3.15.2 Compatibility Caveats

1. **`-pattern_type glob` is NOT supported on Windows (`ffmpeg` 9.0.2 gyan.dev build)**:
   - Running `ffmpeg -pattern_type glob -i "frame-*.jpeg"` fails with:
     `Pattern type 'glob' was selected but globbing is not supported by this libavformat build` / `Error opening input file ...: Function not implemented` (`rc = -40`).
   - **Use `-pattern_type sequence` (default)** with `-start_number 1 -i "<dir>/<stem>-%03d.jpeg"`, OR **`-f concat -safe 0`** with a temporary UTF-8 list file when selecting subsets/sheets.
2. **`concat` demuxer path escaping on Windows**:
   - Verified locally with spaces and an apostrophe (`sub dir's/frame 001.jpeg`): converting backslashes to forward slashes and escaping single quotes (`p.replace("\\", "/").replace("'", "'\\''")`) inside `file '...'` lines succeeds with `rc=0`.
3. **Never use `shell=True` in `subprocess.run`**:
   - Avoids `cmd.exe` / PowerShell quoting and escaping issues (such as PowerShell stripping quotes or `cmd.exe`'s 8,192-character command line limit) and ensures argument lists pass directly to Win32 `CreateProcessW` (`docs.python.org/3/library/subprocess.html`).
4. **Windows `MAX_PATH` (260 chars) & extended-length `\\?\` prefix**:
   - Python 3.6+ supports long paths (`>260` chars) when Windows `LongPathsEnabled=1` is set (`docs.python.org/3/using/windows.html`), or via the Win32 extended-length prefix `\\?\` on normalized absolute paths with backslashes (note: `\\?\` disables forward-slash normalization, per Microsoft Win32 Naming Files documentation).
5. **Subprocess text encoding & CSV newlines on Windows**:
   - Always pass `encoding="utf-8", errors="replace"` when decoding `ffmpeg`/`ffprobe` stderr/stdout (Windows defaults to the local ANSI code page such as `cp1252`). Do **not** use `text=True` when reading `rawvideo` `rgb24` bytes from `pipe:1`.
   - When writing the CSV with Python's `csv.writer`, open with `newline="", encoding="utf-8"` so Windows `\r\n` translation does not insert blank lines between rows.

---

## Sources

- Local `ffmpeg version 9.0.2-full_build-www.gyan.dev` CLI help outputs: `ffmpeg -h filter=tile`, `ffmpeg -h filter=scale`, `ffmpeg -h filter=fps`, `ffmpeg -h muxer=image2`, `ffmpeg -h demuxer=image2`, `ffmpeg -h demuxer=concat`, `ffmpeg -h muxer=rawvideo`, `ffmpeg -h demuxer=rawvideo`, `ffmpeg -h encoder=mjpeg`, `ffmpeg -h encoder=png`, `ffmpeg -h long`.
- Local synthetic `lavfi` verification runs executed on Windows against `ffmpeg 9.0.2` and `Python 3.15.2` (temporary scratch files removed after verification).
- Official FFmpeg documentation: `ffmpeg-filters` (`tile`, `scale`, `fps`), `ffmpeg-formats` (`image2`, `concat`), `ffmpeg-all` (`-fps_mode`, `-r`).
- Python 3 `subprocess` & Windows documentation (`docs.python.org`) and Microsoft Win32 "Maximum Path Length Limitation" (`MAX_PATH` / `\\?\`).
