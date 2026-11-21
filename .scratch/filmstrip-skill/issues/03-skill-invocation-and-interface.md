# Skill Invocation, Naming, and Output Interface

Type: `grilling`
Status: `resolved`
Blocked by: 01

## Question

Define the skill's public interface and ergonomics:

1. **Skill name & invocation mode**: Should the skill be named `filmstrip` (or `video-filmstrip`), and should it be **model-invoked** (with a concise trigger `description`) or **user-invoked only** (`disable-model-invocation: true`)?
2. **Output naming & directory structure**: Given an input video like `my_video.mp4` or `s01e01.mp4`, what should the output folder and file names look like?
   - Extracted frames folder (e.g., `<output_dir>/frames/frame-%04d.jpeg` or `<prefix>-%03d.jpeg`)
   - Aggregated 4-column grid image (`<prefix>_grid.jpeg`)
   - Average-color barcode image (`<prefix>_averagesRGB.jpeg`)
   - Average-RGB CSV (`<prefix>_averagesRGB.csv`, with or without header / frame index / timestamp?)
3. **CLI flags**: Which flags should the helper script expose (`--fps`, `--width`, `--cols`, `--barcode-height`, `--output-dir`, `--prefix`, etc.)?

## Answer

- **Skill Name & Invocation**: `video-filmstrip`, **user-invoked only** (`disable-model-invocation: true` in `SKILL.md` frontmatter, one-line human-facing `description`).
- **Output Directory & File Names** (default `<prefix>` = input video stem; default parent = input video directory unless `--output-dir` is specified):
  - `<prefix>_filmstrip/frames/<prefix>-001.jpeg`, ... (Extracted Frames)
  - `<prefix>_filmstrip/<prefix>_grid.jpeg` (or `<prefix>_grid-001.jpeg`, ... when split across Grid Sheets at `65500px`)
  - `<prefix>_filmstrip/<prefix>_averagesRGB.jpeg` (Average Color Barcode)
  - `<prefix>_filmstrip/<prefix>_averagesRGB.csv` (Average RGB CSV)
- **CSV Format**: Header + metadata columns: `frame,timestamp_sec,r,g,b`.
- **CLI Flags**: `input_video`, `--output-dir`, `--prefix`, `--fps` (default `1`), `--cols` (default `4`), `--grid-width` (default `3840`), `--barcode-height` (default `715`), `--barcode-stripe-width` (default `1`), `--quality` (default `2`), `--start` (`-ss`), and `--duration` (`-t`).
