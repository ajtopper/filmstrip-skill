# 02: Multi-sheet Grid splitting for long videos (> 65500px)

**What to build:** When a video's 4-column Filmstrip Grid exceeds FFmpeg's 65500px JPEG axis limit, the CLI automatically splits the output into numbered JPEG Grid Sheets (`<prefix>_grid-001.jpeg`, `<prefix>_grid-002.jpeg`, ...) with no empty trailing sheets, while single-sheet grids continue writing `<prefix>_grid.jpeg`.

**Blocked by:** 01: End-to-end Extracted Frames and single Grid Sheet tracer bullet

**Status:** ready-for-agent

- [ ] Computes `max_rows_per_sheet` from the tile height and FFmpeg's 65500px JPEG height cap before encoding
- [ ] Writes `<prefix>_grid.jpeg` when all rows fit on one sheet, and `<prefix>_grid-001.jpeg`, `<prefix>_grid-002.jpeg`, ... when split across multiple sheets
- [ ] Verified with an automated integration test simulating sheet overflow (verifying multiple output sheets and expected dimensions below 65500px)
