from pathlib import Path
from types import SimpleNamespace

from war3_retro_hd.packager import collect_model_texture_paths, copy_referenced_texture, is_local_generated_texture


def test_collect_model_texture_paths_only_keeps_retrotex():
    model = SimpleNamespace(
        textures=[
            SimpleNamespace(path=r"RetroTex\Textures\Footman_diffuse.tif"),
            SimpleNamespace(path=r"Textures\Black32.blp"),
            SimpleNamespace(path=r"ReplaceableTextures\EnvironmentMap.blp"),
            SimpleNamespace(path=""),
        ],
        materials=[
            SimpleNamespace(
                layers=[
                    SimpleNamespace(texture_id=0),
                    SimpleNamespace(texture_id=1),
                    SimpleNamespace(texture_id=2),
                    SimpleNamespace(texture_id=3),
                ]
            )
        ],
    )

    assert collect_model_texture_paths(model) == {r"RetroTex\Textures\Footman_diffuse.tif"}


def test_collect_model_texture_paths_ignores_unused_retrotex_entries():
    model = SimpleNamespace(
        textures=[
            SimpleNamespace(path=r"RetroTex\Used_diffuse.tif"),
            SimpleNamespace(path=r"RetroTex\Unused_alpha_diffuse.tif"),
            SimpleNamespace(path=r"RetroTex\Unused_team_diffuse.tif"),
        ],
        materials=[SimpleNamespace(layers=[SimpleNamespace(texture_id=0)])],
    )

    assert collect_model_texture_paths(model) == {r"RetroTex\Used_diffuse.tif"}


def test_copy_referenced_texture_preserves_retrotex_structure(tmp_path):
    source_root = tmp_path / "Retro"
    source = source_root / "RetroTex" / "Textures" / "Footman_diffuse.tif"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"texture")

    output_dir = tmp_path / "Packaged" / "RUnits" / "human" / "footman"
    ok, result = copy_referenced_texture(r"RetroTex\Textures\Footman_diffuse.tif", source_root, output_dir)

    assert ok
    assert Path(result) == output_dir / "RetroTex" / "Textures" / "Footman_diffuse.tif"
    assert Path(result).read_bytes() == b"texture"


def test_local_generated_texture_detection_is_case_insensitive():
    assert is_local_generated_texture(r"retrotex\units\grunt_diffuse.tif")
    assert not is_local_generated_texture(r"ReplaceableTextures\TeamColor\TeamColor00.blp")
