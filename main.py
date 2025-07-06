from openai import OpenAI
import time
import os
import yaml  # 替换 json 为 yaml

# 颜色定义
COLOR_YELLOW = "\033[33m"
COLOR_GREEN = "\033[32m"
COLOR_BLUE = "\033[34m"
COLOR_RED = "\033[31m"
COLOR_CYAN = "\033[36m"
COLOR_RESET = "\033[0m"

# 欢迎语定义
WELCOME_MSG = f"""{COLOR_GREEN}我是 DeepSeek，很高兴见到你！
我可以帮你写代码、读文件、写作各种创意内容，请把你的任务交给我吧~{COLOR_RESET}"""

# help 内容定义
HELP_MSG = f"""{COLOR_YELLOW}指令列表:
{COLOR_BLUE}
- 'exit': 退出 DeepSeek AI 助手
- 'clear': 清屏
- 'key': 查看当前 API Key
- 'systemprompt': 查看当前系统提示词
- 'model': 查看当前模型名称
{COLOR_RESET}
{WELCOME_MSG}"""

# 初始设置
print("\033[H\033[J", end="")  # 清屏

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
config = {}
api_key = None
api_endpoint = None
system_prompt = None
model_name = None

def save_config(path, api_key, api_endpoint, system_prompt, model_name):
    data = {
        "API_key": api_key,
        "API_endpoint": api_endpoint,
        "system_Prompt": system_prompt,
        "model-name": model_name
    }
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)

# 检查 config.yaml 是否存在，不存在则创建
if not os.path.exists(CONFIG_PATH):
    print(f"{COLOR_YELLOW}未检测到 config.yaml，将进行首次配置...{COLOR_RESET}")
    # 手动输入
    api_key = input(f"{COLOR_YELLOW}请输入您的 API Key: {COLOR_RESET}").strip()
    while not api_key:
        print(f"{COLOR_RED}API Key 不能为空{COLOR_RESET}")
        api_key = input(f"{COLOR_YELLOW}请输入您的 API Key: {COLOR_RESET}").strip()
    api_endpoint = input(f"{COLOR_YELLOW}请输入 API Endpoint（默认 https://api.deepseek.com）：{COLOR_RESET}").strip() or "https://api.deepseek.com"
    system_prompt = input(f"{COLOR_YELLOW}请输入系统提示词（System Prompt）：{COLOR_RESET}").strip()
    model_name = input(f"{COLOR_YELLOW}请输入模型名称（默认 deepseek-chat）：{COLOR_RESET}").strip() or "deepseek-chat"
    save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
    print(f"{COLOR_GREEN}配置已保存到 config.yaml{COLOR_RESET}")

# 读取 config.yaml
if os.path.exists(CONFIG_PATH):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        api_key = config.get("API_key")
        api_endpoint = config.get("API_endpoint")
        system_prompt = config.get("system_Prompt")
        model_name = config.get("model-name", "deepseek-chat")
    except Exception as e:
        print(f"{COLOR_RED}读取 config.yaml 失败: {e}{COLOR_RESET}")

# 尝试用 config.yaml 连接 API
client = None
if api_key and api_endpoint and system_prompt:
    print(f"{COLOR_GREEN}正在尝试使用 config.yaml 连接 API...{COLOR_RESET}")
    try:
        client = OpenAI(api_key=api_key, base_url=api_endpoint)
        client.models.list()
        print(f"{COLOR_GREEN}config.yaml 连接成功！{COLOR_RESET}")
    except Exception as e:
        print(f"{COLOR_RED}config.yaml 连接失败: {e}{COLOR_RESET}")
        client = None

