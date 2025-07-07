# CMD OpenAI Chat Tool
[![MIT](https://img.shields.io/badge/License-MIT-orange.svg)](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/blob/main/LICENSE)
[![Static Badge](https://img.shields.io/badge/Languages-Python-blue.svg)](https://github.com/search?q=repo%3AMiaowCham%2CMD_Open-AI_Chat_Tool++language%3APython&type=code)
[![Github Release](https://img.shields.io/github/v/release/MiaowCham/CMD_Open-AI_Chat_Tool)](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/releases)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/MiaowCham/CMD_Open-AI_Chat_Tool/.github/workflows/build.yml)](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/actions/workflows/build.yml)  
一个简单的命令行 OpenAI 聊天工具，支持多种模型  
你可以直接克隆仓库并运行 `main.py` 来使用  
或者前往 [Release](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/releases/latest) 页面下载构建好的可执行文件

> 哦当然你也可以去 [Actions](https://github.com/MiaowCham/CMD_Open-AI_Chat_Tool/actions/workflows/build.yml) 页面下载实时构建的最新版本
不用担心无法运行，我在同步到 Github 前会测试的

## 特征
使用 OpenAI 库编写的一个简单的命令行 AI 聊天工具  
支持多种 API 和 模型 (~~毕竟用的 OpenAI 写好的库~~)

- [x] 丰富的文字提示，支持彩色输出（顶部提示写成 DeepSeek 了，但开源项目嘛，你完全可以改成自己喜欢的输出）
- [x] API Key 可用性校验
- [x] 使用 `.coctool\config.yaml` 记录配置信息
- [x] 指令支持（对话时输入 `/help` 查看相关帮助）
- [x] 多平台支持（仅打包Win端，其他平台可以使用 Wine 或直接运行源码）

### 依赖包列表:
 - pyinstaller（可选，用于 `build_exe.py` 构建可执行文件）
 - pyyaml
 - openai
 - packaging

### 安装方法（命令行执行）:
```bash
pip install pyinstaller pyyaml openai packaging
```

## 许可证
本项目使用 MIT 许可证