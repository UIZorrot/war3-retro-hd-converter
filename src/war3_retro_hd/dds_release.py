"""Build a shared-RetroTex DDS/BC3 release tree."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, asdict
from pathlib import Path

from PIL import Image

from .textures import normalize_mdx_texture_path


@dataclass
class DdsReleaseStats:
    copied_files: int = 0
    converted_textures: int = 0
    rewritten_models: int = 0
    rewritten_texture_paths: int = 0
    failed_textures: list[dict] | None = None
    failed_models: list[dict] | None = None

    def __post_init__(self):
        if self.failed_textures is None:
            self.failed_textures = []
        if self.failed_models is None:
            self.failed_models = []


def is_under_retrotex(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    return bool(rel.parts) and rel.parts[0].lower() == "retrotex"


def copy_non_retrotex_files(source_root: Path, output_root: Path, stats: DdsReleaseStats) -> None:
    for source_path in source_root.rglob("*"):
        if not source_path.is_file():
            continue
        if is_under_retrotex(source_path, source_root):
            continue
        dest_path = output_root / source_path.relative_to(source_root)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, dest_path)
        stats.copied_files += 1


def save_bc3_dds(source_path: Path, dest_path: Path) -> None:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source_path) as raw:
        image = raw.convert("RGBA")
        image.save(dest_path, format="DDS", pixel_format="DXT5")


def convert_retrotex_to_dds(source_root: Path, output_root: Path, stats: DdsReleaseStats) -> None:
    retrotex_root = source_root / "RetroTex"
    if not retrotex_root.exists():
        return
    for source_path in retrotex_root.rglob("*"):
        if not source_path.is_file():
            continue
        rel = source_path.relative_to(source_root)
        if source_path.suffix.lower() in (".tif", ".tiff"):
            dest_path = (output_root / rel).with_suffix(".dds")
            try:
                save_bc3_dds(source_path, dest_path)
                stats.converted_textures += 1
            except Exception as exc:
                stats.failed_textures.append({"path": str(source_path), "error": f"{type(exc).__name__}: {exc}"})
        elif source_path.suffix.lower() == ".dds":
            dest_path = output_root / rel
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dest_path)
            stats.converted_textures += 1


def rewrite_model_retrotex_paths(model, stats: DdsReleaseStats) -> None:
    for texture in getattr(model, "textures", []):
        path = normalize_mdx_texture_path(getattr(texture, "path", ""))
        if path.lower().startswith("retrotex\\") and path.lower().endswith((".tif", ".tiff")):
            base = path.rsplit(".", 1)[0]
            texture.path = base + ".dds"
            stats.rewritten_texture_paths += 1


def rewrite_output_models(output_root: Path, model_class, stats: DdsReleaseStats) -> None:
    for model_path in output_root.rglob("*.mdx"):
        try:
            model = model_class(model_path.read_bytes())
            model.load()
            before = stats.rewritten_texture_paths
            rewrite_model_retrotex_paths(model, stats)
            if stats.rewritten_texture_paths != before:
                model_path.write_bytes(model.save_mdx())
                stats.rewritten_models += 1
        except Exception as exc:
            stats.failed_models.append({"path": str(model_path), "error": f"{type(exc).__name__}: {exc}"})


def verify_dds_bc3_header(path: Path) -> bool:
    with path.open("rb") as handle:
        header = handle.read(128)
    return header[:4] == b"DDS " and header[84:88] == b"DXT5"


def summarize_dds_headers(output_root: Path, sample_limit: int = 100) -> dict:
    dds_files = list((output_root / "RetroTex").rglob("*.dds")) if (output_root / "RetroTex").exists() else []
    bad = []
    for path in dds_files[:sample_limit]:
        if not verify_dds_bc3_header(path):
            bad.append(str(path))
    return {"dds_files": len(dds_files), "sample_checked": min(len(dds_files), sample_limit), "bad_sample_headers": bad}


def build_dds_release(source_root: str, output_root: str, model_class) -> dict:
    source = Path(source_root).resolve()
    output = Path(output_root).resolve()
    output.mkdir(parents=True, exist_ok=True)
    stats = DdsReleaseStats()
    copy_non_retrotex_files(source, output, stats)
    convert_retrotex_to_dds(source, output, stats)
    rewrite_output_models(output, model_class, stats)
    payload = asdict(stats)
    payload["dds_header_summary"] = summarize_dds_headers(output)
    report_path = output / "_reports" / "dds_release_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    payload["report_path"] = str(report_path)
    return payload
