"""Package converted models into standalone folders with local RetroTex assets."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .textures import normalize_mdx_texture_path


@dataclass
class PackageRecord:
    source_dir: str
    output_dir: str
    models: list[str] = field(default_factory=list)
    copied_textures: list[str] = field(default_factory=list)
    missing_textures: list[str] = field(default_factory=list)


def is_local_generated_texture(texture_path: str) -> bool:
    return normalize_mdx_texture_path(texture_path).lower().startswith("retrotex\\")


def collect_model_texture_paths(model) -> set[str]:
    referenced_texture_ids = set()
    for material in getattr(model, "materials", []):
        for layer in getattr(material, "layers", []):
            referenced_texture_ids.add(getattr(layer, "texture_id", -1))

    paths = set()
    for texture_id in referenced_texture_ids:
        if texture_id < 0 or texture_id >= len(getattr(model, "textures", [])):
            continue
        texture = model.textures[texture_id]
        path = normalize_mdx_texture_path(getattr(texture, "path", ""))
        if path and is_local_generated_texture(path):
            paths.add(path)
    return paths


def iter_model_package_dirs(input_root: str | os.PathLike[str]):
    root = Path(input_root)
    dirs = sorted({path.parent for path in root.rglob("*.mdx") if path.is_file()})
    for path in dirs:
        yield path


def copy_referenced_texture(texture_path: str, source_root: Path, output_dir: Path) -> tuple[bool, str]:
    relative = Path(*normalize_mdx_texture_path(texture_path).split("\\"))
    source_path = source_root / relative
    dest_path = output_dir / relative
    if not source_path.exists():
        return False, str(source_path)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, dest_path)
    return True, str(dest_path)


def package_model_dir(model_dir: Path, source_root: Path, output_root: Path, model_class) -> PackageRecord:
    relative_dir = model_dir.relative_to(source_root)
    output_dir = output_root / relative_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    record = PackageRecord(source_dir=str(model_dir), output_dir=str(output_dir))
    texture_paths: set[str] = set()

    for source_model in sorted(model_dir.glob("*.mdx")):
        output_model = output_dir / source_model.name
        shutil.copy2(source_model, output_model)
        record.models.append(str(output_model))

        model = model_class(source_model.read_bytes())
        model.load()
        texture_paths.update(collect_model_texture_paths(model))

    for texture_path in sorted(texture_paths):
        ok, result_path = copy_referenced_texture(texture_path, source_root, output_dir)
        if ok:
            record.copied_textures.append(result_path)
        else:
            record.missing_textures.append(result_path)

    return record


def package_model_tree(input_root: str, source_root: str, output_root: str, model_class, limit: int | None = None) -> list[PackageRecord]:
    package_dirs = list(iter_model_package_dirs(input_root))
    if limit is not None:
        package_dirs = package_dirs[:limit]
    source_root_path = Path(source_root).resolve()
    output_root_path = Path(output_root).resolve()
    return [package_model_dir(path.resolve(), source_root_path, output_root_path, model_class) for path in package_dirs]
