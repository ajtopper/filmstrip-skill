# 03: Average Color Barcode and Average RGB CSV generation

**What to build:** In the same single FFmpeg decode pass used to extract Extracted Frames, the CLI computes each frame's mean RGB color (using accurate area scaling in `rgb24`), writes `<prefix>_averagesRGB.csv` with `frame,timestamp_sec,r,g,b` rows, and renders the Average Color Barcode (`<prefix>_averagesRGB.jpeg`, defaulting to 1px stripe width per frame by 715px height).

**Blocked by:** 01: End-to-end Extracted Frames and single Grid Sheet tracer bullet

**Status:** ready-for-agent

- [ ] Computes per-frame RGB averages in the same decode pass as frame extraction (`format=rgb24,scale=1:1:flags=area+accurate_rnd`)
- [ ] Writes `<prefix>_averagesRGB.csv` with UTF-8 encoding, `newline=""`, and header `frame,timestamp_sec,r,g,b`
- [ ] Renders `<prefix>_averagesRGB.jpeg` via nearest-neighbor scaling (`flags=neighbor`) at `N * stripe_width` by `barcode_height` (default `1px` × `715px` per frame)
- [ ] Verified with an automated integration test against synthetic solid/split color test frames asserting expected RGB values within <= 1 LSB and barcode dimensions
