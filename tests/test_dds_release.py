from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from war3_retro_hd.dds_release import rewrite_model_retrotex_paths, save_bc3_dds, verify_dds_bc3_header


def test_save_bc3_dds_writes_dxt5_header(tmp_path):
    source = tmp_path / "source.tif"
    dest = tmp_path / "out.dds"
    Image.new("RGBA", (8, 8), (10, 20, 30, 128)).save(source)

    save_bc3_dds(source, dest)

    assert verify_dds_bc3_header(dest)


def test_rewrite_model_retrotex_tif_paths_to_dds():
    model = SimpleNamespace(
        textures=[
            SimpleNamespace(path=r"RetroTex\Footman_diffuse.tif"),
            SimpleNamespace(path=r"RetroTex\Footman_normal.TIF"),
            SimpleNamespace(path=r"Textures\Black32.blp"),
        ]
    )
    stats = SimpleNamespace(rewritten_texture_paths=0)

    rewrite_model_retrotex_paths(model, stats)

    assert model.textures[0].path == r"RetroTex\Footman_diffuse.dds"
    assert model.textures[1].path == r"RetroTex\Footman_normal.dds"
    assert model.textures[2].path == r"Textures\Black32.blp"
    assert stats.rewritten_texture_paths == 2
