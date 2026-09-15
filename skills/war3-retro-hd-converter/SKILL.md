---
name: war3-retro-hd-converter
description: Convert Warcraft III Reforged SD MDX models from war3.w3mod into HD-material MDX replacements with generated RetroTex diffuse/normal/ORM textures. Use when Codex needs to run, debug, package, or extend this SD-to-HD conversion pipeline, especially for units, buildings, team color alpha, DDS/TIF texture handling, MDX pivot/extent/normal/tangent repair, and duplicate texture basename issues.
---

# War3 Retro HD Converter

Use this skill to operate the open-source SD-to-HD conversion repository.

## Required Context

- Treat `war3.w3mod` as the source root containing SD `.mdx` models and original texture resources.
- Treat the Warcraft III `_retail_` directory as the output root only when the user explicitly wants live game replacement files.
- Require PyMdlxConverter to parse and save MDX. If it is not importable, pass `--pymdlx-path` to the CLI.
- Prefer TIF output. Use DDS only when a verified Warcraft-compatible BC3/DXT5 writer is available.

## Core Workflow

1. Run `python -m war3_retro_hd.cli audit-textures --source-root <war3.w3mod>` before bulk conversion if textures look wrong.
2. Convert a small representative model first with `convert-file`.
3. Validate the output with `validate-mdx`.
4. Convert the tree with `convert-tree` only after the representative model is correct.
5. Write buildings to `Rbuildings` if the user is using that replacement convention: `--path-rewrite buildings=Rbuildings`.
6. Use `package-models` after conversion when the user wants each model directory to be independently distributable with a local `RetroTex`.
7. Use `make-dds-release` when the user wants one shared `RetroTex` folder converted to BC3/DXT5 DDS and all model paths rewritten to `.dds`.

## Important Rules

- Keep generated assets under `RetroTex`, but preserve the logical source path under it. Do not collapse to basename-only paths such as `RetroTex\hut_diffuse.tif`; that causes wrong textures when multiple source files share a basename.
- Do not replace Warcraft-managed team color/team glow textures with generated images. Preserve replaceable texture IDs.
- Keep converted model version at `1000`.
- Recalculate pivot points, extents, normals, and tangents after material conversion.
- Use `Shader_HD_DefaultUnit` with the generated diffuse, normal, ORM, black emissive, team color, and environment layers.
- For team-color materials, derive the alpha mask from source alpha and write team ORM alpha as a binary exposure mask.
- Missing textures usually do not crash Warcraft III; hard crashes normally indicate invalid MDX structure, pivot count mismatch, or unsupported material/layer state.

## Typical Commands

Convert one model:

```powershell
python -m war3_retro_hd.cli convert-file `
  --input "<war3.w3mod>\units\human\footman\footman.mdx" `
  --source-root "<war3.w3mod>" `
  --output-root "<_retail_>" `
  --pymdlx-path "<path-containing-PyMdlxConverter>"
```

Convert buildings into `Rbuildings`:

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "<war3.w3mod>\buildings" `
  --source-root "<war3.w3mod>" `
  --output-root "<_retail_>" `
  --path-rewrite "buildings=Rbuildings" `
  --pymdlx-path "<path-containing-PyMdlxConverter>"
```

Validate output:

```powershell
python -m war3_retro_hd.cli validate-mdx --root "<_retail_>\Rbuildings" --pymdlx-path "<path-containing-PyMdlxConverter>"
```

Package standalone model folders:

```powershell
python -m war3_retro_hd.cli package-models `
  --input-root "<converted Retro root>" `
  --source-root "<converted Retro root>" `
  --output-root "<packaged output root>" `
  --pymdlx-path "<path-containing-PyMdlxConverter>"
```

The packager groups by model directory, so a main model and its portrait stay together and share one local `RetroTex` folder. It copies only `RetroTex\...` paths and leaves Warcraft-managed `Textures\...` and `ReplaceableTextures\...` paths untouched.

Build a shared DDS/BC3 release:

```powershell
python -m war3_retro_hd.cli make-dds-release `
  --source-root "<converted Retro root>" `
  --output-root "<dds release output root>" `
  --pymdlx-path "<path-containing-PyMdlxConverter>"
```

After this command, verify that the output `RetroTex` contains only `.dds`, DDS headers report `DXT5`, and no MDX texture path under `RetroTex` still ends in `.tif`.

## Debugging Checklist

- If the model uses the wrong image, run `audit-textures` and inspect duplicate basenames.
- If team color is missing, inspect diffuse alpha and team ORM alpha.
- If team color is too dark, tune team diffuse luminance floors before changing material layers.
- If transparent quads show black boxes, inspect replaceable-only materials and filter modes.
- If Warcraft crashes, inspect pivot point count, material layer count/filter modes, and whether the converted MDX can be loaded by PyMdlxConverter.
