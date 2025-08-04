# 依赖包列表:
# - pyinstaller
# - pyyaml
# - openai
# - packaging
# - prompt-toolkit

# 安装方法（命令行执行）:
# pip install pyinstaller pyyaml openai packaging prompt-toolkit
import os
import sys
import subprocess
import shutil
import pkg_resources
import re

def get_version_from_main():
    """从main.py中提取版本信息"""
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 使用简单的方法解析版本
        for line in content.split('\n'):
            if 'VERSION' in line and '=' in line:
                # 提取引号中的内容
                if '"' in line:
                    parts = line.split('"')
                    if len(parts) >= 2:
                        return parts[1]
                elif "'" in line:
                    parts = line.split("'")
                    if len(parts) >= 2:
                        return parts[1]
        
        print("警告: 未在main.py中找到VERSION变量，使用默认版本1.0.0")
        return "1.0.0"
    except Exception as e:
        print(f"读取版本信息失败: {e}，使用默认版本1.0.0")
        return "1.0.0"

def create_version_file(version):
    """创建Windows版本信息文件"""
    version_info = f"""# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
# filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
# Set not needed items to zero 0.
filevers=({version.replace('.', ', ')}, 0),
prodvers=({version.replace('.', ', ')}, 0),
# Contains a bitmask that specifies the valid bits 'flags'r
mask=0x3f,
# Contains a bitmask that specifies the Boolean attributes of the file.
flags=0x0,
# The operating system for which this file was designed.
# 0x4 - NT and there is no need to change it.
OS=0x4,
# The general type of file.
# 0x1 - the file is an application.
fileType=0x1,
# The function of the file.
# 0x0 - the function is not defined for this fileType
subtype=0x0,
# Creation date and time stamp.
date=(0, 0)
),
  kids=[
StringFileInfo(
  [
  StringTable(
    u'040904B0',
    [StringStruct(u'CompanyName', u'OpenAI Chat Tool CLI'),
    StringStruct(u'FileDescription', u'OpenAI Chat Tool CLI - 命令行AI聊天工具'),
    StringStruct(u'FileVersion', u'{version}'),
    StringStruct(u'InternalName', u'octool_cli'),
    StringStruct(u'LegalCopyright', u'MIT License'),
    StringStruct(u'OriginalFilename', u'octool_cli.exe'),
    StringStruct(u'ProductName', u'OpenAI Chat Tool CLI'),
    StringStruct(u'ProductVersion', u'{version}')])
  ]), 
VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)"""
    
    with open('version_info.txt', 'w', encoding='utf-8') as f:
        f.write(version_info)
    
    print(f"已创建版本信息文件，版本: {version}")
    return 'version_info.txt'

def check_and_install(package):
    try:
        pkg_resources.get_distribution(package)
    except pkg_resources.DistributionNotFound:
        print(f"未检测到 {package}，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
    except Exception as e:
        print(f"检测/安装 {package} 失败: {e}")

def clean_build_dirs():
    for d in ["build", "dist"]:
        if os.path.exists(d):
            print(f"正在删除目录: {d}")
            shutil.rmtree(d)
    
    # 清理构建相关文件
    files_to_clean = ["main.spec", "version_info.txt"]
    for file in files_to_clean:
        if os.path.exists(file):
            print(f"正在删除文件: {file}")
            os.remove(file)

def build_exe():
    print("正在使用 PyInstaller 构建可执行文件...")
    
    # 获取版本信息并创建版本文件
    version = get_version_from_main()
    version_file = create_version_file(version)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onedir",
        "--clean",
        "--name", "octool_cli",
        "--version-file", version_file,
        "--hidden-import", "yaml",
        "--hidden-import", "yaml.loader",
        "--hidden-import", "yaml.dumper",
        "--hidden-import", "prompt_toolkit",
        "--hidden-import", "prompt_toolkit.key_binding",
        "--hidden-import", "prompt_toolkit.shortcuts",
        "--hidden-import", "tiktoken",
        "--hidden-import", "tiktoken.registry",
        "--hidden-import", "tiktoken.model",
        "--hidden-import", "tiktoken_ext",
        "--hidden-import", "tiktoken_ext.openai_public",
        "--collect-data", "tiktoken_ext",
        "--add-data", "i18n;i18n",
        "main.py"
    ]
    subprocess.check_call(cmd)

if __name__ == "__main__":
    # 检查依赖
    check_and_install("packaging")
    check_and_install("pyinstaller")
    check_and_install("pyyaml")
    check_and_install("openai")
    check_and_install("prompt-toolkit")
    check_and_install("tiktoken")
    # 清理旧目录
    clean_build_dirs()
    # 构建
    build_exe()
    print("构建完成！可执行文件在 dist/octool_cli 目录下。")