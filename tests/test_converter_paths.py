from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from war3_retro_hd.converter import build_hd_texture_virtual_path, ensure_hd_texture_triplet, should_force_flat_normal


def test_retrotex_path_preserves_logical_source_path():
    assert (
        build_hd_texture_virtual_path(r"Textures\hut.blp", "_diffuse.tif")
        == r"RetroTex\Textures\hut_diffuse.tif"
    )
    assert (
        build_hd_texture_virtual_path(r"Buildings\Other\PigFarm\Hut.blp", "_diffuse.tif")
        == r"RetroTex\Buildings\Other\PigFarm\Hut_diffuse.tif"
    )


def test_team_texture_triplet_uses_source_alpha_for_team_mask(tmp_path):
    source_root = tmp_path / "war3.w3mod"
    texture_dir = source_root / "Textures"
    texture_dir.mkdir(parents=True)
    output_root = tmp_path / "out"
    model_path = tmp_path / "units" / "dummy.mdx"
    model_path.parent.mkdir(parents=True)
    model_path.write_bytes(b"")

    image = Image.new("RGBA", (3, 1))
    image.putdata([(0, 0, 0, 255), (10, 10, 10, 128), (120, 120, 120, 0)])
    image.save(texture_dir / "TeamAlpha.png")

    texture = SimpleNamespace(path=r"Textures\TeamAlpha.blp", replaceable_id=0)
    triplet = ensure_hd_texture_triplet(texture, str(model_path), str(output_root), search_roots=[str(source_root)], team_color_mask=True)

    assert triplet["virtual_paths"]["diff"] == r"RetroTex\Textures\TeamAlpha_diffuse.tif"
    team_diffuse = Image.open(output_root / "RetroTex" / "Textures" / "TeamAlpha_team_diffuse.tif").convert("RGBA")
    team_orm = Image.open(output_root / "RetroTex" / "Textures" / "TeamAlpha_team_orm.tif").convert("RGBA")

    assert team_diffuse.getpixel((0, 0))[:3] == (0, 0, 0)
    assert team_diffuse.getpixel((1, 0))[:3] == (119, 119, 119)
    assert team_diffuse.getpixel((2, 0))[:3] == (160, 160, 160)
    assert [team_orm.getpixel((x, 0))[3] for x in range(3)] == [0, 255, 255]


def test_gnollhut_hut_forces_flat_normal():
    texture = SimpleNamespace(path=r"Textures\hut.blp", replaceable_id=0)
    assert should_force_flat_normal(r"D:\War3\Rbuildings\other\gnollhut2\gnollhut2.mdx", texture)
