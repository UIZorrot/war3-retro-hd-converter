# War3 Retro HD Converter

[English](README.md)

War3 Retro HD Converter 用于将《魔兽争霸 III：重制版》的 SD MDX 模型转换为使用 HD 材质的 MDX 模型。它保留原有网格、UV、动画和由游戏管理的资源，同时生成 HD 材质管线需要的贴图引用。

> 本工具是材质转换工具，不是自动重建模型或放大贴图的工具。它不会增加面数、重建几何细节或提升 diffuse 分辨率。

## 下载

请从 [GitHub Releases](https://github.com/UIZorrot/war3-retro-hd-converter/releases/latest) 下载 Windows x64 便携版。

1. 下载 `War3RetroHD-Windows-x64.zip`。
2. 完整解压压缩包。
3. 运行 `War3RetroHD.exe`，并保留同目录的 `_internal` 文件夹。

便携版无需安装 Python。版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## 桌面程序

程序默认使用 English。可通过 **SD → HD** 标题旁的下拉框切换中文；已选择的文件、输出目录和正在执行的任务都会保留。

1. 选择一个或多个 `.mdx` 模型，或递归添加模型文件夹。
2. 选择贴图文件，或添加一个或多个贴图文件夹。
3. 点击 **Check textures**，检查模型中的每个引用与实际匹配文件。
4. 选择输出文件夹并点击 **Convert to HD**。

每次运行都会新建 `SD-to-HD_<日期>_<时间>_<编号>` 文件夹。每个模型都有独立包，包含 HD `.mdx`、所需的自定义贴图、`RetroTex` 下生成的材质贴图、`manifest.json`，总结果写入 `conversion_report.json`。

转换完成后可点击 **Open output folder** 打开结果目录。

### 贴图自动匹配

程序按以下顺序查找贴图：

1. 已添加资源根目录中的完整逻辑路径，允许替代扩展名。
2. 导入文件的目录后缀。
3. 模型所在目录。
4. 唯一文件名或不含扩展名的唯一名称。

匹配不区分大小写。唯一的 `Footman.png`、`Footman.dds` 或 `Footman.tif` 可以满足模型中的 `Textures\\Footman.blp` 引用。目录路径匹配优先；同一优先级有多个候选时，程序会报告冲突而不会随意选择。

**Check textures** 会显示“模型引用 → 实际匹配文件”。若存在同名贴图，请保留原有目录结构，并添加对应资源根目录。

### 转换会做什么

- 将输出 MDX 转为 `1000` 版本，并使用 `Shader_HD_DefaultUnit` 重建材质。
- 在 `RetroTex` 下生成 `diffuse`、`alpha_diffuse`、`team_diffuse`、`normal`、`orm` 和 `team_orm` 贴图，并保留源逻辑路径。
- 重新计算 pivot point、范围、顶点法线与切线。
- 保留队伍色、队伍光晕、Black32、EnvironmentMap 等游戏管理资源的引用。

自动生成的 Normal 来自 diffuse 明暗变化的估算。默认 ORM 以兼容性为目标：完整环境遮蔽、最高粗糙度和零金属度。如需物理意义准确的材质，请使用手工制作或烘焙的 Normal 与 ORM 替换生成结果。

原始输入文件不会被修改。缺失贴图或匹配冲突会阻止转换；贴图解码、模型解析、输出和校验失败会记录在报告中，程序不会发布不完整的模型包。

当前版本不会自动收集外部子模型、声音和 FaceFX 文件。

## 从源码运行

```powershell
python -m pip install -e .[dev]
python launch_desktop.pyw
```

项目依赖 Python Tk、numpy、Pillow、python-dateutil 和 PyMdlxConverter。源码模式会自动查找 `../scripts/PyMdlxConverter` 与 `../scripts/blplabcl.exe`；便携版已包含所需的本地运行环境和工具。

重新构建便携版：

```powershell
python -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -e .[dev] pyinstaller
.\.venv-build\Scripts\python.exe build_desktop.py
```

分发前请核对 PyMdlxConverter、BLP Lab 及其 DLL 的分发许可。本仓库不包含《魔兽争霸 III》游戏模型与贴图。

### 便携版自检

```powershell
.\dist\War3RetroHD\War3RetroHD.exe --self-test --input "D:\assets\model.mdx" --texture-root "D:\assets" --output "D:\output\diagnostics"
```

该命令会进行实际转换，在输出目录写入 `self-test.json`，成功时退出码为 `0`。

## 命令行

### 环境要求

- Python 3.10+
- `numpy`
- `Pillow`
- 位于 `PYTHONPATH` 中的 PyMdlxConverter，或通过 `--pymdlx-path` 指定
- 可选：`blplabcl.exe`，用于更可靠的 BLP 转换

开发环境安装：

```powershell
cd D:\Quenching\LSON\war3-retro-hd-converter
python -m pip install -e .[dev]
```

### 转换单个模型

```powershell
python -m war3_retro_hd.cli convert-file `
  --input "D:\Quenching\LSON\Pack\war3.w3mod\units\human\footman\footman.mdx" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

### 转换整个模型树

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "D:\Quenching\LSON\Pack\war3.w3mod\units" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

转换后的路径保留相对于 `--source-root` 的位置。要将建筑输出到 `Rbuildings`：

```powershell
python -m war3_retro_hd.cli convert-tree `
  --input-root "D:\Quenching\LSON\Pack\war3.w3mod\buildings" `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod" `
  --output-root "D:\Quenching\War3Reforged\Warcraft III\_retail_" `
  --path-rewrite "buildings=Rbuildings" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

### 检查重复贴图名称

生成贴图采用 `RetroTex/<源逻辑路径>_*.tif`，避免旧版 `RetroTex/<basename>_*.tif` 结构产生同名冲突。

```powershell
python -m war3_retro_hd.cli audit-textures `
  --source-root "D:\Quenching\LSON\Pack\war3.w3mod"
```

### 打包模型目录

```powershell
python -m war3_retro_hd.cli package-models `
  --input-root "D:\Quenching\QM\3.3\Retro" `
  --source-root "D:\Quenching\QM\3.3\Retro" `
  --output-root "D:\Quenching\QM\3.3\Retro_Packaged" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

每个包包含对应源目录的 MDX 文件及其引用的 `RetroTex` 文件。由 Warcraft 管理的资源会继续保留为外部游戏引用。

### 创建共享 RetroTex DDS/BC3 发布包

```powershell
python -m war3_retro_hd.cli make-dds-release `
  --source-root "D:\Quenching\QM\3.3\Retro" `
  --output-root "D:\Quenching\QM\3.3\Retro_DDS_BC3" `
  --pymdlx-path "D:\Quenching\LSON\scripts\PyMdlxConverter"
```

该命令复制模型树，将 `RetroTex\\*.tif` 转成 BC3/DXT5 `.dds`，并改写对应 MDX 贴图路径。除非 DDS 流程已在《魔兽争霸 III：重制版》中验证，否则建议默认使用 TIF。

## 说明

- 缺失贴图本身通常不会直接导致游戏崩溃；崩溃更常由无效 MDX 结构或不受支持的材质/图层组合引起。
- 不要把 Warcraft 的可替换队伍色或队伍光晕路径转换为普通图片。
- 分发前请在目标游戏环境中验证最终模型包。
