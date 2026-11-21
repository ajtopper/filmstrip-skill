# 05: Author video-filmstrip skill, README, and global installation

**What to build:** Author the English `video-filmstrip` Antigravity skill (`disable-model-invocation: true`, concise runbook pointing to the Python script and output validation checks), add a root repository `README.md`, and install the skill globally under `~/.gemini/config/skills/video-filmstrip/`.

**Blocked by:** 02: Multi-sheet Grid splitting for long videos (> 65500px), 03: Average Color Barcode and Average RGB CSV generation, 04: CLI options for frame rate, trimming, dimensions, and custom paths

**Status:** done

- [x] Creates `video-filmstrip` `SKILL.md` in English with `disable-model-invocation: true`, human-facing one-line description, prerequisites, usage steps, and output verification checks
- [x] Creates repository `README.md` documenting features, requirements, CLI usage, and installation
- [x] Installs the complete `video-filmstrip` skill folder into `~/.gemini/config/skills/video-filmstrip/` matching the repository copy
- [x] Verified end-to-end by running the installed global skill script against a test video and confirming all four outputs
