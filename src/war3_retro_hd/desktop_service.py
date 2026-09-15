"""Desktop workflow: explicit texture matching, complete packages and safe publication."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import threading
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path, PureWindowsPath

from .converter import convert_model_to_hd
from .i18n import Message as M, error_message, render
from .textures import SUPPORTED_TEXTURE_EXTENSIONS, load_texture_reliable, normalize_mdx_texture_path


class Cancelled(Exception):
    pass


def check_cancel(cancel):
    if cancel is not None and cancel.is_set():
        raise Cancelled(M("stopped"))


def runtime_paths():
    """Find bundled tools, or the existing tools alongside this repository."""
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    repo = Path(__file__).resolve().parents[2]
    scripts = repo.parent / "scripts"
    parser = scripts / "PyMdlxConverter"
    if parser.is_dir() and str(parser) not in sys.path:
        sys.path.insert(0, str(parser))
    for base in (bundle / "tools", scripts):
        if (base / "blplabcl.exe").is_file():
            return str(base / "blplabcl.exe")
    return None


class ParserLog(io.StringIO):
    def __init__(self):
        super().__init__()
        self.failed = False

    def write(self, value):
        if "parsing error" in value.lower() or "traceback" in value.lower():
            self.failed = True
        super().write(value[:max(0, 16000 - self.tell())])
        return len(value)


def load_model(data: bytes):
    runtime_paths()
    from PyMdlxConverter.parsers.mdlx.model import Model
    if data[:4] != b"MDLX":
        raise ValueError(M("invalid_mdx"))
    offset, tags = 4, set()
    while offset < len(data):
        if offset + 8 > len(data):
            raise ValueError(M("incomplete_chunk"))
        tag, size = struct.unpack_from("<4sI", data, offset)
        offset += 8 + size
        if offset > len(data):
            raise ValueError(M("oversized_chunk"))
        tags.add(tag)
    if not {b"VERS", b"MODL"}.issubset(tags):
        raise ValueError(M("missing_chunks"))
    log = ParserLog()
    model = Model(data)
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        model.load()
    if log.failed:
        raise ValueError(M("parse_error", detail=log.getvalue()[-2000:]))
    if model.version not in (800, 900, 1000, 1100, 1200):
        raise ValueError(M("unsupported_version", version=model.version))
    return model


def safe_relative(path: str) -> Path:
    logical = PureWindowsPath(normalize_mdx_texture_path(path))
    if (not logical.parts or logical.is_absolute() or logical.drive or logical.root
            or any(p in (".", "..") or any(c in p for c in ':*?"<>|')
                   or p.endswith((".", " ")) for p in logical.parts)):
        raise ValueError(M("relative_path", path=path))
    if any(PureWindowsPath(part).is_reserved() for part in logical.parts):
        raise ValueError(M("reserved_path", path=path))
    return Path(*logical.parts)


def game_resource(texture) -> bool:
    if getattr(texture, "replaceable_id", 0) != 0:
        return True
    name = normalize_mdx_texture_path(texture.path).casefold()
    return name in {r"textures\black32.blp", r"replaceabletextures\environmentmap.blp"} or name.startswith(
        ("replaceabletextures\\teamcolor\\", "replaceabletextures\\teamglow\\"))


@dataclass
class ModelPlan:
    source: str
    sources: dict[str, str] = field(default_factory=dict)
    game_resources: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class TextureIndex:
    def __init__(self, roots=(), files=(), cancel=None):
        self.roots = list(dict.fromkeys(Path(p).resolve() for p in roots))
        self.files = set(Path(p).resolve() for p in files)
        for root in self.roots:
            if not root.is_dir():
                raise ValueError(M("missing_folder", path=root))
            for path in root.rglob("*"):
                check_cancel(cancel)
                if path.is_file() and path.suffix.lower() in SUPPORTED_TEXTURE_EXTENSIONS:
                    self.files.add(path.resolve())
        self.by_name, self.by_stem = {}, {}
        for path in sorted(self.files):
            if not path.is_file():
                raise ValueError(M("missing_file", path=path))
            self.by_name.setdefault(path.name.casefold(), set()).add(path)
            self.by_stem.setdefault(path.stem.casefold(), set()).add(path)

    def resolve(self, logical, model_dir):
        rel = safe_relative(logical)
        # Exact logical paths take precedence over every basename fallback.
        candidates = self.by_name.get(rel.name.casefold(), set())
        def choose(paths):
            paths = sorted(set(paths))
            if len(paths) > 1:
                raise ValueError(M("ambiguous", logical=logical, paths=paths))
            return paths[0] if paths else None
        for pool, alternate in ((candidates, False), (self.by_stem.get(rel.stem.casefold(), set()), True)):
            matches = []
            for root in [model_dir, *self.roots]:
                target = str(root / rel).casefold()
                matches.extend(p for p in pool if (str(p.with_suffix("")).casefold() == str(Path(target).with_suffix("")).casefold()
                                                   if alternate else str(p).casefold() == target))
            found = choose(matches)
            if found:
                return found
        # Explicit files retain directory suffixes even when image extensions differ.
        stem_candidates = self.by_stem.get(rel.stem.casefold(), set())
        for pool, alternate in ((candidates, False), (stem_candidates, True)):
            suffix_path = rel.with_suffix("") if alternate else rel
            suffix = "\\" + str(suffix_path).replace(os.sep, "\\").casefold()
            found = choose(p for p in pool if str(p.with_suffix("") if alternate else p).replace(os.sep, "\\").casefold().endswith(suffix))
            if found:
                return found
        for pool in (candidates, stem_candidates):
            found = choose(p for p in pool if p.parent == model_dir)
            if found:
                return found
        return choose(candidates) or choose(stem_candidates)


def inspect_models(models, roots=(), files=(), *, progress=lambda message: None, cancel=None):
    paths = list(dict.fromkeys(Path(p).resolve() for p in models))
    if not paths:
        raise ValueError(M("need_models"))
    search_roots = list(roots)
    local_files = list(files)
    for path in paths:
        if path.suffix.lower() != ".mdx" or not path.is_file():
            raise ValueError(M("invalid_model", path=path))
        # Nearby images are automatic; recursively search only selected roots.
        local_files.extend(p for p in path.parent.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_TEXTURE_EXTENSIONS)
        for parent in path.parents:
            if parent.name.lower() == "war3.w3mod":
                search_roots.append(parent)
                break
    progress(M("indexing"))
    index = TextureIndex(search_roots, local_files, cancel)
    plans = []
    for path in paths:
        check_cancel(cancel)
        progress(M("checking_model", name=path.name))
        plan = ModelPlan(str(path))
        try:
            model = load_model(path.read_bytes())
            if any(getattr(m, "shader", "").startswith("Shader_HD") for m in model.materials):
                raise ValueError(M("already_hd"))
            generated_stems = {}
            for texture in model.textures:
                check_cancel(cancel)
                if game_resource(texture):
                    plan.game_resources.append(texture.path or f"Replaceable ID {texture.replaceable_id}")
                    continue
                if not texture.path:
                    raise ValueError(M("empty_texture"))
                safe_relative(texture.path)
                key = normalize_mdx_texture_path(texture.path).casefold()
                source = index.resolve(texture.path, path.parent)
                if source is None:
                    plan.errors.append(M("missing_texture", path=texture.path))
                else:
                    stem = str(PureWindowsPath(key).with_suffix("")).casefold()
                    if stem in generated_stems and generated_stems[stem] != key:
                        plan.errors.append(M("generated_collision", path=texture.path))
                    generated_stems[stem] = key
                    plan.sources[key] = str(source)
        except Cancelled:
            raise
        except Exception as exc:
            plan.errors.append(error_message(exc))
        plans.append(plan)
    return plans


def convert_models(models, roots, files, output_parent, *, progress=lambda message: None, cancel=None, language="zh"):
    blplab = runtime_paths()
    plans = inspect_models(models, roots, files, progress=progress, cancel=cancel)
    errors = [M("model_error", name=Path(p.source).name, detail=error) for p in plans for error in p.errors]
    if errors:
        raise ValueError(M("resolve_errors", details=errors))
    check_cancel(cancel)
    output_parent = Path(output_parent).expanduser().resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    run_dir = output_parent / (datetime.now().strftime("SD-to-HD_%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6])
    run_dir.mkdir()
    report = {"output": str(run_dir), "format": "TIF", "models": [], "cancelled": False}
    for i, plan in enumerate(plans, 1):
        if cancel is not None and cancel.is_set():
            report["cancelled"] = True
            break
        source = Path(plan.source)
        record = {"source": plan.source, "status": "failed"}
        progress(M("converting_model", index=i, total=len(plans), name=source.name))
        try:
            with tempfile.TemporaryDirectory(prefix=".converting-", dir=run_dir) as temp:
                package = Path(temp) / "package"
                package.mkdir()
                model = load_model(source.read_bytes())
                decoded = {}
                resolved = {}
                for texture in model.textures:
                    check_cancel(cancel)
                    if game_resource(texture):
                        continue
                    key = normalize_mdx_texture_path(texture.path).casefold()
                    texture_source = plan.sources[key]
                    # Decode once into the private workspace, never write beside the input.
                    if texture_source not in decoded:
                        image = load_texture_reliable(texture_source, blplab)
                        if image is None:
                            raise ValueError(M("decode_error", path=texture_source))
                        decoded[texture_source] = image
                    rel = safe_relative(texture.path)
                    # Preserve original data when extensions match; otherwise output a real TIF.
                    if rel.suffix.casefold() == Path(texture_source).suffix.casefold():
                        dest = package / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(texture_source, dest)
                    else:
                        rel = rel.with_suffix(".tif")
                        dest = package / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        decoded[texture_source].save(dest, format="TIFF", compression="tiff_deflate")
                        texture.path = str(rel).replace(os.sep, "\\")
                    # Always feed the predecoded RGBA to the converter (BLP alpha remains intact).
                    cache = Path(temp) / "decoded" / (uuid.uuid4().hex + ".tif")
                    cache.parent.mkdir(exist_ok=True)
                    decoded[texture_source].save(cache, format="TIFF")
                    resolved[normalize_mdx_texture_path(texture.path).casefold()] = str(cache)
                stats = convert_model_to_hd(model, str(source), str(package), resolved_sources=resolved)
                check_cancel(cancel)
                data = model.save_mdx()
                verified = load_model(data)
                if verified.version != 1000:
                    raise ValueError(M("output_version"))
                for texture in verified.textures:
                    if not game_resource(texture) and not (package / safe_relative(texture.path)).is_file():
                        raise ValueError(M("missing_output", path=texture.path))
                (package / source.name).write_bytes(data)
                record.update(status="ok", stats=asdict(stats), game_resources=plan.game_resources,
                              textures=[str(p.relative_to(package)) for p in package.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_TEXTURE_EXTENSIONS])
                (package / "manifest.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                final = run_dir / f"{i:03d}_{source.stem}"
                package.rename(final)
                record["output"] = str(final)
                progress(M("model_complete", name=source.name, count=len(record['textures'])))
        except Cancelled:
            report["cancelled"] = True
            break
        except Exception as exc:
            record["error"] = render(error_message(exc), language)
            progress(M("model_failed", name=source.name, detail=error_message(exc)))
        report["models"].append(record)
    report["ok"] = sum(r["status"] == "ok" for r in report["models"])
    report["failed"] = sum(r["status"] != "ok" for r in report["models"])
    report["requested"] = len(plans)
    (run_dir / "conversion_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