# 若 config.yaml 连接失败或缺失字段，进入手动输入流程，并保存到 config.yaml
if not client:
    print("\033[H\033[J", end="")  # 清屏
    # 提示用户输入 API Key,并验证其有效性
    while True:
        api_key = input(f"{COLOR_YELLOW}请输入您的 API Key: {COLOR_RESET}").strip()
        if not api_key:
            print(f"{COLOR_RED}API Key 不能为空{COLOR_RESET}")
            time.sleep(1)
            print("\033[H\033[J", end="")  # 清屏
            continue
        api_endpoint = input(f"{COLOR_YELLOW}请输入 API Endpoint（默认 https://api.deepseek.com）：{COLOR_RESET}").strip() or "https://api.deepseek.com"
        print(f"{COLOR_GREEN}正在验证 API Key，请稍候...{COLOR_RESET}")
        try:
            test_client = OpenAI(api_key=api_key, base_url=api_endpoint)
            test_client.models.list()
        except Exception as e:
            print("\033[H\033[J", end="")  # 清屏
            print(f"{COLOR_RED}API Key 无效或不可用，请重新输入。{COLOR_RESET}")
            continue
        print("\033[F\033[K", end="")  # 清除上一行“正在验证 API Key，请稍候...”
        break
    system_prompt = input(f"{COLOR_YELLOW}请输入系统提示词（System Prompt）：{COLOR_RESET}").strip()
    model_name = input(f"{COLOR_YELLOW}请输入模型名称（默认 deepseek-chat）：{COLOR_RESET}").strip() or "deepseek-chat"
    save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
    print(f"{COLOR_GREEN}配置已保存到 config.yaml{COLOR_RESET}")
    client = OpenAI(api_key=api_key, base_url=api_endpoint)

print(f"{COLOR_GREEN}已完成初始设置！{COLOR_RESET}")
time.sleep(1)
print("\033[H\033[J", end="")  # 清屏

print(WELCOME_MSG)

while True:
    user_input = input(f"\n{COLOR_YELLOW}给 DeepSeek 发生消息（输入 'help' 查看帮助）：{COLOR_RESET}\n")
    # 检查用户输入是否为 'help'
    if user_input.lower() == 'help':
        print("\033[H\033[J", end="")  # 清屏
        print(HELP_MSG)
        continue
    # 检查用户输入是否为 'exit'
    if user_input.lower() == 'exit':
        print(f"{COLOR_RED}退出 DeepSeek AI 助手。{COLOR_RESET}")
        break
    # 检查用户输入是否为 'clear'
    if user_input.lower() == 'clear':
        print("\033[H\033[J", end="")  # 清屏
        print(WELCOME_MSG)
        continue
    # 检查用户输入是否为 'key'
    if user_input.lower() == 'key':
        print("\033[H\033[J", end="")  # 清屏
        print(f"""{COLOR_YELLOW}当前 DeepSeek API Key: {COLOR_RESET} {api_key}\n""")
        print(WELCOME_MSG)
        continue
    # 检查用户输入是否为 'systemprompt'
    if user_input.lower() == 'systemprompt':
        print("\033[H\033[J", end="")  # 清屏
        print(f"""{COLOR_YELLOW}当前系统提示词: {COLOR_RESET} {system_prompt}\n""")
        print(WELCOME_MSG)
        continue
    # 检查用户输入是否为 'model'
    if user_input.lower() == 'model':
        print("\033[H\033[J", end="")  # 清屏
        print(f"""{COLOR_YELLOW}当前模型名称: {COLOR_RESET} {model_name}\n""")
        print(WELCOME_MSG)
        continue
    # 检查用户输入是否为空
    if not user_input.strip():
        print("\033[H\033[J", end="")
        print(f"""{COLOR_RED}输入不能为空，请重新输入。{COLOR_RESET}
{WELCOME_MSG}""")
        time.sleep(1)
        print("\033[H\033[J", end="")
        print(WELCOME_MSG)
        continue
    # 处理用户输入
    else:
        print(f"{COLOR_BLUE}正在处理您的请求，请稍候...{COLOR_RESET}")
        # 调用 DeepSeek API
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            stream=False
        )
        print("\033[F\033[K", end="")  # 清除上一行“正在处理您的请求，请稍候...”
        print(f"\n{COLOR_CYAN}Deepseek:{COLOR_RESET}")
        print(response.choices[0].message.content)