"""SD MDX to HD-material conversion logic."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .model_repair import repair_model_geometry
from .textures import (
    get_texture_basename,
    is_replaceable_texture,
    load_texture_reliable,
    normalize_mdx_texture_path,
    resolve_texture_source,
    save_war3_texture,
)


HD_SHADER = "Shader_HD_DefaultUnit"
NORMAL_BRIGHTNESS_OFFSET = 25
TEAM_ALPHA_OPAQUE_THRESHOLD = 245
TEAM_DIFFUSE_EDGE_FLOOR = 80
TEAM_DIFFUSE_STRONG_FLOOR = 160

STATIC_TEXTURES = {
    r"RetroTex\FlatNormal.tif": {"size": (32, 32), "color": (128, 128, 0, 255)},
    r"RetroTex\FlatORM.tif": {"size": (32, 32), "color": (255, 245, 10, 0)},
}


@dataclass
class ConversionStats:
    converted_materials: int = 0
    preserved_materials: int = 0
    converted_textures: int = 0


def _new_texture():
    from PyMdlxConverter.parsers.mdlx.texture import Texture

    return Texture()


def _is_special_sd_path(path: str) -> bool:
    normalized = normalize_mdx_texture_path(path).lower()
    return normalized.startswith("replaceabletextures\\teamcolor\\") or normalized.startswith("replaceabletextures\\teamglow\\")


def get_texture(textures, texture_id: int):
    if texture_id < 0 or texture_id >= len(textures):
        return None
    return textures[texture_id]


def material_uses_replaceable_texture(material, textures) -> bool:
    for layer in material.layers:
        texture = get_texture(textures, layer.texture_id)
        if texture is None:
            continue
        if is_replaceable_texture(texture) or _is_special_sd_path(getattr(texture, "path", "")):
            return True
    return False


def find_material_base_layer(material, textures):
    replaceable_layer = None
    for layer in material.layers:
        texture = get_texture(textures, layer.texture_id)
        if texture is None:
            continue
        if is_replaceable_texture(texture):
            if replaceable_layer is None:
                replaceable_layer = layer
            continue
        if getattr(texture, "path", ""):
            return layer
    return replaceable_layer


def should_convert_material(material, textures) -> bool:
    return find_material_base_layer(material, textures) is not None


def layer_needs_diffuse_alpha(layer) -> bool:
    return getattr(layer, "filter_mode", 0) != 0


def is_building_model_path(model_path: str) -> bool:
    normalized = normalize_mdx_texture_path(model_path).lower()
    return "\\buildings\\" in normalized or "\\rbuildings\\" in normalized or normalized.startswith("buildings\\")


def uses_legacy_unit_material_rules(model_path: str) -> bool:
    normalized = normalize_mdx_texture_path(model_path).lower()
    return "\\units\\human\\gyrocopter\\" in normalized or "\\units\\human\\mortarteam\\" in normalized


def should_force_flat_normal(model_path: str, texture) -> bool:
    normalized_model = normalize_mdx_texture_path(model_path).lower()
    normalized_texture = normalize_mdx_texture_path(getattr(texture, "path", "")).lower()
    is_gnoll_hut = "\\buildings\\other\\gnollhut" in normalized_model or "\\rbuildings\\other\\gnollhut" in normalized_model
    return is_gnoll_hut and normalized_texture == "textures\\hut.blp"


def find_replaceable_layer(material, textures, replaceable_id: int):
    for layer in material.layers:
        texture = get_texture(textures, layer.texture_id)
        if texture is not None and getattr(texture, "replaceable_id", 0) == replaceable_id:
            return layer
    return None


def find_first_real_texture_layer(material, textures):
    for layer in material.layers:
        texture = get_texture(textures, layer.texture_id)
        if texture is not None and not is_replaceable_texture(texture) and getattr(texture, "path", ""):
            return layer
    return None


def is_replaceable_only_material(material, textures) -> bool:
    return material_uses_replaceable_texture(material, textures) and find_first_real_texture_layer(material, textures) is None


def build_hd_texture_virtual_path(texture_path: str, suffix: str) -> str:
    """Build a collision-safe RetroTex path.

    A basename-only path such as RetroTex/hut_diffuse.tif corrupts models when
    both Textures/hut.dds and Buildings/Other/PigFarm/Hut.dds exist. Preserve
    the logical source path under RetroTex instead.
    """
    normalized = normalize_mdx_texture_path(texture_path)
    base, _ = os.path.splitext(normalized)
    parts = [part for part in base.split("\\") if part]
    if not parts:
        parts = [os.path.basename(base) or "texture"]
    parts[-1] = f"{parts[-1]}{suffix}"
    return "RetroTex\\" + "\\".join(parts)


def build_hd_texture_disk_path(texture_path: str, suffix: str, output_root: str) -> str:
    virtual = build_hd_texture_virtual_path(texture_path, suffix)
    return os.path.join(output_root, virtual.replace("\\", os.sep))


def ensure_static_texture_files(output_root: str) -> None:
    for virtual_path, data in STATIC_TEXTURES.items():
        disk_path = os.path.join(output_root, virtual_path.replace("\\", os.sep))
        Path(disk_path).parent.mkdir(parents=True, exist_ok=True)
        if os.path.exists(disk_path):
            continue
        Image.new("RGBA", data["size"], data["color"]).save(disk_path, format="TIFF", compression="tiff_deflate")


def _check_semitransparency(img: Image.Image) -> bool:
    alpha = np.array(img.split()[3])
    semi_count = np.sum((alpha > 10) & (alpha < 245))
    return (semi_count / alpha.size) > 0.005


def _generate_hd_triplet(
    img: Image.Image,
    *,
    team_color_mask: bool = False,
    preserve_diffuse_alpha: bool = False,
    team_diffuse_edge_floor: int = TEAM_DIFFUSE_EDGE_FLOOR,
    team_diffuse_strong_floor: int = TEAM_DIFFUSE_STRONG_FLOOR,
    binary_team_orm_alpha: bool | None = None,
):
    rgba = np.array(img.convert("RGBA"))
    source_alpha = rgba[..., 3].copy()
    team_pixels = source_alpha < TEAM_ALPHA_OPAQUE_THRESHOLD

    alpha_rgba = rgba.copy()
    team_rgba = rgba.copy()
    team_strength = (255 - source_alpha.astype(np.float32)) / 255.0
    team_floor = team_diffuse_edge_floor + (team_diffuse_strong_floor - team_diffuse_edge_floor) * team_strength
    team_luma = (
        0.2126 * team_rgba[..., 0].astype(np.float32)
        + 0.7152 * team_rgba[..., 1].astype(np.float32)
        + 0.0722 * team_rgba[..., 2].astype(np.float32)
    )
    lifted_luma = np.maximum(team_luma, team_floor).astype(np.uint8)
    lifted_rgb = np.repeat(lifted_luma[..., None], 3, axis=2)
    team_rgba[..., :3] = np.where(team_pixels[..., None], lifted_rgb, team_rgba[..., :3])
    team_rgba[..., 3] = 255

    if not preserve_diffuse_alpha:
        rgba[..., 3] = 255

    gray = np.mean(rgba[..., :3], axis=2).astype(np.float32)
    gx = np.gradient(gray, axis=1) * 2.0 if gray.shape[1] > 1 else np.zeros_like(gray)
    gy = np.gradient(gray, axis=0) * 2.0 if gray.shape[0] > 1 else np.zeros_like(gray)
    normal = np.zeros((gray.shape[0], gray.shape[1], 3), dtype=np.uint8)
    normal[..., 0] = np.clip((255 - np.clip(gx + 128, 0, 255)) + NORMAL_BRIGHTNESS_OFFSET, 0, 255).astype(np.uint8)
    normal[..., 1] = np.clip((255 - np.clip(gy + 128, 0, 255)) + NORMAL_BRIGHTNESS_OFFSET, 0, 255).astype(np.uint8)
    normal[..., 2] = NORMAL_BRIGHTNESS_OFFSET

    orm_r = np.full_like(gray, 255, dtype=np.uint8)
    orm_g = np.full_like(gray, 255, dtype=np.uint8)
    orm_b = np.zeros_like(gray, dtype=np.uint8)
    orm_alpha = np.zeros_like(orm_r)
    orm = np.stack([orm_r, orm_g, orm_b, orm_alpha], axis=-1)
    if binary_team_orm_alpha if binary_team_orm_alpha is not None else team_color_mask:
        team_orm_alpha = np.where(team_pixels, 255, 0).astype(np.uint8)
    else:
        team_orm_alpha = (255 - source_alpha).astype(np.uint8)
    team_orm = np.stack([orm_r, orm_g, orm_b, team_orm_alpha], axis=-1)

    return (
        Image.fromarray(rgba, "RGBA"),
        Image.fromarray(alpha_rgba, "RGBA"),
        Image.fromarray(team_rgba, "RGBA"),
        Image.fromarray(normal),
        Image.fromarray(orm, "RGBA"),
        Image.fromarray(team_orm, "RGBA"),
    )


def ensure_hd_texture_triplet(
    texture,
    model_path: str,
    output_root: str,
    *,
    search_roots: list[str] | None = None,
    blplab_path: str | None = None,
    team_color_mask: bool = False,
    preserve_diffuse_alpha: bool = False,
    prefer_dds: bool = False,
    binary_team_orm_alpha: bool | None = None,
    resolved_sources: dict[str, str] | None = None,
):
    resolved = (resolved_sources.get(normalize_mdx_texture_path(texture.path).casefold())
                if resolved_sources is not None
                else resolve_texture_source(texture, model_path, search_roots=search_roots))
    if not resolved:
        return None
    img = load_texture_reliable(resolved, blplab_path=blplab_path)
    if img is None:
        return None

    diffuse_img, alpha_diffuse_img, team_diffuse_img, normal_img, orm_img, team_orm_img = _generate_hd_triplet(
        img,
        team_color_mask=team_color_mask,
        preserve_diffuse_alpha=preserve_diffuse_alpha,
        binary_team_orm_alpha=binary_team_orm_alpha,
    )

    bases = {
        "diff": build_hd_texture_disk_path(texture.path, "_diffuse", output_root),
        "alpha_diff": build_hd_texture_disk_path(texture.path, "_alpha_diffuse", output_root),
        "team_diff": build_hd_texture_disk_path(texture.path, "_team_diffuse", output_root),
        "norm": build_hd_texture_disk_path(texture.path, "_normal", output_root),
        "orm": build_hd_texture_disk_path(texture.path, "_orm", output_root),
        "team_orm": build_hd_texture_disk_path(texture.path, "_team_orm", output_root),
    }
    disk_paths = {
        "diff": save_war3_texture(diffuse_img, bases["diff"], prefer_dds=prefer_dds),
        "alpha_diff": save_war3_texture(alpha_diffuse_img, bases["alpha_diff"], prefer_dds=prefer_dds),
        "team_diff": save_war3_texture(team_diffuse_img, bases["team_diff"], prefer_dds=prefer_dds),
        "norm": save_war3_texture(normal_img, bases["norm"], prefer_dds=prefer_dds),
        "orm": save_war3_texture(orm_img, bases["orm"], prefer_dds=prefer_dds),
        "team_orm": save_war3_texture(team_orm_img, bases["team_orm"], prefer_dds=prefer_dds),
    }

    def virtual_path(key: str) -> str:
        disk_path = disk_paths[key]
        rel = os.path.relpath(disk_path, output_root)
        return rel.replace(os.sep, "\\")

    return {
        "resolved_source": resolved,
        "semi_transparent": _check_semitransparency(img),
        "basename": get_texture_basename(texture.path),
        "virtual_paths": {key: virtual_path(key) for key in disk_paths},
    }


def append_hd_textures(model, old_texture, virtual_paths: dict[str, str]) -> dict[str, int]:
    indices = {}
    for key in ("diff", "alpha_diff", "team_diff", "norm", "orm", "team_orm"):
        texture = copy.deepcopy(old_texture)
        texture.path = virtual_paths[key]
        texture.replaceable_id = 0
        model.textures.append(texture)
        indices[key] = len(model.textures) - 1
    return indices


def get_or_create_texture_by_path(model, path: str) -> int:
    normalized = normalize_mdx_texture_path(path).lower()
    for index, texture in enumerate(model.textures):
        if normalize_mdx_texture_path(getattr(texture, "path", "")).lower() == normalized:
            return index
    texture = _new_texture()
    texture.path = path
    texture.replaceable_id = 0
    texture.flags = 0
    model.textures.append(texture)
    return len(model.textures) - 1


def get_or_create_team_color_texture(model) -> int:
    for index, texture in enumerate(model.textures):
        if getattr(texture, "replaceable_id", 0) == 1:
            return index
    texture = _new_texture()
    texture.path = ""
    texture.replaceable_id = 1
    texture.flags = 0
    model.textures.append(texture)
    return len(model.textures) - 1


def ensure_standard_hd_slots(model) -> dict[str, int]:
    return {
        "flat_normal": get_or_create_texture_by_path(model, r"RetroTex\FlatNormal.tif"),
        "flat_orm": get_or_create_texture_by_path(model, r"RetroTex\FlatORM.tif"),
        "emissive": get_or_create_texture_by_path(model, r"Textures\Black32.blp"),
        "team_color": get_or_create_team_color_texture(model),
        "environment": get_or_create_texture_by_path(model, r"ReplaceableTextures\EnvironmentMap.blp"),
    }


def convert_material_layers_to_hd(material, texture_indices, static_texture_ids, *, mode=None, source_layer=None, static_filter_mode=0):
    converted = copy.deepcopy(material)
    original_layer = source_layer or material.layers[0]
    effective_mode = original_layer.filter_mode if mode is None else mode
    if "diff" not in texture_indices:
        texture_indices = texture_indices.get(original_layer.texture_id, {})
    texture_indices = {
        "diff": texture_indices.get("diff", original_layer.texture_id),
        "norm": texture_indices.get("norm", static_texture_ids["flat_normal"]),
        "orm": texture_indices.get("orm", static_texture_ids["flat_orm"]),
    }

    diffuse_layer = copy.deepcopy(original_layer)
    diffuse_layer.texture_id = texture_indices["diff"]
    diffuse_layer.filter_mode = effective_mode
    if texture_indices["diff"] == static_texture_ids["team_color"]:
        diffuse_layer.flags = 0

    normal_layer = copy.deepcopy(original_layer)
    normal_layer.texture_id = texture_indices["norm"]
    normal_layer.filter_mode = 0
    normal_layer.flags = 0
    normal_layer.alpha = 1.0

    orm_layer = copy.deepcopy(original_layer)
    orm_layer.texture_id = texture_indices["orm"]
    orm_layer.filter_mode = 0
    orm_layer.flags = 0
    orm_layer.alpha = 1.0

    static_layers = []
    for texture_id in (static_texture_ids["emissive"], static_texture_ids["team_color"], static_texture_ids["environment"]):
        layer = copy.deepcopy(original_layer)
        layer.texture_id = texture_id
        layer.filter_mode = static_filter_mode
        layer.flags = 0
        layer.alpha = 1.0
        static_layers.append(layer)

    converted.layers = [diffuse_layer, normal_layer, orm_layer, *static_layers]
    converted.shader = HD_SHADER
    return converted


def material_has_team_color_layer(material, textures) -> bool:
    return find_replaceable_layer(material, textures, 1) is not None


def convert_model_to_hd(
    model,
    model_path: str,
    output_root: str,
    *,
    search_roots: list[str] | None = None,
    blplab_path: str | None = None,
    prefer_dds: bool = False,
    resolved_sources: dict[str, str] | None = None,
) -> ConversionStats:
    ensure_static_texture_files(output_root)
    search_roots = list(search_roots or [])
    old_textures = list(model.textures)
    building_model = is_building_model_path(model_path)
    legacy_unit_materials = uses_legacy_unit_material_rules(model_path)
    stats = ConversionStats()
    texture_triplets = {}
    material_decisions = []
    team_color_texture_ids = set()
    alpha_texture_ids = set()

    for material in model.materials:
        base_layer = find_material_base_layer(material, old_textures)
        if building_model and base_layer is None and material.layers:
            base_layer = material.layers[0]
        material_decisions.append(base_layer)
        if base_layer is None:
            continue
        texture_id = base_layer.texture_id
        texture = get_texture(old_textures, texture_id)
        if texture is None:
            continue
        if layer_needs_diffuse_alpha(base_layer):
            alpha_texture_ids.add(texture_id)
        if material_uses_replaceable_texture(material, old_textures) and not is_replaceable_texture(texture) and getattr(texture, "path", ""):
            team_color_texture_ids.add(texture_id)

    for base_layer in material_decisions:
        if base_layer is None:
            continue
        texture_id = base_layer.texture_id
        texture = get_texture(old_textures, texture_id)
        if texture is None:
            continue
        if not is_replaceable_texture(texture) and getattr(texture, "path", "") and texture_id not in texture_triplets:
            texture_triplets[texture_id] = ensure_hd_texture_triplet(
                texture,
                model_path,
                output_root,
                search_roots=search_roots,
                blplab_path=blplab_path,
                team_color_mask=texture_id in team_color_texture_ids,
                preserve_diffuse_alpha=texture_id in alpha_texture_ids,
                binary_team_orm_alpha=texture_id in team_color_texture_ids,
                prefer_dds=prefer_dds,
                resolved_sources=resolved_sources,
            )

    model.version = 1000
    model.textures = list(old_textures)
    appended_texture_indices = {}
    for texture_id, triplet in texture_triplets.items():
        if not triplet:
            continue
        appended_texture_indices[texture_id] = append_hd_textures(model, old_textures[texture_id], triplet["virtual_paths"])
        stats.converted_textures += 1

    static_texture_ids = ensure_standard_hd_slots(model)
    new_materials = []
    for material, base_layer in zip(model.materials, material_decisions):
        if base_layer is None:
            preserved = copy.deepcopy(material)
            preserved.shader = ""
            new_materials.append(preserved)
            stats.preserved_materials += 1
            continue

        texture_id = base_layer.texture_id
        indices = appended_texture_indices.get(texture_id, {"diff": texture_id, "norm": static_texture_ids["flat_normal"], "orm": static_texture_ids["flat_orm"]})
        texture = get_texture(old_textures, texture_id)
        if texture is not None and should_force_flat_normal(model_path, texture):
            indices = dict(indices)
            indices["norm"] = static_texture_ids["flat_normal"]

        triplet = texture_triplets.get(texture_id)
        real_layer = find_first_real_texture_layer(material, old_textures)
        team_material = material_has_team_color_layer(material, old_textures) and real_layer is not None
        if team_material and "team_diff" in indices:
            indices = dict(indices)
            indices["diff"] = indices["team_diff"]
            indices["orm"] = indices.get("team_orm", indices["orm"])
        elif layer_needs_diffuse_alpha(base_layer) and "alpha_diff" in indices:
            indices = dict(indices)
            indices["diff"] = indices["alpha_diff"]
        if not legacy_unit_materials and material_uses_replaceable_texture(material, old_textures) and real_layer is not None and "team_diff" in indices:
            indices = dict(indices)
            indices["diff"] = indices["team_diff"]

        if team_material:
            mode = 1
        elif is_replaceable_only_material(material, old_textures):
            mode = 1
        elif not building_model and not legacy_unit_materials and base_layer.filter_mode == 2:
            mode = 1
        elif triplet and triplet["semi_transparent"] and base_layer.filter_mode == 0:
            mode = 1
        else:
            mode = base_layer.filter_mode

        new_materials.append(
            convert_material_layers_to_hd(
                material,
                indices,
                static_texture_ids,
                mode=mode,
                source_layer=base_layer,
                static_filter_mode=1 if building_model else 0,
            )
        )
        stats.converted_materials += 1

    model.materials = new_materials
    repair_model_geometry(model)
    return stats
