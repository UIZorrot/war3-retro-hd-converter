# War3 Retro HD Converter

War3 Retro HD Converter is a Python toolkit for converting Warcraft III Reforged SD MDX models into HD-material MDX models while preserving the original SD geometry, animation, UVs, and game resource semantics.

The converter was built for replacing models under `war3.w3mod` with HD shader materials and generated PBR-compatible texture triplets.

## Download / 下载

Get the Windows x64 portable app from [GitHub Releases](https://github.com/UIZorrot/war3-retro-hd-converter/releases/latest).
Download `War3RetroHD-Windows-x64.zip`, extract the entire archive, and run `War3RetroHD.exe`. No Python installation is required. Keep the `_internal` folder beside the executable.

从 [Release 页面](https://github.com/UIZorrot/war3-retro-hd-converter/releases/latest)下载 `War3RetroHD-Windows-x64.zip`，完整解压后运行 `War3RetroHD.exe`。无需安装 Python。
版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## Windows 小程序（中英双语 / English & Chinese）

本地便携版入口：`dist/War3RetroHD/War3RetroHD.exe`。双击即可使用，无需另外安装 Python。
移动程序时请复制整个 `War3RetroHD` 文件夹，保留旁边的 `_internal`。

启动默认 **English**。标题旁的 **English / 中文** 下拉框可以随时切换语言，界面、状态和已有日志同步更新；已选文件、输出目录和正在运行的任务保持不变。报告中的错误说明使用开始转换时选择的语言。

The desktop app starts in **English**. Use the language selector beside **SD → HD** to switch to Chinese at any time. Selected files and running jobs are preserved. Choose **Select MDX…**, add textures or texture folders, then click **Check textures** or **Convert to HD**.

1. **添加模型**：多选 `.mdx`，或选择一个模型文件夹递归添加。主模型与 portrait 都可以添加。
2. **添加贴图**：多选贴图文件，或添加一个或多个资源根目录。自动查找模型同目录的贴图；对位于 `war3.w3mod` 中的模型会自动识别该资源根目录。
3. **检查贴图**：列出缺失贴图与同名冲突。保留原目录结构可以准确匹配同名贴图。
4. **一键转换**：输出位置下创建一个新的 `SD-to-HD_日期_时间_编号` 文件夹，每个模型有独立子目录。成功后点击“打开输出文件夹”。

### 贴图自动匹配 / Automatic texture matching

模型引用 `Textures\Footman.blp` 时，直接添加唯一的 `Footman.blp` 即可，不需要手动创建原目录。
也支持同名不同扩展名，例如 `Footman.png`、`Footman.dds`、`Footman.tif`，并且不区分大小写。输出时自动写入对应的包内路径。

匹配顺序为：资源根目录下的完整逻辑路径（允许替代扩展名），导入文件的目录后缀，模型同目录，最后按唯一文件名或不带扩展名的名称匹配。
同一优先级有多个候选时会提示冲突，不会任意选一张。多张同名贴图应保留各自目录并添加相应资源根目录。
“检查贴图”会显示 **模型引用 → 实际文件**，便于确认匹配结果。

Unique filenames match automatically regardless of case, even when the image extension differs from the model reference. For example, `Footman.png` can satisfy `Textures\Footman.blp`. Directory paths take precedence; ambiguous duplicates are reported. **Check textures** shows each reference and the actual matched file.

每个模型包包含 HD `.mdx`、`RetroTex` 中的 TIF 材质贴图、模型贴图表中的原始自定义贴图，以及 `manifest.json`。主模型与 portrait 分别打包。总结果写入 `conversion_report.json`。
队伍颜色、队伍光晕、Black32、EnvironmentMap 等游戏资源保留游戏引用，不复制为普通贴图。粒子等使用的自定义贴图也会收集。

转换保留原有造型与动画，生成 HD 材质，不增加网格细节或自动放大贴图。默认使用现有转换算法与 TIF 输出。
原输入文件保持不变；再次运行会创建新的输出目录。缺图或重名冲突会阻止开始转换；损坏贴图、模型解析或输出校验失败会记入报告，不发布该模型的半成品。
“检查贴图”检查引用和路径，贴图实际解码及输出校验在转换时执行。
程序处理 MDX 贴图表中的资源；模型引用的外部子模型、声音和 FaceFX 文件不在此版本的自动收集范围内。

### 从源码运行或重新打包

```powershell
python -m pip install -e .[dev]
python launch_desktop.pyw

# 使用精简环境构建便携版，复用相邻 scripts 中的 PyMdlxConverter 与 BLP Lab
python -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -e .[dev] pyinstaller
.\.venv-build\Scripts\python.exe build_desktop.py
```

依赖包括 Python 的 Tk、numpy、Pillow、python-dateutil、PyMdlxConverter。
源码模式自动发现 `../scripts/PyMdlxConverter`、`../scripts/blplabcl.exe`；打包版本包含所需运行环境和本地工具。
向他人分发前需核对 PyMdlxConverter、BLP Lab 及其 DLL 的分发许可；本仓库不纳入游戏模型与贴图。

便携版可运行包含真实转换与 Tk 初始化的诊断：

```powershell
.\dist\War3RetroHD\War3RetroHD.exe --self-test --input "D:\assets\model.mdx" --texture-root "D:\assets" --output "D:\output\diagnostics"
```

此模式实际生成输出，并在指定目录写入 `self-test.json`，正常退出码为 0。

## Features

- Converts MDX model version to `1000` for HD material compatibility.
- Rebuilds SD materials as HD shader layers using `Shader_HD_DefaultUnit`.
- Generates `diffuse`, `alpha_diffuse`, `team_diffuse`, `normal`, `orm`, and `team_orm` textures.
- Writes generated textures under `RetroTex` while preserving logical source paths to prevent basename collisions.
- Keeps Warcraft replaceable textures, team color, team glow, and environment maps as game-managed resources.
- Recalculates pivot points, extents, normals, and tangents after conversion.
- Supports `.dds`, `.blp`, `.tif`, `.png`, `.tga`, and common image formats through Pillow plus optional BLP Lab CLI.
- Provides duplicate texture basename auditing for old conversion output issues.

## Requirements

- Python 3.10+
- `numpy`
- `Pillow`
- PyMdlxConverter available on `PYTHONPATH` or passed with `--pymdlx-path`
- Optional: `blplabcl.exe` for reliable BLP conversion

This repository intentionally does not vendor PyMdlxConverter. If your PyMdlxConverter copy is inside another workspace, pass the path that contains the `PyMdlxConverter` package:

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter" `
  --blplab "D:\Quenching\LSON\scripts\blplabcl.exe"
```

## Install For Development

```powershell
cd D:\Quenching\LSON\war3-retro-hd-converter
python -m pip install -e .[dev]
```

## Convert One Model

```powershell
python -m war3_retro_hd.cli convert-file `
  --input "D:\Quenching\LSON\Pack\war3.w3mod\units\human\footman\footman.mdx" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

## Convert Units And Buildings

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "D:\Quenching\LSON\Pack\war3.w3mod\units" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

By default, converted paths preserve the input path relative to `--source-root`. To write buildings under `Rbuildings`, use:

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "D:\Quenching\LSON\Pack\war3.w3mod\buildings" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --path-rewrite "buildings=Rbuildings" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

## Audit Duplicate Texture Names

Older prototypes wrote every generated texture as `RetroTex/<basename>_*.tif`, which causes wrong textures when different source paths share the same basename. This converter writes `RetroTex/<source logical path>_*.tif`.

Run:

```powershell
python -m war3_retro_hd.cli audit-textures `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod"
```

## Package Each Model Directory

After conversion, you can split the result into standalone model folders. Each output folder contains the `.mdx` files from one model directory plus a local `RetroTex` folder containing only the generated textures referenced by those models.

```powershell
python -m war3_retro_hd.cli package-models `
  --input-root "D:\Quenching\QM\3.3\Retro" `
  --source-root "D:\Quenching\QM\3.3\Retro" `
  --output-root "D:\Quenching\QM\3.3\Retro_Packaged" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

The packager copies only `RetroTex\...` references. Warcraft-managed resources such as `Textures\Black32.blp`, `ReplaceableTextures\EnvironmentMap.blp`, and team color replaceables are left as game resources.

## Build A Shared RetroTex DDS/BC3 Release

If you want one shared `RetroTex` folder instead of per-model texture folders, build a DDS release from the converted TIF output:

```powershell
python -m war3_retro_hd.cli make-dds-release `
  --source-root "D:\Quenching\QM\3.3\Retro" `
  --output-root "D:\Quenching\QM\3.3\Retro_DDS_BC3" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

This copies the model tree, converts every `RetroTex\*.tif` to BC3/DXT5 `.dds`, and rewrites MDX texture paths from `RetroTex\*.tif` to `RetroTex\*.dds`.

## Notes

- Missing texture files should not crash Warcraft III by themselves; hard crashes usually come from invalid MDX structure or unsupported material/layer combinations.
- Do not HD-convert Warcraft team color/team glow paths into ordinary images. Keep replaceable textures as replaceable resources.
- Use TIF by default unless you have a verified BC3 DDS pipeline for Warcraft III Reforged.
