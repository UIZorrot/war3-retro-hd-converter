import json
import struct
import threading
from pathlib import Path

import pytest
from PIL import Image

from war3_retro_hd.desktop_service import (
    Cancelled, TextureIndex, convert_models, inspect_models, load_model, runtime_paths, safe_relative,
)


@pytest.fixture
def model_factory():
    runtime_paths()
    pytest.importorskip("PyMdlxConverter")
    from PyMdlxConverter.parsers.mdlx.model import Model
    from PyMdlxConverter.parsers.mdlx.material import Material
    from PyMdlxConverter.parsers.mdlx.layer import Layer
    from PyMdlxConverter.parsers.mdlx.texture import Texture

    def create(path, texture_paths, replaceables=()):
        model = Model(b"")
        # SD materials also occur in version 900; the legacy parser's 800 writer
        # has an unrelated material-size bug. Actual game files are smoke-tested separately.
        model.version = 900
        model.name = "Test"
        for texture_path in texture_paths:
            tex = Texture()
            tex.path = texture_path
            model.textures.append(tex)
        for rid in replaceables:
            tex = Texture()
            tex.replaceable_id = rid
            model.textures.append(tex)
        if texture_paths:
            mat = Material()
            layer = Layer()
            layer.texture_id = 0
            mat.layers = [layer]
            model.materials = [mat]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(model.save_mdx())
        return path
    return create


def picture(path, color=(40, 100, 160, 128)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (4, 4), color).save(path)
    return path


def test_logical_path_beats_wrong_local_basename(tmp_path):
    root = tmp_path / "resources"
    correct = picture(root / "Textures" / "skin.png")
    wrong = picture(tmp_path / "models" / "skin.png")
    index = TextureIndex([root], [wrong])
    assert index.resolve(r"Textures\skin.png", wrong.parent) == correct


def test_ambiguous_basename_is_reported(tmp_path):
    a = picture(tmp_path / "a" / "skin.png")
    b = picture(tmp_path / "b" / "skin.png")
    index = TextureIndex(files=[a, b])
    with pytest.raises(ValueError, match="重名"):
        index.resolve(r"Textures\skin.png", tmp_path / "models")


def test_missing_texture_prevents_output(tmp_path, model_factory):
    model = model_factory(tmp_path / "model.mdx", [r"Textures\missing.blp"])
    with pytest.raises(ValueError, match="缺失贴图"):
        convert_models([model], [], [], tmp_path / "out")
    assert not (tmp_path / "out").exists()


@pytest.mark.parametrize("path", [r"..\escape.png", r"C:\skin.png", r"\skin.png", r"a\..\skin.png", r"a:stream.png", r"CON\skin.png"])
def test_unsafe_texture_paths_rejected(path):
    with pytest.raises(ValueError):
        safe_relative(path)


def test_complete_package_keeps_non_material_textures_and_replaceables(tmp_path, model_factory):
    source = tmp_path / "input"
    model = model_factory(source / "custom.mdx", [r"Textures\skin.blp", r"Particles\spark.png"], [1, 2, 11])
    skin = picture(source / "Textures" / "skin.png")
    spark = picture(source / "Particles" / "spark.png")
    original = {p: p.read_bytes() for p in (model, skin, spark)}
    report = convert_models([model], [source], [], tmp_path / "out")
    assert report["ok"] == 1 and report["failed"] == 0
    package = Path(report["models"][0]["output"])
    result = load_model((package / model.name).read_bytes())
    assert result.version == 1000
    assert result.materials[0].shader == "Shader_HD_DefaultUnit"
    assert {1, 2, 11}.issubset({t.replaceable_id for t in result.textures})
    assert (package / "Particles" / "spark.png").read_bytes() == spark.read_bytes()
    assert (package / "Textures" / "skin.tif").is_file()
    assert (package / "RetroTex" / "Textures" / "skin_diffuse.tif").is_file()
    assert not list(package.parent.glob(".converting-*"))
    assert original == {p: p.read_bytes() for p in original}


