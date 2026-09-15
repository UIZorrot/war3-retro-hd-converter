"""UI messages retain their arguments so running jobs can switch languages live."""

TEXT = {
    "title": ("War3 · SD → HD Model Converter", "War3 · SD → HD 模型转换"),
    "subtitle": ("Warcraft III model converter · Keep geometry and animations, generate HD materials and textures", "魔兽争霸 III 模型转换 · 保留造型与动画，生成 HD 材质与贴图"),
    "models": ("01  Models", "01  添加模型"),
    "pick_models": ("Select MDX…", "选择 MDX…"),
    "model_folder": ("Add model folder…", "添加模型文件夹…"),
    "remove": ("Remove selected", "移除选中"),
    "textures": ("02  Textures", "02  添加贴图"),
    "pick_textures": ("Select textures…", "选择贴图…"),
    "texture_folder": ("Add texture folder…", "添加贴图文件夹…"),
    "matching_hint": ("Unique filenames match automatically, even with a different image extension. Folders are searched recursively; ambiguous duplicates are reported.", "文件名唯一即可自动匹配，也支持不同图片扩展名。文件夹递归搜索；无法区分的同名贴图会提示冲突。"),
    "output": ("03  Output folder", "03  输出位置"),
    "browse": ("Browse…", "浏览…"),
    "check": ("Check textures", "检查贴图"),
    "convert": ("Convert to HD", "一键转换"),
    "stop": ("Stop", "停止"),
    "open": ("Open output folder", "打开输出文件夹"),
    "ready": ("Ready · TIF textures, one package per model, a new folder for each run", "就绪 · 输出 TIF 贴图，每个模型独立打包，每次转换创建新文件夹"),
    "footer": ("Packages include generated and original custom textures. Team color and team glow are supplied by Warcraft III.", "输出包含生成贴图及原始自定义贴图。队伍颜色、队伍光晕等资源由游戏提供。"),
    "folder_item": ("[Folder] {path}", "[文件夹] {path}"),
    "texture_item": ("[Texture] {path}", "[贴图] {path}"),
    "models_dialog": ("Select SD models (multiple files and portraits supported)", "选择 SD 模型（可多选，含 portrait）"),
    "model_type": ("MDX models", "MDX 模型"),
    "model_folder_dialog": ("Select model folder (including subfolders)", "选择模型文件夹（包含子文件夹）"),
    "textures_dialog": ("Select textures (multiple files supported)", "选择贴图（可多选）"),
    "texture_type": ("Textures", "贴图"),
    "all_files": ("All files", "所有文件"),
    "texture_folder_dialog": ("Select texture resource folder", "选择贴图资源根目录"),
    "output_dialog": ("Select output folder", "选择输出位置"),
    "working": ("Working…", "正在处理…"),
    "need_models": ("Add at least one MDX model first.", "请先添加至少一个 MDX 模型。"),
    "need_output": ("Select an output folder.", "请选择输出位置。"),
    "models_added": ("Models added · {count} total", "已添加模型，共 {count} 个"),
    "inspection_model": ("{name}: {textures} custom textures, {resources} game resources", "{name}：{textures} 张自定义贴图，{resources} 项游戏资源"),
    "mapping": ("  {logical} → {source}", "  {logical} → {source}"),
    "indented": ("  {detail}", "  {detail}"),
    "checked": ("Check complete · {models} models, {errors} issues", "检查完成 · {models} 个模型，{errors} 个问题"),
    "checked_ready": ("Check complete · {models} models, no issues. Ready to convert.", "检查完成 · {models} 个模型，无问题，可以转换"),
    "complete": ("Conversion complete", "转换完成"),
    "stopped": ("Stopped", "已停止"),
    "summary": ("{state} · {ok} succeeded, {failed} failed, {pending} unprocessed", "{state} · 成功 {ok}，失败 {failed}，未处理 {pending}"),
    "output_log": ("Output: {path}", "输出：{path}"),
    "error_status": ("Not completed · See the details below", "未完成 · 请查看下方问题说明"),
    "stopping": ("Stopping… Waiting for the current texture to finish.", "正在停止，请等待当前贴图处理结束…"),
    "closing": ("Stopping the task. Close the window after it stops.", "正在停止任务，停止后可关闭窗口。"),
    "startup_title": ("Unable to start", "无法启动"),
    "startup_error": ("{error}\n\nSource mode requires numpy, Pillow, python-dateutil and PyMdlxConverter.", "{error}\n\n源码运行需要 numpy、Pillow、python-dateutil 和 PyMdlxConverter。"),
    "invalid_mdx": ("Invalid MDX file (MDLX header required)", "不是有效的 MDX 文件（需要 MDLX 文件头）"),
    "incomplete_chunk": ("Incomplete MDX chunk", "MDX 数据块不完整"),
    "oversized_chunk": ("MDX chunk extends beyond the file", "MDX 数据块超出文件长度"),
    "missing_chunks": ("MDX is missing version or model data", "MDX 缺少版本或模型数据块"),
    "parse_error": ("MDX parsing failed: {detail}", "MDX 解析失败：{detail}"),
    "unsupported_version": ("Unsupported model version: {version}", "不支持的模型版本：{version}"),
    "relative_path": ("Texture path must be relative to the package: {path}", "贴图路径必须是包内的相对路径：{path}"),
    "reserved_path": ("Texture path uses a reserved system name: {path}", "贴图路径使用了系统保留名称：{path}"),
    "missing_folder": ("Texture folder does not exist: {path}", "贴图目录不存在：{path}"),
    "missing_file": ("Texture file does not exist: {path}", "贴图不存在：{path}"),
    "ambiguous": ("Ambiguous texture {logical}; multiple matches: {paths}", "贴图重名，无法确定 {logical}：{paths}"),
    "invalid_model": ("Model does not exist or is not MDX: {path}", "模型不存在或不是 MDX：{path}"),
    "indexing": ("Indexing textures…", "正在索引贴图…"),
    "checking_model": ("Checking: {name}", "检查：{name}"),
    "already_hd": ("This model already contains HD materials. Select the original SD model.", "模型已经包含 HD 材质，请选择原始 SD 模型"),
    "empty_texture": ("Model has an empty texture path without a Replaceable ID", "模型含空贴图路径且没有 Replaceable ID"),
    "missing_texture": ("Missing texture: {path}", "缺失贴图：{path}"),
    "generated_collision": ("Generated texture name conflict: {path} (same path, different extensions)", "生成贴图名称冲突：{path}（同路径不同扩展名）"),
    "model_error": ("{name}: {detail}", "{name}：{detail}"),
    "resolve_errors": ("Resolve these issues first:\n{details}", "请先解决以下问题：\n{details}"),
    "converting_model": ("[{index}/{total}] Converting: {name}", "[{index}/{total}] 转换：{name}"),
    "decode_error": ("Cannot decode texture: {path}", "无法解码贴图：{path}"),
    "output_version": ("Output model version validation failed", "输出模型版本校验失败"),
    "missing_output": ("Output texture is missing: {path}", "输出缺少贴图：{path}"),
    "model_complete": ("Done: {name}, {count} textures", "完成：{name}，{count} 张贴图"),
    "model_failed": ("Failed: {name} — {detail}", "失败：{name} — {detail}"),
}


def render(value, language="en"):
    if isinstance(value, Message):
        template = TEXT[value.key][0 if language == "en" else 1]
        return template.format(**{k: render(v, language) for k, v in value.values.items()})
    if isinstance(value, (list, tuple)):
        return "\n".join(render(v, language) for v in value)
    return str(value)


class Message(str):
    """Keep the original Chinese service API, with lossless UI translations."""
    def __new__(cls, key, **values):
        text = TEXT[key][1].format(**{k: render(v, "zh") for k, v in values.items()})
        instance = super().__new__(cls, text)
        instance.key, instance.values = key, values
        return instance


def error_message(error):
    if error.args and isinstance(error.args[0], Message):
        return error.args[0]
    return str(error)
