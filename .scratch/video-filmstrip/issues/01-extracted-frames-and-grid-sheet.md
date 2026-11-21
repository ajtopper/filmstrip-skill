# 01: End-to-end Extracted Frames and single Grid Sheet tracer bullet

**What to build:** Running the Python CLI against an input video extracts all Extracted Frames at 1 fps into a dedicated frames directory at the source video's original resolution and builds a single 4-column, 4K-wide (3840px total, 960px per tile) Filmstrip Grid Grid Sheet (`<prefix>_grid.jpeg`), normalizing non-16:9 inputs and handling partial final rows (< 4 cells).

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Extracts Extracted Frames into `<prefix>_filmstrip/frames/<prefix>-001.jpeg`... at 1 fps and original source resolution using FFmpeg's `fps` filter
- [x] Computes exact row count `ceil(N / 4)` from the actual extracted frame count `N` (no blank trailing rows)
- [x] Builds `<prefix>_filmstrip/<prefix>_grid.jpeg` at 3840px total width (960px per tile, aspect ratio preserved, centered pad if needed)
- [x] Verified with an automated integration test on a synthetic video covering partial trailing rows and non-16:9 aspect ratios
