"""Build a local portable Windows application using the repository's parser/tools."""
import importlib.util
import subprocess
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
scripts = root.parent / "scripts"
if not importlib.util.find_spec("PyInstaller"):
    raise SystemExit("Install the build dependency first: python -m pip install pyinstaller")
args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
        "--name", "War3RetroHD", "--distpath", str(root / "dist"),
        "--workpath", str(root / "build"), "--specpath", str(root / "build"),
        "--paths", str(root / "src"), "--paths", str(scripts / "PyMdlxConverter"),
        "--collect-submodules", "PyMdlxConverter"]
for name in ("blplabcl.exe", "swdn_blp.dll"):
    path = scripts / name
    if path.is_file():
        args.extend(["--add-binary", f"{path};tools"])
args.append(str(root / "launch_desktop.pyw"))
subprocess.run(args, check=True, cwd=root)
shutil.copy2(root / "README.md", root / "dist" / "War3RetroHD" / "使用说明.md")
shutil.make_archive(str(root / "dist" / "War3RetroHD-Windows-x64"), "zip", root / "dist", "War3RetroHD")
print(root / "dist" / "War3RetroHD" / "War3RetroHD.exe")
