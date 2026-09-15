"""Texture path, loading, and output helpers for Warcraft III assets."""

from __future__ import annotations

import os
import subprocess
import uuid
import tempfile
from pathlib import Path

from PIL import Image


SUPPORTED_TEXTURE_EXTENSIONS = (".dds", ".blp", ".tif", ".tiff", ".png", ".jpg", ".jpeg", ".bmp", ".tga")
TEAM_REPLACEABLE_IDS = {1, 2, 31}


def normalize_mdx_texture_path(path: str | os.PathLike[str] | None) -> str:
    if not path:
        return ""
    return str(path).replace("/", "\\").strip()


def is_replaceable_texture(texture) -> bool:
    return getattr(texture, "replaceable_id", 0) in TEAM_REPLACEABLE_IDS


def get_texture_basename(texture_path: str) -> str:
    normalized = normalize_mdx_texture_path(texture_path)
    return os.path.splitext(os.path.basename(normalized))[0]


def resolve_texture_source(texture, model_path: str, search_roots: list[str] | None = None) -> str | None:
    texture_path = normalize_mdx_texture_path(getattr(texture, "path", ""))
    if not texture_path or is_replaceable_texture(texture):
        return None

    search_roots = list(search_roots or [])
    model_dir = os.path.dirname(os.path.abspath(model_path))
    basename = get_texture_basename(texture_path)
    logical_relative = texture_path.replace("\\", os.sep)
    candidates: list[str] = []

    def add_candidate(path: str | None) -> None:
        if path and path not in candidates:
            candidates.append(path)

    add_candidate(os.path.join(model_dir, texture_path))
    add_candidate(os.path.join(model_dir, os.path.basename(texture_path)))
    for ext in SUPPORTED_TEXTURE_EXTENSIONS:
        add_candidate(os.path.join(model_dir, basename + ext))

    for root in search_roots:
        rooted = os.path.join(root, logical_relative)
        add_candidate(rooted)
        rooted_base = os.path.splitext(rooted)[0]
        for ext in SUPPORTED_TEXTURE_EXTENSIONS:
            add_candidate(rooted_base + ext)
        add_candidate(os.path.join(root, os.path.basename(texture_path)))
        for ext in SUPPORTED_TEXTURE_EXTENSIONS:
            add_candidate(os.path.join(root, basename + ext))

    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return None


def convert_blp_to_tga(blp_path: str, blplab_path: str | None = None) -> str | None:
    if not blplab_path or not os.path.exists(blplab_path):
        return None
    temp_path = os.path.join(tempfile.gettempdir(), f"war3_{uuid.uuid4().hex}.tga")
    try:
        result = subprocess.run(
            [blplab_path, blp_path, temp_path, "-type0"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if result.returncode != 0:
            Path(temp_path).unlink(missing_ok=True)
            return None
        return temp_path if os.path.exists(temp_path) else None
    except (OSError, subprocess.TimeoutExpired):
        Path(temp_path).unlink(missing_ok=True)
        return None


def load_texture_reliable(path: str, blplab_path: str | None = None) -> Image.Image | None:
    if not path or not os.path.exists(path):
        return None

    temp_path = None
    try:
        if path.lower().endswith(".blp"):
            temp_path = convert_blp_to_tga(path, blplab_path=blplab_path)
            if temp_path:
                with Image.open(temp_path) as raw:
                    img = raw.convert("RGBA")
                    img.load()
                    return img

        with Image.open(path) as raw:
            img = raw.convert("RGBA")
            img.load()
            return img
    except Exception:
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def save_war3_texture(image: Image.Image, output_path_without_ext: str, prefer_dds: bool = False) -> str:
    Path(output_path_without_ext).parent.mkdir(parents=True, exist_ok=True)

    if prefer_dds:
        dds_path = output_path_without_ext + ".dds"
        try:
            save_image = image if image.mode in ("RGB", "RGBA", "L", "LA") else image.convert("RGBA")
            save_image.save(dds_path, format="DDS", pixel_format="DXT5")
            return dds_path
        except Exception:
            pass

    tif_path = output_path_without_ext + ".tif"
    save_image = image if image.mode in ("RGB", "RGBA", "L", "LA") else image.convert("RGBA")
    save_image.save(tif_path, format="TIFF", compression="tiff_deflate")
    return tif_path


def iter_texture_files(root: str | os.PathLike[str]):
    root_path = Path(root)
    for path in root_path.rglob("*"):
        if path.is_file() and path.suffix.lower() in SUPPORTED_TEXTURE_EXTENSIONS:
            yield path