def test_same_model_names_and_reruns_do_not_overwrite(tmp_path, model_factory):
    models = [model_factory(tmp_path / str(i) / "same.mdx", ["skin.png"]) for i in range(2)]
    for i, model in enumerate(models):
        picture(model.parent / "skin.png", (30 + i * 100, 50, 60, 255))
    report = convert_models(models, [], [], tmp_path / "out")
    assert report["ok"] == 2
    paths = [Path(r["output"]) for r in report["models"]]
    assert paths[0] != paths[1]
    assert (paths[0] / "skin.png").read_bytes() != (paths[1] / "skin.png").read_bytes()
    rerun = convert_models(models[:1], [], [], tmp_path / "out")
    assert rerun["output"] != report["output"]
    assert all(p.is_dir() for p in paths)


def test_bad_image_produces_failed_report_without_package(tmp_path, model_factory):
    model = model_factory(tmp_path / "bad.mdx", ["skin.png"])
    (tmp_path / "skin.png").write_bytes(b"invalid image")
    report = convert_models([model], [], [], tmp_path / "out")
    assert report["failed"] == 1 and report["ok"] == 0
    assert "无法解码" in report["models"][0]["error"]
    assert not list(Path(report["output"]).glob("*/bad.mdx"))
    assert json.loads((Path(report["output"]) / "conversion_report.json").read_text(encoding="utf-8"))["failed"] == 1


def test_cancel_before_inspection_writes_nothing(tmp_path, model_factory):
    model = model_factory(tmp_path / "model.mdx", [])
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(Cancelled):
        convert_models([model], [], [], tmp_path / "out", cancel=cancel)
    assert not (tmp_path / "out").exists()


def test_parser_error_that_upstream_swallows_is_rejected():
    runtime_paths()
    pytest.importorskip("PyMdlxConverter")
    malformed = b"MDLX" + struct.pack("<4sII", b"VERS", 4, 800) + struct.pack("<4sII", b"MODL", 4, 0)
    with pytest.raises(ValueError, match="解析失败"):
        load_model(malformed)


def test_hd_input_is_rejected(tmp_path, model_factory):
    model = model_factory(tmp_path / "model.mdx", ["skin.png"])
    picture(tmp_path / "skin.png")
    report = convert_models([model], [], [], tmp_path / "out")
    output = Path(report["models"][0]["output"]) / model.name
    plans = inspect_models([output])
    assert "已经包含 HD" in plans[0].errors[0]


def test_version_1200_sd_input_is_accepted(tmp_path, model_factory):
    path = model_factory(tmp_path / "current-sd.mdx", [])
    data = bytearray(path.read_bytes())
    struct.pack_into("<I", data, 12, 1200)
    path.write_bytes(data)
    assert load_model(data).version == 1200
    assert inspect_models([path])[0].errors == []


@pytest.mark.parametrize("filename", ["skin.png", "SKIN.PNG", "skin.tif"])
def test_unique_imported_filename_matches_without_original_folders(tmp_path, filename):
    imported = picture(tmp_path / "loose-files" / filename)
    index = TextureIndex(files=[imported])
    assert index.resolve(r"Textures\Original\Skin.blp", tmp_path / "models") == imported


def test_imported_files_use_directory_suffix_with_alternate_extension(tmp_path):
    correct = picture(tmp_path / "imported" / "Textures" / "A" / "skin.png")
    other = picture(tmp_path / "imported" / "Textures" / "B" / "skin.png")
    index = TextureIndex(files=[correct, other])
    assert index.resolve(r"Textures\A\skin.blp", tmp_path / "models") == correct


def test_ambiguous_alternate_extensions_are_not_guessed(tmp_path):
    a = picture(tmp_path / "loose" / "skin.png")
    b = picture(tmp_path / "loose" / "skin.tif")
    index = TextureIndex(files=[a, b])
    with pytest.raises(ValueError, match="重名"):
        index.resolve(r"Textures\skin.blp", tmp_path / "models")


def test_english_conversion_failure_report(tmp_path, model_factory):
    model = model_factory(tmp_path / "bad.mdx", ["skin.png"])
    (tmp_path / "skin.png").write_bytes(b"not an image")
    report = convert_models([model], [], [], tmp_path / "out", language="en")
    assert report["models"][0]["error"].startswith("Cannot decode texture:")
