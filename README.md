# OpenAI Chat Tool CLI
[![MIT](https://img.shields.io/badge/License-MIT-orange.svg)](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/blob/main/LICENSE)
[![Static Badge](https://img.shields.io/badge/Languages-Python-blue.svg)](https://github.com/search?q=repo%3AMiaowCham%2FCMD_Open-AI_Chat_Tool++language%3APython&type=code)
[![Github Release](https://img.shields.io/github/v/release/MiaowCham/CMD_Open-AI_Chat_Tool)](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/releases)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/MiaowCham/CMD_Open-AI_Chat_Tool/.github/workflows/build.yml)](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/actions/workflows/build.yml)  

一个功能丰富的命令行 OpenAI 聊天工具，支持多种模型、多语言界面和智能功能  
你可以直接克隆仓库并运行 `main.py` 来使用  
或者前往 [Release](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/releases/latest) 页面下载构建好的可执行文件

> 哦当然你也可以去 [Actions](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/actions/workflows/build.yml) 页面下载实时构建的最新版本
不用担心无法运行，我在同步到 Github 前会测试的

## 特征
使用 OpenAI 库编写的功能丰富的命令行 AI 聊天工具  
支持多种 API 和模型，具备完整的对话管理和智能功能

### 核心功能
- [x] **多配置管理** - 支持多个 AI 配置，可快速切换不同的模型和设置
- [x] **多语言界面** - 支持中文/英文界面切换 (`/lang` 命令)
- [x] **智能历史记录** - 自动保存对话历史，支持智能总结压缩
- [x] **模板变量系统** - 支持时间相关模板变量 (`{{time}}`, `{{date}}`, `{{datetime}}` 等)
- [x] **多行输入** - 支持 Alt+Enter 换行，提升输入体验
- [x] **丰富的文字提示** - 支持彩色输出和用户友好的界面
- [x] **API Key 校验** - 自动验证 API 密钥可用性
- [x] **指令系统** - 丰富的命令支持 (`/help`, `/config`, `/history`, `/lang` 等)
- [x] **多平台支持** - 支持 Windows、Linux、macOS

### 配置管理
- [x] 使用 `.octool_cli\config.yaml` 记录配置信息
- [x] 支持配置的增删改查和别名设置
- [x] 多语言配置名称和欢迎消息
- [x] 自动时间信息注入

### 智能功能
- [x] 对话历史自动管理和压缩
- [x] 智能总结功能，节省 token 消耗
- [x] 实时模板变量替换
- [x] 自动配置向后兼容

### 依赖包列表:
 - **openai** - OpenAI API 客户端
 - **pyyaml** - YAML 配置文件处理
 - **packaging** - 版本管理
 - **prompt-toolkit** - 多行输入和终端交互
 - **pyinstaller**（可选，用于 `build_exe.py` 构建可执行文件）

### 安装方法

#### 方法一：使用 requirements.txt（推荐）
```bash
pip install -r requirements.txt
```

#### 方法二：手动安装
```bash
pip install openai pyyaml packaging prompt-toolkit
# 如需构建可执行文件
pip install pyinstaller
```

## 使用方法

### 快速开始
1. 克隆仓库：`git clone https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool.git`
2. 安装依赖：`pip install -r requirements.txt`
3. 运行程序：`python main.py`
4. 首次运行会引导你配置 API 密钥和基本设置

### 命令行参数
```bash
# 交互模式（默认）
python main.py

# 极简模式
python main.py --simple --prompt "你的问题" --key "your_api_key"

# 指定配置
python main.py --config config_name
```

### 主要命令
- `/help` - 显示帮助信息
- `/config list` - 列出所有配置
- `/config switch <id>` - 切换配置
- `/config new` - 创建新配置
- `/history` - 查看历史记录统计
- `/lang switch <language>` - 切换界面语言
- `/clear` - 清屏
- `/exit` - 退出程序

## 许可证
本项目使用 MIT 许可证
