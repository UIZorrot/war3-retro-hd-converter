"""Source launcher and PyInstaller entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from war3_retro_hd.desktop import main

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        import argparse
        import json
        import tkinter as tk
        from war3_retro_hd.desktop import App
        from war3_retro_hd.desktop_service import convert_models
        parser = argparse.ArgumentParser()
        parser.add_argument("--self-test", action="store_true")
        parser.add_argument("--input", action="append", required=True)
        parser.add_argument("--texture-root", action="append", default=[])
        parser.add_argument("--output", required=True)
        args = parser.parse_args()
        try:
            root = tk.Tk()
            root.withdraw()
            app = App(root)
            assert app.language == "en" and "Model Converter" in root.title()
            app.set_language("zh")
            assert "模型转换" in root.title()
            app.set_language("en")
            root.update_idletasks()
            root.destroy()
            report = convert_models(args.input, args.texture_root, [], args.output, language="en")
            report["gui_initialized"] = True
            report["gui_languages"] = ["en", "zh"]
        except Exception:
            import traceback
            report = {"failed": 1, "cancelled": False, "error": traceback.format_exc()}
        Path(args.output).mkdir(parents=True, exist_ok=True)
        Path(args.output, "self-test.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        raise SystemExit(1 if report["failed"] or report["cancelled"] else 0)
    else:
        main()
