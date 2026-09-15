"""Command line interface for War3 Retro HD Converter."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

from .converter import convert_model_to_hd
from .dds_release import build_dds_release
from .packager import package_model_tree
from .textures import iter_texture_files


def add_pymdlx_path(path: str | None) -> None:
    if path:
        sys.path.insert(0, path)


def load_model_class():
    try:
        from PyMdlxConverter.parsers.mdlx.model import Model
    except ModuleNotFoundError as exc:
        raise SystemExit("PyMdlxConverter is not importable. Pass --pymdlx-path or set PYTHONPATH.") from exc
    return Model


def collect_mdx_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.mdx") if path.is_file())


def parse_path_rewrite(values: list[str] | None) -> dict[str, str]:
    rewrites = {}
    for value in values or []:
        if "=" not in value:
            raise SystemExit(f"Invalid --path-rewrite value: {value!r}. Expected from=to.")
        src, dst = value.split("=", 1)
        rewrites[src.lower()] = dst
    return rewrites


def output_path_for(source_path: Path, source_root: Path, output_root: Path, rewrites: dict[str, str]) -> Path:
    rel = source_path.relative_to(source_root)
    parts = list(rel.parts)
    if parts and parts[0].lower() in rewrites:
        parts[0] = rewrites[parts[0].lower()]
    return output_root.joinpath(*parts)


def convert_one(args, source_path: Path, source_root: Path, output_root: Path, rewrites: dict[str, str]):
    Model = load_model_class()
    model = Model(source_path.read_bytes())
    model.load()
    stats = convert_model_to_hd(
        model,
        str(source_path),
        str(output_root),
        search_roots=[str(source_root)],
        blplab_path=args.blplab,
        prefer_dds=args.prefer_dds,
    )
    out_path = output_path_for(source_path, source_root, output_root, rewrites)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(model.save_mdx())
    return stats, out_path


def command_convert_file(args) -> int:
    add_pymdlx_path(args.pymdlx_path)
    source_path = Path(args.input).resolve()
    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root).resolve()
    rewrites = parse_path_rewrite(args.path_rewrite)
    stats, out_path = convert_one(args, source_path, source_root, output_root, rewrites)
    print(
        f"OK {source_path} -> {out_path} "
        f"materials={stats.converted_materials}/{stats.preserved_materials} textures={stats.converted_textures}"
    )
    return 0


def command_convert_tree(args) -> int:
    add_pymdlx_path(args.pymdlx_path)
    input_root = Path(args.input_root).resolve()
    source_root = Path(args.source_root).resolve()
    output_root = Path(args.output_root).resolve()
    rewrites = parse_path_rewrite(args.path_rewrite)
    mdx_files = collect_mdx_files(input_root)
    if args.limit is not None:
        mdx_files = mdx_files[: args.limit]

    results = []
    for index, source_path in enumerate(mdx_files, start=1):
        started_at = time.time()
        try:
            stats, out_path = convert_one(args, source_path, source_root, output_root, rewrites)
            result = {
                "source_path": str(source_path),
                "relative_path": str(source_path.relative_to(source_root)),
                "status": "ok",
                "output_path": str(out_path),
                "converted_materials": stats.converted_materials,
                "preserved_materials": stats.preserved_materials,
                "converted_textures": stats.converted_textures,
                "elapsed_seconds": round(time.time() - started_at, 3),
            }
            print(f"[{index}/{len(mdx_files)}] OK {result['relative_path']} textures={stats.converted_textures}")
        except BaseException as exc:
            result = {
                "source_path": str(source_path),
                "relative_path": str(source_path.relative_to(source_root)),
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
                "elapsed_seconds": round(time.time() - started_at, 3),
            }
            print(f"[{index}/{len(mdx_files)}] FAIL {result['relative_path']} {result['error']}")
        results.append(result)

    report_path = Path(args.report or output_root / "_reports" / "conversion_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total_models": len(results),
        "ok_models": sum(1 for item in results if item["status"] == "ok"),
        "failed_models": sum(1 for item in results if item["status"] != "ok"),
        "converted_materials": sum(item.get("converted_materials", 0) for item in results),
        "preserved_materials": sum(item.get("preserved_materials", 0) for item in results),
        "converted_textures": sum(item.get("converted_textures", 0) for item in results),
    }
    report_path.write_text(json.dumps({"summary": summary, "results": results}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Finished total={summary['total_models']} ok={summary['ok_models']} failed={summary['failed_models']} report={report_path}")
    return 1 if summary["failed_models"] else 0


def command_audit_textures(args) -> int:
    root = Path(args.source_root).resolve()
    by_name = defaultdict(list)
    for path in iter_texture_files(root):
        by_name[path.stem.lower()].append(path)
    duplicates = {name: paths for name, paths in by_name.items() if len(paths) > 1}
    payload = []
    for name, paths in sorted(duplicates.items()):
        payload.append({"basename": name, "paths": [str(path.relative_to(root)) for path in sorted(paths)]})
    text = json.dumps({"root": str(root), "duplicate_basenames": payload}, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    print(text)
    return 0


def command_validate_mdx(args) -> int:
    add_pymdlx_path(args.pymdlx_path)
    Model = load_model_class()
    root = Path(args.root).resolve()
    files = collect_mdx_files(root) if root.is_dir() else [root]
    bad = []
    versions = defaultdict(int)
    pivot_bad = 0
    for path in files:
        try:
            model = Model(path.read_bytes())
            model.load()
            versions[str(model.version)] += 1
            id_object_count = sum(len(getattr(model, name, [])) for name in (
                "bones", "lights", "helpers", "attachments", "particle_emitters",
                "particle_emitters2", "particle_emitters_popcorn", "ribbon_emitters",
                "event_objects", "collision_shapes",
            ))
            if len(getattr(model, "pivot_points", [])) < id_object_count:
                pivot_bad += 1
        except BaseException as exc:
            bad.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
    print(json.dumps({"total": len(files), "versions": dict(versions), "bad_count": len(bad), "pivot_bad_count": pivot_bad, "bad": bad[:50]}, indent=2, ensure_ascii=False))
    return 1 if bad else 0


def command_package_models(args) -> int:
    add_pymdlx_path(args.pymdlx_path)
    Model = load_model_class()
    records = package_model_tree(
        args.input_root,
        args.source_root,
        args.output_root,
        Model,
        limit=args.limit,
    )
    payload = {
        "input_root": str(Path(args.input_root).resolve()),
        "source_root": str(Path(args.source_root).resolve()),
        "output_root": str(Path(args.output_root).resolve()),
        "summary": {
            "packages": len(records),
            "models": sum(len(record.models) for record in records),
            "copied_textures": sum(len(record.copied_textures) for record in records),
            "missing_textures": sum(len(record.missing_textures) for record in records),
        },
        "packages": [record.__dict__ for record in records],
    }
    report_path = Path(args.report or Path(args.output_root) / "_reports" / "package_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        f"Packaged packages={payload['summary']['packages']} models={payload['summary']['models']} "
        f"textures={payload['summary']['copied_textures']} missing={payload['summary']['missing_textures']} "
        f"report={report_path}"
    )
    return 1 if payload["summary"]["missing_textures"] else 0


def command_make_dds_release(args) -> int:
    add_pymdlx_path(args.pymdlx_path)
    Model = load_model_class()
    payload = build_dds_release(args.source_root, args.output_root, Model)
    print(
        f"DDS release copied_files={payload['copied_files']} converted_textures={payload['converted_textures']} "
        f"rewritten_models={payload['rewritten_models']} rewritten_texture_paths={payload['rewritten_texture_paths']} "
        f"failed_textures={len(payload['failed_textures'])} failed_models={len(payload['failed_models'])} "
        f"dds_files={payload['dds_header_summary']['dds_files']} report={payload['report_path']}"
    )
    return 1 if payload["failed_textures"] or payload["failed_models"] or payload["dds_header_summary"]["bad_sample_headers"] else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="war3-retro-hd")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common_convert_flags(p):
        p.add_argument("--source-root", required=True)
        p.add_argument("--output-root", required=True)
        p.add_argument("--pymdlx-path")
        p.add_argument("--blplab")
        p.add_argument("--prefer-dds", action="store_true", help="Write generated textures as DXT5 DDS when Pillow supports it.")
        p.add_argument("--path-rewrite", action="append", help="Rewrite first output path segment, e.g. buildings=Rbuildings.")

    p = sub.add_parser("convert-file")
    p.add_argument("--input", required=True)
    add_common_convert_flags(p)
    p.set_defaults(func=command_convert_file)

    p = sub.add_parser("convert-tree")
    p.add_argument("--input-root", required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--report")
    add_common_convert_flags(p)
    p.set_defaults(func=command_convert_tree)

    p = sub.add_parser("audit-textures")
    p.add_argument("--source-root", required=True)
    p.add_argument("--output")
    p.set_defaults(func=command_audit_textures)

    p = sub.add_parser("validate-mdx")
    p.add_argument("--root", required=True)
    p.add_argument("--pymdlx-path")
    p.set_defaults(func=command_validate_mdx)

    p = sub.add_parser("package-models")
    p.add_argument("--input-root", required=True, help="Root to scan for model package directories, e.g. Retro/RUnits.")
    p.add_argument("--source-root", required=True, help="Converted asset root containing shared RetroTex and model folders.")
    p.add_argument("--output-root", required=True, help="Destination root for standalone package folders.")
    p.add_argument("--pymdlx-path")
    p.add_argument("--limit", type=int)
    p.add_argument("--report")
    p.set_defaults(func=command_package_models)

    p = sub.add_parser("make-dds-release")
    p.add_argument("--source-root", required=True, help="Converted Retro root containing RUnits/Rbuildings and shared RetroTex.")
    p.add_argument("--output-root", required=True, help="Destination root for DDS/BC3 release.")
    p.add_argument("--pymdlx-path")
    p.set_defaults(func=command_make_dds_release)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
