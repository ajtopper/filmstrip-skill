# Filmstrip Skill

Domain vocabulary for extracting video frames and generating aggregated visual and color summaries.

## Language

**Extracted Frame**:
A single JPEG image sampled from the source video at the configured frame rate (default 1 fps) and kept at the source video's original resolution.
_Avoid_: thumbnail, snapshot, screenshot

**Filmstrip Grid**:
The 4-column contact-sheet layout arranging all Extracted Frames in chronological row-major order at a 4K target total width (`3840px`).
_Avoid_: collage, montage, storyboard

**Grid Sheet**:
A single output JPEG file representing one page of a Filmstrip Grid, capped at FFmpeg's `65500px` JPEG height limit.
_Avoid_: chunk, slice, part

**Average Color Barcode**:
An image composed of contiguous vertical color stripes (default `1px` wide by `715px` tall per frame) showing each Extracted Frame's mean RGB color over time.
_Avoid_: palette, color strip, spectrum

**Average RGB CSV**:
A comma-separated data file recording the per-frame mean red, green, and blue values corresponding to an Average Color Barcode.
_Avoid_: color dump, metadata table

**Frame Badge**:
A bottom-left circular white marker with `16px` black text overlaid on each populated tile in a Grid Sheet to show its 1-based chronological appearance order.
_Avoid_: watermark, stamp, caption
