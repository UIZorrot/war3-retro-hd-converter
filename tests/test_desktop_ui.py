import tkinter as tk

import pytest

from war3_retro_hd.desktop import App
from war3_retro_hd.i18n import Message as M
from war3_retro_hd.desktop_service import ModelPlan


def test_desktop_controls_and_async_error_recover():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display is not available")
    root.withdraw()
    app = App(root)
    try:
        app.models = ["model-a.mdx", "model-b.mdx"]
        app.textures = ["a.png", "b.png"]
        app.texture_roots = ["textures"]
        app.refresh()
        app.model_list.selection_set(0)
        app.remove_models()
        assert app.models == ["model-b.mdx"]
        app.texture_list.selection_set(0, 1)
        app.remove_textures()
        assert app.texture_roots == [] and app.textures == ["b.png"]
        app.set_busy(True)
        assert all(str(b.cget("state")) == "disabled" for b in app.buttons)
        app.events.put(("error", "Missing texture"))
        app.events.put(("idle", None))
        app.poll()
        assert not app.busy
        assert all(str(b.cget("state")) == "normal" for b in app.buttons)
        assert "Missing texture" in app.log.get("1.0", "end")
    finally:
        for callback in root.tk.call("after", "info"):
            root.after_cancel(callback)
        root.destroy()


def test_live_language_switch_preserves_inputs_selection_and_job_state(monkeypatch):
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("Tk display is not available")
    root.withdraw()
    app = App(root)
    try:
        assert app.language == "en"
        assert "Model Converter" in root.title()
        assert app.language_picker.get() == "English"
        app.models = ["custom.mdx"]
        app.textures = ["skin.png"]
        app.texture_roots = ["resources"]
        app.output_var.set("custom-output")
        app.last_output = "previous-output"
        app.refresh()
        app.model_list.selection_set(0)
        app.texture_list.selection_set(1)
        app.events.put(("inspection", [ModelPlan("custom.mdx", sources={r"Textures\skin.blp": "skin.png"})]))
        app.poll()
        assert "Textures\\skin.blp → skin.png" in app.log.get("1.0", "end")
        app.set_busy(True)
        app.events.put(("log", M("converting_model", index=1, total=2, name="custom.mdx")))
        app.poll()
        assert "Converting" in app.status_var.get()
        app.language_var.set("中文")
        app.language_picker.event_generate("<<ComboboxSelected>>")
        assert app.language == "zh"
        assert "模型转换" in root.title()
        assert "转换" in app.status_var.get()
        assert "自定义贴图" in app.log.get("1.0", "end")
        assert app.busy and not app.cancel.is_set()
        assert app.models == ["custom.mdx"] and app.textures == ["skin.png"]
        assert app.output_var.get() == "custom-output" and app.last_output == "previous-output"
        assert app.model_list.curselection() == (0,) and app.texture_list.curselection() == (1,)
        assert all(str(b.cget("state")) == "disabled" for b in app.buttons)
        app.set_language("en")
        assert "custom textures" in app.log.get("1.0", "end")
        assert "Converting" in app.status_var.get()
        app.events.put(("error", M("resolve_errors", details=[M("missing_texture", path="Skin.blp")])) )
        app.events.put(("idle", None))
        app.poll()
        assert "Missing texture: Skin.blp" in app.log.get("1.0", "end")
        assert not app.busy
        observed = {}
        def choose(**kwargs):
            observed.update(kwargs)
            return ()
        monkeypatch.setattr("war3_retro_hd.desktop.filedialog.askopenfilenames", choose)
        app.add_models()
        assert observed["title"].startswith("Select SD models")
        app.set_language("zh")
        app.add_models()
        assert observed["title"].startswith("选择 SD 模型")
    finally:
        for callback in root.tk.call("after", "info"):
            root.after_cancel(callback)
        root.destroy()
