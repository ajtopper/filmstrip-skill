# Spec: Numbered Frame Badges on Filmstrip Grid Sheets

Status: `ready-for-agent`

## Problem Statement

When inspecting a 4-column Filmstrip Grid—especially across visually similar or fast-cut scenes, or when a video spans multiple Grid Sheets—viewers cannot tell at a glance the exact chronological appearance order of each tile. Without visible frame numbers on the grid, mapping a tile back to its Extracted Frame file or its timestamp row in the Average RGB CSV requires manually counting rows and columns.

## Solution

Overlay a compact **Frame Badge** in the bottom-left corner of every tile on every Grid Sheet, displaying the 1-based chronological frame index in `16px` black text centered inside a white circular background sized to the font. Numbering continues monotonically across multi-sheet Grid Sheets (e.g., sheet 2 picks up from the frame after sheet 1's last tile), while leaving the source Extracted Frames, Average Color Barcode, and Average RGB CSV unchanged.

## User Stories

1. As a user inspecting a Filmstrip Grid, I want each tile to show its 1-based appearance order number in the bottom-left corner, so that I can immediately trace the sequence of frames left-to-right, top-to-bottom.
2. As a user inspecting a Filmstrip Grid over dark or bright footage, I want the frame number rendered in black `16px` text on a solid white circular background sized tightly to the font, so that the number remains legible over any scene color without obscuring the frame.
3. As a user reviewing a long video split across multiple Grid Sheets, I want frame numbering to continue sequentially across sheets rather than resetting to `1` on each sheet, so that every tile number matches its exact Extracted Frame index and Average RGB CSV row.
4. As a user archiving Extracted Frames, I want the kept frames in the extracted-frames folder to remain clean and unbadged, so that raw frames stay reusable outside the grid.
5. As a user analyzing color telemetry, I want the Average Color Barcode and Average RGB CSV to reflect the video's true colors unaffected by the white circular Frame Badge, so that RGB measurements remain accurate.
6. As a user processing videos of varying resolutions (landscape, portrait, low-res, or 4K), I want the Frame Badge font size (`16px`) and circle size to be consistent in final Grid Sheet pixels, so that badges never look oversized on low-res sources or microscopic on 4K sources.
7. As a user generating a Filmstrip Grid with custom `--cols` or `--grid-width`, I want Frame Badges to appear on every populated tile while leaving unused trailing black cells on an incomplete last row unnumbered, so that empty grid padding is never mislabeled as a frame.
8. As a user running with `--start` and `--duration` trim flags, I want the displayed Frame Badges to number the extracted sequence `1..N` matching the extracted frame files and CSV `frame` column, so that all outputs stay 1-to-1 aligned.
9. As a user on Windows without third-party Python imaging libraries, I want Frame Badge rendering to rely solely on FFmpeg and the Python standard library, so that zero extra dependencies are required.

## Implementation Decisions

- **Pipeline stage**: Render Frame Badges during Grid Sheet assembly after scaling and padding each Extracted Frame to tile dimensions and immediately before applying the `tile` filter. This keeps the single-pass extraction, Extracted Frames folder, Average Color Barcode, and Average RGB CSV untouched, guarantees uniform `16px` sizing across arbitrary input aspect ratios and resolutions, and ensures unused trailing `tile` cells remain plain black.
- **Badge geometry and styling**:
  - Position: bottom-left corner of each tile with a small consistent pixel inset from the bottom and left edges.
  - Typography: `16px` black numeral (`1`, `2`, `3`, ...), rendered via FFmpeg's `drawtext` filter.
  - Background: solid white circular disc sized closely to the `16px` font height (with minimal circular padding so digits remain centered inside the circle), overlaid behind the text using a zero-dependency circular alpha mask generated in memory or via FFmpeg filter expression.
- **Continuous multi-sheet numbering**: Pass each Grid Sheet's starting 1-based frame offset into the badge text expression so sheet `k` numbers frames starting at `(k - 1) * frames_per_sheet + 1`.
- **Cross-platform font resolution**: Ensure `drawtext` resolves a reliable sans-serif font cleanly on Windows (as well as POSIX environments) without hardcoding brittle environment-specific paths.
- **Optional toggle / defaults**: Frame numbering is enabled by default on all Filmstrip Grids, with an optional CLI flag (e.g., `--no-frame-numbers` if needed—only if explicitly requested; otherwise always on by default).
- **Skill and repository docs**: Update the `video-filmstrip` skill instructions, glossary, and repository README to document the Frame Badge on Grid Sheets.

## Testing Decisions

- **Single high-level seam**: Continue testing through the single existing public seam—invoking the filmstrip CLI entrypoint against synthetic FFmpeg-generated videos—and inspecting the produced Grid Sheet images via `ffprobe` / FFmpeg raw RGB pixel sampling.
- **What makes a good test**: Assert observable pixel and layout properties of the generated Grid Sheet rather than internal filter string construction:
  - A dark synthetic video yields bright white pixels at the expected bottom-left circular badge region of each populated tile, with dark/black glyph pixels inside the circle center.
  - Unused trailing cells on a partial final row remain black (no badge rendered in empty cells).
  - Multi-sheet split Grid Sheets render continuous badges across sheet boundaries (the first tile of sheet 2 has a badge while trailing unused cells do not), and kept Extracted Frames remain unbadged (dark at the bottom-left pixel).
  - Average RGB CSV and Average Color Barcode values remain unaffected by the white badge.

## Out of Scope

- Burning timestamps or frame numbers onto the kept Extracted Frames in the frames folder.
- Custom badge colors, font families, or arbitrary corner placement flags beyond the specified bottom-left `16px` black-on-white-circle style.
- Adding third-party Python dependencies such as Pillow or OpenCV.

## Further Notes

- Multi-digit frame numbers (`100+` or `1000+` on long videos) may be wider than a `16px`-tall circle if the circle diameter is fixed strictly to `16px`; sizing the circle diameter tightly around the `16px` font (e.g., ~`22px`–`28px` or sizing gracefully for 2–3+ digits while keeping `16px` font) should be verified during implementation so multi-digit indices remain legible inside the white circle.
