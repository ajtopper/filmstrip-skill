# 07: Continuous Frame Badge numbering across multi-sheet Grid Sheets & multi-digit fit

**What to build:** Ensure multi-sheet Grid Sheets (`grid-001`, `grid-002`, ...) continue Frame Badge numbering sequentially across sheet boundaries (never resetting to `1` on sheet 2), fit multi-digit indices (`10+`, `100+`) cleanly inside the white circle, and resolve a sans-serif font portably on Windows without third-party dependencies.

**Blocked by:** 06: Render Frame Badges on single-sheet Filmstrip Grids

**Status:** done

- [x] Multi-sheet Grid Sheets continue 1-based numbering sequentially across sheet boundaries (`(sheet - 1) * frames_per_sheet + 1`)
- [x] Multi-digit frame numbers (`10+`, `100+`) remain centered and legible inside the white circular badge
- [x] Resolves sans-serif font portably on Windows and POSIX without hardcoding brittle paths
- [x] Verified with an automated integration test covering multi-sheet boundary continuity and multi-digit badge geometry
