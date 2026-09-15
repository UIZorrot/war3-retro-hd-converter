# Changelog

## v0.1.0 — 2026-09-15

First release of the Windows desktop app and Python conversion toolkit.

### Desktop app

- English by default, with live English / Chinese switching beside the title.
- Select multiple MDX models, individual textures or texture folders.
- Match textures by logical path and unique filename, ignoring case and allowing alternate image extensions.
- Show the matched source for each reference; report missing and ambiguous textures before conversion.
- Generate one complete package per model with HD MDX, TIF material textures, original custom textures and a manifest.
- Keep Warcraft-managed resources as game references and write each run into a new output folder.
- Include a portable Windows x64 runtime with PyMdlxConverter and BLP Lab.

### Command line

- Convert individual models or entire model trees.
- Audit texture names, validate MDX structure, package converted models and create DDS/BC3 releases.

### Validation

- 33 automated tests passed.
- Portable executable tested without Python or Conda on its search path.
- Footman, Footman Portrait and Farm conversion smoke tests passed during development.
- Bilingual executable tested with a real Footman model and loose, uppercase DDS texture filenames.
- Model geometry, UVs and bone animation data compared against the originals for the three development examples.

### Scope

- Preserves SD geometry and animations; does not add mesh detail or upscale image resolution.
- External submodels, sound files and FaceFX assets are not collected automatically.
- Game-managed resources remain external references. In-game rendering has not been manually verified for this release.
- Game assets and generated examples are not included in the source repository or release archive.
