"""English/Chinese Tk application. Run with python -m war3_retro_hd.desktop."""
from __future__ import annotations

import os
import queue
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from .desktop_service import Cancelled, convert_models, inspect_models, runtime_paths
from .i18n import Message as M, render, error_message


class App:
    def __init__(self, root):
        self.root = root
        self.models, self.textures, self.texture_roots = [], [], []
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.last_output = None
        self.buttons = []
        self.language = "en"
        self.localized_widgets = []
        self.log_messages = []
        self.status_message = M("ready")
        root.title(self.t("title"))
        root.geometry("1000x820")
        root.minsize(820, 740)
        root.configure(bg="#f2f5f9")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#f2f5f9")
        style.configure("TLabel", background="#f2f5f9", font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 10), padding=(12, 7))
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 23, "bold"), foreground="#172238")
        style.configure("Section.TLabel", font=("Microsoft YaHei UI", 11, "bold"), foreground="#172238")
        style.configure("Accent.TButton", background="#285ee8", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1948bf"), ("disabled", "#a9b5cc")])

        page = ttk.Frame(root, padding=24)
        page.pack(fill="both", expand=True)
        page.columnconfigure(0, weight=1)
        page.rowconfigure(8, weight=1)
        title_row = ttk.Frame(page)
        title_row.grid(row=0, column=0, sticky="ew")
        ttk.Label(title_row, text="SD → HD", style="Title.TLabel").pack(side="left")
        self.language_var = tk.StringVar(value="English")
        self.language_picker = ttk.Combobox(title_row, textvariable=self.language_var, values=("English", "中文"), state="readonly", width=10, font=("Microsoft YaHei UI", 10))
        self.language_picker.pack(side="left", padx=(22, 0))
        self.language_picker.bind("<<ComboboxSelected>>", lambda event: self.set_language("zh" if self.language_var.get() == "中文" else "en"))
        subtitle = self.label(page, "subtitle", foreground="#526078", wraplength=900)
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 18))

        self.model_list = self.section(page, 2, "models", [
            ("pick_models", self.add_models), ("model_folder", self.add_model_folder), ("remove", self.remove_models)])
        self.texture_list = self.section(page, 3, "textures", [
            ("pick_textures", self.add_textures), ("texture_folder", self.add_texture_folder), ("remove", self.remove_textures)])
        hint = self.label(page, "matching_hint", foreground="#526078", wraplength=900)
        hint.grid(row=4, column=0, sticky="w", pady=(0, 12))

        output = ttk.Frame(page)
        output.grid(row=5, column=0, sticky="ew", pady=(0, 12))
        output.columnconfigure(1, weight=1)
        self.label(output, "output", style="Section.TLabel").grid(row=0, column=0, padx=(0, 12))
        self.output_var = tk.StringVar(value=str(Path.home() / "Documents" / "War3-HD-Output"))
        self.output_entry = ttk.Entry(output, textvariable=self.output_var, font=("Microsoft YaHei UI", 10))
        self.output_entry.grid(row=0, column=1, sticky="ew")
        self.button(output, "browse", self.choose_output).grid(row=0, column=2, padx=(10, 0))

        actions = ttk.Frame(page)
        actions.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        self.button(actions, "check", lambda: self.start(False)).pack(side="left")
        self.button(actions, "convert", lambda: self.start(True), "Accent.TButton").pack(side="left", padx=10)
        self.stop_button = self.localize(ttk.Button(actions, command=self.stop, state="disabled"), "stop")
        self.stop_button.pack(side="left")
        self.open_button = self.localize(ttk.Button(actions, command=self.open_output, state="disabled"), "open")
        self.open_button.pack(side="right")

        self.status_var = tk.StringVar(value=render(self.status_message, self.language))
        status_label = ttk.Label(page, textvariable=self.status_var, wraplength=900)
        status_label.grid(row=7, column=0, sticky="w", pady=(0, 8))
        self.log = ScrolledText(page, height=8, wrap="word", bg="#ffffff", fg="#26364d", relief="flat", font=("Microsoft YaHei UI", 10), padx=12, pady=10, state="disabled")
        self.log.grid(row=8, column=0, sticky="nsew")
        self.bar = ttk.Progressbar(page, mode="indeterminate")
        self.bar.grid(row=9, column=0, sticky="ew", pady=(10, 0))
        footer = self.label(page, "footer", foreground="#526078", wraplength=900)
        footer.grid(row=10, column=0, sticky="w", pady=(8, 0))
        page.bind("<Configure>", lambda event: [label.configure(wraplength=max(300, event.width - 48)) for label in (subtitle, hint, status_label, footer)])
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.after(100, self.poll)

    def t(self, key, **values):
        return render(M(key, **values), self.language)

    def localize(self, widget, key):
        self.localized_widgets.append((widget, key))
        widget.configure(text=self.t(key))
        return widget

    def label(self, parent, key, **options):
        return self.localize(ttk.Label(parent, **options), key)

    def set_status(self, message):
        self.status_message = message
        self.status_var.set(render(message, self.language))

    def set_language(self, language):
        self.language = language
        self.language_var.set("中文" if language == "zh" else "English")
        self.root.title(self.t("title"))
        for widget, key in self.localized_widgets:
            widget.configure(text=self.t(key))
        self.set_status(self.status_message)
        self.refresh()
        self.render_log()

    def button(self, parent, key, command, style="TButton"):
        button = self.localize(ttk.Button(parent, command=command, style=style), key)
        self.buttons.append(button)
        return button

    def section(self, parent, row, title, buttons):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        frame.columnconfigure(0, weight=1)
        header = ttk.Frame(frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 7))
        self.label(header, title, style="Section.TLabel").pack(side="left")
        for label, command in buttons:
            self.button(header, label, command).pack(side="left", padx=(12, 0))
        listing = tk.Listbox(frame, height=4, selectmode="extended", font=("Microsoft YaHei UI", 10), bg="white", fg="#26364d", relief="flat", borderwidth=0, exportselection=False)
        listing.grid(row=1, column=0, sticky="ew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=listing.yview)
        scroll.grid(row=1, column=1, sticky="ns")
        listing.configure(yscrollcommand=scroll.set)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=listing.xview)
        horizontal.grid(row=2, column=0, sticky="ew")
        listing.configure(xscrollcommand=horizontal.set)
        return listing

    def refresh(self):
        selected_models = self.model_list.curselection()
        selected_textures = self.texture_list.curselection()
        self.model_list.delete(0, "end")
        for path in self.models:
            self.model_list.insert("end", path)
        self.texture_list.delete(0, "end")
        for path in self.texture_roots:
            self.texture_list.insert("end", self.t("folder_item", path=path))
        for path in self.textures:
            self.texture_list.insert("end", self.t("texture_item", path=path))
        for i in selected_models:
            self.model_list.selection_set(i)
        for i in selected_textures:
            self.texture_list.selection_set(i)

    def add_models(self):
        paths = filedialog.askopenfilenames(title=self.t("models_dialog"), filetypes=[(self.t("model_type"), "*.mdx")])
        self.models = list(dict.fromkeys(self.models + list(paths)))
        self.refresh()

    def add_model_folder(self):
        path = filedialog.askdirectory(title=self.t("model_folder_dialog"))
        if path:
            self.run_worker(lambda: ("models", [str(p) for p in Path(path).rglob("*") if p.is_file() and p.suffix.lower() == ".mdx"]))

    def remove_models(self):
        for i in reversed(self.model_list.curselection()):
            del self.models[i]
        self.refresh()

    def add_textures(self):
        paths = filedialog.askopenfilenames(title=self.t("textures_dialog"), filetypes=[(self.t("texture_type"), "*.blp *.dds *.tif *.tiff *.png *.tga *.jpg *.jpeg *.bmp"), (self.t("all_files"), "*.*")])
        self.textures = list(dict.fromkeys(self.textures + list(paths)))
        self.refresh()

    def add_texture_folder(self):
        path = filedialog.askdirectory(title=self.t("texture_folder_dialog"))
        if path:
            self.texture_roots = list(dict.fromkeys(self.texture_roots + [path]))
            self.refresh()

    def remove_textures(self):
        count = len(self.texture_roots)
        for i in reversed(self.texture_list.curselection()):
            if i < count:
                del self.texture_roots[i]
            else:
                del self.textures[i - count]
        self.refresh()

    def choose_output(self):
        path = filedialog.askdirectory(title=self.t("output_dialog"))
        if path:
            self.output_var.set(path)

    def append_log(self, message):
        self.log_messages.append(message)
        self.log_messages = self.log_messages[-1000:]
        self.render_log()

    def render_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.insert("end", "\n".join(render(message, self.language) for message in self.log_messages) + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_busy(self, busy):
        self.busy = busy
        for button in self.buttons:
            button.configure(state="disabled" if busy else "normal")
        self.output_entry.configure(state="disabled" if busy else "normal")
        self.stop_button.configure(state="normal" if busy else "disabled")
        if busy:
            self.bar.start(15)
        else:
            self.bar.stop()

    def run_worker(self, work):
        if self.busy:
            return
        self.cancel.clear()
        self.set_busy(True)
        self.set_status(M("working"))
        def worker():
            try:
                self.events.put(work())
            except Cancelled:
                self.events.put(("stopped", None))
            except Exception as exc:
                self.events.put(("error", error_message(exc)))
            finally:
                self.events.put(("idle", None))
        threading.Thread(target=worker, daemon=True).start()

    def start(self, convert):
        if not self.models:
            self.append_log(M("need_models"))
            return
        if convert and not self.output_var.get().strip():
            self.append_log(M("need_output"))
            return
        models, roots, textures = list(self.models), list(self.texture_roots), list(self.textures)
        output = self.output_var.get().strip()
        report_language = self.language
        def progress(message):
            self.events.put(("log", message))
        def work():
            if convert:
                return "result", convert_models(models, roots, textures, output, progress=progress, cancel=self.cancel, language=report_language)
            return "inspection", inspect_models(models, roots, textures, progress=progress, cancel=self.cancel)
        self.run_worker(work)

    def poll(self):
        for _ in range(100):
            try:
                kind, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind == "idle":
                self.set_busy(False)
            elif kind == "log":
                self.append_log(value)
                self.set_status(value)
            elif kind == "models":
                self.models = list(dict.fromkeys(self.models + value))
                self.refresh()
                self.set_status(M("models_added", count=len(self.models)))
            elif kind == "inspection":
                errors = sum(len(p.errors) for p in value)
                for plan in value:
                    self.append_log(M("inspection_model", name=Path(plan.source).name, textures=len(plan.sources), resources=len(plan.game_resources)))
                    for logical, source in plan.sources.items():
                        self.append_log(M("mapping", logical=logical, source=source))
                    for error in plan.errors:
                        self.append_log(M("indented", detail=error))
                self.set_status(M("checked" if errors else "checked_ready", models=len(value), errors=errors))
                self.append_log(self.status_message)
            elif kind == "result":
                self.last_output = value["output"]
                self.open_button.configure(state="normal")
                self.set_status(M("summary", state=M("stopped" if value["cancelled"] else "complete"), ok=value["ok"], failed=value["failed"], pending=value["requested"] - len(value["models"])))
                self.append_log(self.status_message)
                self.append_log(M("output_log", path=self.last_output))
            elif kind == "stopped":
                self.set_status(M("stopped"))
            elif kind == "error":
                self.set_status(M("error_status"))
                self.append_log(value)
        self.root.after(100, self.poll)

    def stop(self):
        self.cancel.set()
        self.set_status(M("stopping"))

    def open_output(self):
        if self.last_output and Path(self.last_output).is_dir():
            os.startfile(self.last_output)

    def close(self):
        if self.busy:
            self.stop()
            self.append_log(M("closing"))
        else:
            self.root.destroy()


def main():
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    root = tk.Tk()
    try:
        runtime_paths()
        from PyMdlxConverter.parsers.mdlx.model import Model
        App(root)
        root.mainloop()
    except Exception as exc:
        messagebox.showerror(render(M("startup_title")), render(M("startup_error", error=error_message(exc))))
        root.destroy()
        raise


if __name__ == "__main__":
    main()
