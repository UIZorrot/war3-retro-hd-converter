# Repository Instructions

- Do not commit Warcraft III game assets, generated MDX files, generated textures, or local `_retail_` output.
- Keep generated textures under `RetroTex` and preserve the source logical path beneath it. Do not collapse generated names to basename-only paths.
- Preserve replaceable texture IDs for team color, team glow, and other Warcraft-managed resources.
- Keep converted MDX model version at `1000` unless a verified Reforged compatibility reason requires otherwise.
- Run `python -m compileall -q .\src .\tests` and `python -m pytest -q` after code changes.
- Use TIF by default. Use DDS only when BC3/DXT5 output has been verified in Warcraft III Reforged.
