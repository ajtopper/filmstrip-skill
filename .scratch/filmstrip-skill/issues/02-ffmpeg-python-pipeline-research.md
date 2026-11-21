# FFmpeg + Python Stdlib Pipeline Research

Type: `research`
Status: `open`

## Question

Investigate primary documentation and local FFmpeg 9.0.2 / Python 3.15.2 capabilities to verify the cleanest zero-dependency pipeline (no Pillow/NumPy/OpenCV):

1. **Frame extraction & scaling**: Exact `ffmpeg` flags for extracting frames at `fps` (default `1`) into a subfolder (`-vsync`/`-fps_mode`, JPEG quality `-q:v`, scaling filters).
2. **4-column grid assembly**: Can `ffmpeg`'s `tile=4x<rows>` filter (with `padding` / `margin` or `color` background for incomplete last row) build the 4-column grid directly from extracted frames or a single-pass filtergraph, and what are its exact pixel/dimension limits?
3. **Average RGB calculation & barcode image**: How accurately and fast can `ffmpeg` compute per-frame average RGB (e.g., `scale=1:1:flags=area` + `-f rawvideo -pix_fmt rgb24` piped to Python stdout) compared to reading extracted JPEGs, and can Python pipe raw `rgb24` / PPM bytes back into `ffmpeg` to encode the final barcode JPEG/PNG?
4. **Windows compatibility**: Any quoting, globbing (`image2` `%03d` vs `concat` demuxer), or path-length caveats on Windows PowerShell.
