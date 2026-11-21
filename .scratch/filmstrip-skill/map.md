# Filmstrip Skill — Wayfinder Map

Labels: `wayfinder:map`

## Destination

An English-language Antigravity skill (`SKILL.md` + `scripts/`) using FFmpeg and Python (stdlib) to extract frames from any video and produce:
1. The kept extracted-frames folder (`-001.jpeg`, `-002.jpeg`, ...),
2. A single aggregated 4-column grid image (4K target) of all extracted frames,
3. An average-color barcode image (replacing MATLAB `averageColorGrab.m`), and
4. An average-RGB CSV file—stored in this repository for git and installed globally in `~/.gemini/config/skills/`.

## Notes

- **Domain**: Video frame extraction, contact-sheet grid synthesis, and per-frame average-color barcode generation.
- **Skills to consult every session**: `writing-for-agents`, `agy-customizations`, `domain-modeling`.
- **Standing preferences (already settled with user)**:
  - Skill prose, docs, and script CLI/comments must be in **English**.
  - Default extraction rate: **1 fps** (`-r 1`), configurable.
  - Keep intermediate extracted frames in their own output folder.
  - Aggregated frames image layout: **grid with always 4 columns** and as many rows as needed (`ceil(N / 4)`).
  - Target resolution preference: **4K**.
  - Tech stack: **FFmpeg** (`9.0.2` installed) + **Python** (`3.15.2` stdlib installed; no `Pillow`/`numpy`/`cv2` installed). No MATLAB dependency.
  - Delivery locations: this workspace repository (`filmstrip-skill`) and global skills directory (`~/.gemini/config/skills/`).

## Decisions so far

<!-- Index of resolved tickets: one-line gist + link -->
- **[Output Dimensions and JPEG Limits](issues/01-output-dimensions-and-jpeg-limits.md)**: Grid targets `3840px` total width (`960px`/tile across 4 cols) and auto-splits into numbered JPEG Grid Sheets at `65500px` height; kept extracted frames stay at original video resolution; barcode defaults to `1px`/frame × `715px` height.
- **[FFmpeg + Python Stdlib Pipeline Research](issues/02-ffmpeg-python-pipeline-research.md)**: Single-pass `fps=<rate>,split=2` extracts JPEGs (`-q:v 2`) + streams `format=rgb24,scale=1:1:flags=area+accurate_rnd` raw bytes to Python, then Pass 2 runs `tile=4x<rows>` via `sequence`/`concat` (never `glob` on Windows) respecting FFmpeg `mjpeg`'s `65500px` axis cap and piping barcode bytes with `flags=neighbor` ([research](research/02-ffmpeg-python-pipeline.md)).

## Not yet specified

- Exact `SKILL.md` structure and whether `references/` docs are needed alongside `scripts/`.
- Repository layout for git (e.g., `skills/filmstrip/SKILL.md` vs root files + install/sync mechanism to `~/.gemini/config/skills/`).
- Edge cases surfaced by prototyping (videos with < 4 frames, non-16:9 / portrait aspect ratios, variable frame rate inputs, Windows filename/path quoting).

## Out of scope

- MATLAB `.m` script support or requiring a MATLAB installation.
- Video re-encoding / creating videos back from images.
