# Output Dimensions and JPEG Limits

Type: `grilling`
Status: `resolved`

## Question

Settle exact output dimensions and large-video safeguards:

1. **4K Grid Interpretation**: Does "4K" for the 4-column aggregated grid mean **3840px total grid width** (960px per tile across 4 columns), **3840px per individual tile**, or something else?
2. **Large-Video Dimension Limits**: JPEG has a hard 65,535px max width/height limit. At 1 fps, a 1-hour video produces 3,600 frames = 900 rows in a 4-column grid:
   - At 960×540 per tile, 900 rows = 486,000px tall (exceeds JPEG/PNG practical limits and memory).
   - How should the skill handle long videos whose 4-column grid exceeds safe image limits: split into numbered grid sheets (e.g., `grid-001.jpg`, `grid-002.jpg`), auto-scale tile height/width to fit a single image, or enforce a configurable cap?
3. **Average Color Barcode Dimensions**: Keep the original MATLAB plan's `1px` width per frame × `715px` height (`PaperPosition: [0, 0, videoLength, 715]`), or target a fixed 4K width (`3840px`) / configurable dimensions?

## Answer

- **4K Grid Width**: `3840px` total grid width across 4 columns (`960px` width per tile, aspect ratio preserved; configurable via flags).
- **Large-Video JPEG Splitting**: Auto-split the 4-column grid into numbered JPEG **Grid Sheets** (`grid-001.jpeg`, `grid-002.jpeg`, ...) whenever total grid height exceeds FFmpeg `mjpeg`'s `65500px` axis cap (`max_rows_per_sheet = floor(65500 / tile_height)`).
- **Average Color Barcode Dimensions**: Default `1px` width per frame × `715px` height (matching the original `[0, 0, videoLength, 715]` layout, configurable via flags).
- **Extracted Frames Resolution**: Keep extracted frames in the output folder at the **original source video resolution** (scaling down to `960px` tile width only during grid sheet assembly).
