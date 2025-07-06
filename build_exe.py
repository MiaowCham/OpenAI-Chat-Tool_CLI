# 依赖包列表:
# - pyinstaller
# - pyyaml
# - openai
# - packaging

# 安装方法（命令行执行）:
# pip install pyinstaller pyyaml openai packaging
import os
import sys
import subprocess
import shutil
import pkg_resources

def check_and_install(package):
    try:
        pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        print(f"未检测到 {package}，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def clean_build_dirs():
    for d in ["build", "dist"]:
        if os.path.exists(d):
            print(f"正在删除目录: {d}")
            shutil.rmtree(d)
    spec_file = "main.spec"
    if os.path.exists(spec_file):
        print(f"正在删除文件: {spec_file}")
        os.remove(spec_file)

def build_exe():
    print("正在使用 PyInstaller 构建可执行文件...")
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--clean",
        "--name", "OpenAI-Chat",
        "main.py"
    ]
    subprocess.check_call(cmd)

if __name__ == "__main__":
    # 检查依赖
    check_and_install("packaging")
    check_and_install("pyinstaller")
    check_and_install("pyyaml")
    check_and_install("openai")
    # 清理旧目录
    clean_build_dirs()
    # 构建
    build_exe()
    print("构建完成！可执行文件在 dist 目录下。")