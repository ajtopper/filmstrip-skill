# FFmpeg + Python Stdlib Pipeline Research

Type: `research`
Status: `resolved`

## Question

Investigate primary documentation and local FFmpeg 9.0.2 / Python 3.15.2 capabilities to verify the cleanest zero-dependency pipeline (no Pillow/NumPy/OpenCV):

1. **Frame extraction & scaling**: Exact `ffmpeg` flags for extracting frames at `fps` (default `1`) into a subfolder (`-vsync`/`-fps_mode`, JPEG quality `-q:v`, scaling filters).
2. **4-column grid assembly**: Can `ffmpeg`'s `tile=4x<rows>` filter (with `padding` / `margin` or `color` background for incomplete last row) build the 4-column grid directly from extracted frames or a single-pass filtergraph, and what are its exact pixel/dimension limits?
3. **Average RGB calculation & barcode image**: How accurately and fast can `ffmpeg` compute per-frame average RGB (e.g., `scale=1:1:flags=area` + `-f rawvideo -pix_fmt rgb24` piped to Python stdout) compared to reading extracted JPEGs, and can Python pipe raw `rgb24` / PPM bytes back into `ffmpeg` to encode the final barcode JPEG/PNG?
4. **Windows compatibility**: Any quoting, globbing (`image2` `%03d` vs `concat` demuxer), or path-length caveats on Windows PowerShell.

## Answer

Verified against local `ffmpeg 9.0.2` (`gyan.dev` full build), `Python 3.15.2`, and official FFmpeg/Python/Win32 documentation. See [../research/02-ffmpeg-python-pipeline.md](../research/02-ffmpeg-python-pipeline.md) for full details and primary-source citations.

Summary of the verified zero-dependency pipeline:
1. **Frame extraction & average RGB in one decode pass**: `-vsync` is removed in FFmpeg 9.0.2 (`-fps_mode` replaces it), and filtergraph `fps=<rate>` is more deterministic than output `-r`. Use `-filter_complex "[0:v]fps=<rate>,split=2[v_frames][v_avg];[v_avg]format=rgb24,scale=1:1:flags=area+accurate_rnd[avg]"` to write `-q:v 2` JPEGs (`<stem>-%03d.jpeg`, which naturally expands past `999`) while streaming exact 3-byte-per-frame `rgb24` averages (`<= 1 LSB` error vs full-res mean) to `pipe:1`.
2. **4-column grid assembly (`tile`)**: `tile=4x<rows>` pre-allocates all specified rows (an over-sized `rows` renders blank trailing rows), so a second pass from the extracted frames should compute exact `rows = ceil(N / 4)` and use `scale=W:H:force_original_aspect_ratio=decrease,pad=W:H:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1`. FFmpeg's `mjpeg` encoder enforces a hard **`65500x65500`** maximum resolution (`65520`/`65535` fail), whereas `png` exceeds 65,535px. Multi-sheet splitting works automatically when `tile=4x<rows_per_sheet>` outputs to an `image2` sequence (`grid-%03d.jpg`).
3. **Barcode image generation**: Pipe the `N * 3` `rgb24` bytes from Python back into `ffmpeg` via `stdin` (`-f rawvideo -pix_fmt rgb24 -video_size {N}x1 -i pipe:0 -vf "scale={W}:{H}:flags=neighbor"`), preventing `bicubic` stripe blurring.
4. **Windows caveats**: `-pattern_type glob` is unimplemented on Windows FFmpeg builds (`Function not implemented`); use `-pattern_type sequence` (`-start_number 1 -i "...-%03d.jpeg"`) or `-f concat -safe 0` (with `/` separators and `'\''` apostrophe escaping). Always invoke `subprocess.run(..., shell=False)` with list args, `encoding="utf-8"` for text logs, and `newline=""` for `csv.writer`.
