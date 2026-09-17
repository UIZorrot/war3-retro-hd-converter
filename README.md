# War3 Retro HD Converter

[Chinese README](README.zh-CN.md)

War3 Retro HD Converter converts Warcraft III Reforged SD MDX models to HD-material MDX models. It preserves the original geometry, UVs, animations, and Warcraft-managed resources while generating the texture references required by the HD material pipeline.

> This is a material conversion tool, not a remesher or image upscaler. It does not add polygons, reconstruct geometry, or increase diffuse texture resolution.

## Download

Download the Windows x64 portable app from [GitHub Releases](https://github.com/UIZorrot/war3-retro-hd-converter/releases/latest).

1. Download `War3RetroHD-Windows-x64.zip`.
2. Extract the entire archive.
3. Run `War3RetroHD.exe` and keep the `_internal` folder beside it.

No Python installation is required for the portable app. See [CHANGELOG.md](CHANGELOG.md) for release notes.

## Desktop app

The app starts in English. Use the language selector beside **SD → HD** to switch to Chinese; selected files, output folder, and running jobs are retained.

1. Select one or more `.mdx` models, or add a model folder recursively.
2. Select texture files or add one or more texture folders.
3. Click **Check textures** to inspect each model reference and its matched source file.
4. Choose an output folder and click **Convert to HD**.

Each run creates a new `SD-to-HD_<date>_<time>_<id>` folder. Each model receives its own package containing the HD `.mdx`, its required custom textures, generated `RetroTex` material textures, `manifest.json`, and the overall `conversion_report.json`.

Use **Open output folder** when conversion completes.

### Texture matching

The converter searches for a texture in this order:

1. Full logical path below an added resource root, including an alternate extension.
2. The imported file's directory suffix.
3. The model's own directory.
4. A unique filename or extensionless filename match.

Matching is case-insensitive. A unique `Footman.png`, `Footman.dds`, or `Footman.tif` can satisfy a model reference such as `Textures\\Footman.blp`. Path matches take precedence. If several candidates have the same priority, the converter reports an ambiguity instead of choosing one arbitrarily.

**Check textures** reports `model reference → matched file`. Keep duplicate texture names in their original directory structure and add the relevant resource roots.

### What conversion changes

- Converts MDX output to version `1000` and rebuilds materials with `Shader_HD_DefaultUnit`.
- Generates `diffuse`, `alpha_diffuse`, `team_diffuse`, `normal`, `orm`, and `team_orm` maps under `RetroTex`, preserving their logical source paths.
- Recalculates pivot points, extents, vertex normals, and tangents.
- Preserves replaceable resources such as team color, team glow, Black32, and EnvironmentMap as game-managed references.

The automatic normal map is estimated from diffuse brightness changes. The default ORM is compatibility-oriented: full ambient occlusion, maximum roughness, and zero metalness. For physically accurate materials, replace those generated maps with authored or baked Normal and ORM maps.

Original input files are never changed. Missing textures or ambiguous matches prevent conversion. Decode, model-parse, output, and validation failures are written to the report; incomplete model packages are not published.

External submodels, sound files, and FaceFX assets are not collected automatically in this version.

## Run from source

```powershell
python -m pip install -e .[dev]
python launch_desktop.pyw
```

The project uses Python Tk, numpy, Pillow, python-dateutil, and PyMdlxConverter. In source mode, it discovers `../scripts/PyMdlxConverter` and `../scripts/blplabcl.exe`; the packaged app carries its required local runtime and tools.

To rebuild the portable app:

```powershell
python -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -e .[dev] pyinstaller
.\.venv-build\Scripts\python.exe build_desktop.py
```

Before redistributing, verify the distribution licenses for PyMdlxConverter, BLP Lab, and their DLLs. This repository does not include Warcraft III game models or textures.

### Portable app self-test

```powershell
.\dist\War3RetroHD\War3RetroHD.exe --self-test --input "D:\assets\model.mdx" --texture-root "D:\assets" --output "D:\output\diagnostics"
```

This performs an actual conversion, writes `self-test.json` to the output directory, and exits with code `0` on success.

## Command line

### Requirements

- Python 3.10+
- `numpy`
- `Pillow`
- PyMdlxConverter on `PYTHONPATH`, or passed with `--pymdlx-path`
- Optional: `blplabcl.exe` for reliable BLP conversion

Install for development:

```powershell
cd D:\Quenching\LSON\war3-retro-hd-converter
python -m pip install -e .[dev]
```

### Convert one model

```powershell
python -m war3_retro_hd.cli convert-file `
  --input "D:\Quenching\LSON\Pack\war3.w3mod\units\human\footman\footman.mdx" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

### Convert a model tree

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "D:\Quenching\LSON\Pack\war3.w3mod\units" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

Converted paths preserve their location relative to `--source-root`. To write buildings below `Rbuildings`:

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "D:\Quenching\LSON\Pack\war3.w3mod\buildings" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --path-rewrite "buildings=Rbuildings" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

### Audit duplicate texture names

Generated maps use `RetroTex/<source logical path>_*.tif`, preventing basename collisions from older `RetroTex/<basename>_*.tif` layouts.

```powershell
python -m war3_retro_hd.cli audit-textures `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod"
```

### Package model folders

```powershell
python -m war3_retro_hd.cli package-models `
  --input-root "D:\Quenching\QM\3.3\Retro" `
  --source-root "D:\Quenching\QM\3.3\Retro" `
  --output-root "D:\Quenching\QM\3.3\Retro_Packaged" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

Each package contains the MDX files in that source directory and only the referenced `RetroTex` files. Warcraft-managed resources remain external game references.

### Create a shared RetroTex DDS/BC3 release

```powershell
python -m war3_retro_hd.cli make-dds-release `
  --source-root "D:\Quenching\QM\3.3\Retro" `
  --output-root "D:\Quenching\QM\3.3\Retro_DDS_BC3" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

This copies the model tree, converts `RetroTex\\*.tif` to BC3/DXT5 `.dds`, and rewrites matching MDX texture paths. Use TIF by default unless your DDS pipeline has been verified in Warcraft III Reforged.

## Notes

- Missing texture files alone should not crash Warcraft III; crashes commonly indicate invalid MDX structure or unsupported material/layer combinations.
- Do not convert Warcraft replaceable team-color or team-glow paths into ordinary images.
- Validate the final package in the target game environment before distribution.
