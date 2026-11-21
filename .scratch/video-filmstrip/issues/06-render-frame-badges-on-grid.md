# 06: Render Frame Badges on single-sheet Filmstrip Grids

**What to build:** Overlay a bottom-left Frame Badge on every populated tile of a single Grid Sheet—rendering the 1-based chronological frame index in `16px` black text centered inside a white circular background sized closely to the font—while keeping unused trailing cells plain black and leaving Extracted Frames, Average Color Barcode, and Average RGB CSV untouched.

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Renders a circular white background with centered 16px black 1-based numeral in the bottom-left corner of every populated tile on a Grid Sheet
- [x] Keeps unused trailing grid cells plain black (no Frame Badge)
- [x] Leaves Extracted Frames, Average Color Barcode, and Average RGB CSV unchanged
- [x] Verified with an automated integration test sampling bottom-left tile badge pixels, unused trailing cells, and raw Extracted Frames
