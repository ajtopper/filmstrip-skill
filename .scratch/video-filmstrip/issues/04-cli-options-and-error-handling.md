# 04: CLI options for frame rate, trimming, dimensions, and custom paths

**What to build:** Expose and validate the full CLI surface (`--output-dir`, `--prefix`, `--fps`, `--cols`, `--grid-width`, `--barcode-height`, `--barcode-stripe-width`, `--quality`, `--start`, `--duration`) and provide clear errors for missing FFmpeg, unreadable inputs, invalid numeric arguments, and Windows paths containing spaces or apostrophes.

**Blocked by:** 01: End-to-end Extracted Frames and single Grid Sheet tracer bullet, 03: Average Color Barcode and Average RGB CSV generation

**Status:** done

- [x] Supports `--output-dir`, `--prefix`, `--fps` (default 1), `--cols` (default 4), `--grid-width` (default 3840), `--barcode-height` (default 715), `--barcode-stripe-width` (default 1), `--quality` (default 2), `--start`, and `--duration`
- [x] Handles Windows paths containing spaces and apostrophes safely (`shell=False`, no `glob` demuxer)
- [x] Fails cleanly with actionable error messages when FFmpeg is unavailable, input video does not exist, or no frames are extracted
- [x] Verified with automated tests covering trim options, custom dimensions/columns, Windows special-character paths, and error cases
