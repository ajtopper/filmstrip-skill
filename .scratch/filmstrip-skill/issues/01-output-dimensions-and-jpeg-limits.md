# Output Dimensions and JPEG Limits

Type: `grilling`
Status: `open`

## Question

Settle exact output dimensions and large-video safeguards:

1. **4K Grid Interpretation**: Does "4K" for the 4-column aggregated grid mean **3840px total grid width** (960px per tile across 4 columns), **3840px per individual tile**, or something else?
2. **Large-Video Dimension Limits**: JPEG has a hard 65,535px max width/height limit. At 1 fps, a 1-hour video produces 3,600 frames = 900 rows in a 4-column grid:
   - At 960×540 per tile, 900 rows = 486,000px tall (exceeds JPEG/PNG practical limits and memory).
   - How should the skill handle long videos whose 4-column grid exceeds safe image limits: split into numbered grid sheets (e.g., `grid-001.jpg`, `grid-002.jpg`), auto-scale tile height/width to fit a single image, or enforce a configurable cap?
3. **Average Color Barcode Dimensions**: Keep the original MATLAB plan's `1px` width per frame × `715px` height (`PaperPosition: [0, 0, videoLength, 715]`), or target a fixed 4K width (`3840px`) / configurable dimensions?
