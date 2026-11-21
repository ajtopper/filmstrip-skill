# Skill Invocation, Naming, and Output Interface

Type: `grilling`
Status: `open`
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
