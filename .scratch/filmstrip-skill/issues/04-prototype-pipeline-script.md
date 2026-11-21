# Prototype FFmpeg + Python Pipeline Script

Type: `prototype`
Status: `open`
Blocked by: 01, 02, 03

## Question

Build and run a rough prototype script against a synthetic test video generated with FFmpeg (`testsrc2` / `rgbtestsrc`) to verify:

1. Extracted frames are saved in the output frames folder at the configured FPS.
2. The 4-column grid image renders cleanly even when frame count is not divisible by 4 (e.g., 5, 7, or 10 frames).
3. The average-color barcode image and CSV match expected RGB values for known solid/gradient test frames.
4. Both Windows path handling and execution speed meet expectations.
