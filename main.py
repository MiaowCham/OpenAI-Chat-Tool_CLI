import os
import time
import sys
import yaml
from openai import OpenAI

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
HELP_MSG = f"""{COLOR_YELLOW}指令列表:{COLOR_BLUE}
- '/clear': 清屏
- '/exit': 退出 COCTool 并清空配置文件
- '/key': 查看当前 API Key
- '/model': 查看当前模型名称
- '/sys': 查看当前系统提示词
- '/set': 更改设置，直接输入查看指令帮助
{COLOR_RESET}
{WELCOME_MSG}"""

SET_MSG = f"""{COLOR_YELLOW}/set 指令帮助{COLOR_BLUE}
- '/set model': 更换模型名称（默认 deepseek-chat，输入 deepseek-reasoner 使用推理模型）
- '/set model 0': 切换到 deepseek-chat 模型
- '/set model 1': 切换到 deepseek-reasoner 模型
- '/set key': 更改 API Key
- '/set sys': 更改系统提示词
{COLOR_RESET}
{WELCOME_MSG}"""

def get_config_path():
    # 优先使用运行目录下的 .coctool/config.yaml
    exe_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    config_dir = os.path.join(exe_dir, ".coctool")
    config_path = os.path.join(config_dir, "config.yaml")
    try:
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        # 测试写权限
        with open(config_path, "a", encoding="utf-8"):
            pass
        return config_path
    except Exception:
        # 回退到用户主目录
        user_config_dir = os.path.join(os.path.expanduser("~"), ".COCTool")
        if not os.path.exists(user_config_dir):
            try:
                os.makedirs(user_config_dir, exist_ok=True)
            except Exception as e:
                print(f"{COLOR_RED}无法创建配置目录: {user_config_dir}，错误: {e}{COLOR_RESET}")
        return os.path.join(user_config_dir, "config.yaml")

CONFIG_PATH = get_config_path()
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
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)
    except Exception as e:
        print(f"{COLOR_RED}保存 config.yaml 失败: {e}{COLOR_RESET}")

def load_config(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"{COLOR_RED}读取 config.yaml 失败: {e}{COLOR_RESET}")
        return None

def validate_api(api_key, api_endpoint):
    try:
        client = OpenAI(api_key=api_key, base_url=api_endpoint)
        client.models.list()
        return True
    except Exception as e:
        print("\033[F\033[K", end="")  # 清除上一行
        print(f"{COLOR_RED}API Key 验证失败: {e}{COLOR_RESET}")
        return False

def input_config():
    while True:
        print("\033[H\033[J", end="")  # 清屏
        print(f"{COLOR_YELLOW}欢迎使用 CMD OpenAI Chat Tool！请输入您的 API Key 和相关配置。{COLOR_RESET}")
        api_key = input(f"{COLOR_YELLOW}请输入您的 API Key: {COLOR_RESET}").strip()
        if not api_key:
            print("\033[F\033[K", end="")  # 清除上一行
            continue
        api_endpoint = input(f"{COLOR_YELLOW}请输入 API Endpoint（默认 https://api.deepseek.com）：{COLOR_RESET}").strip() or "https://api.deepseek.com"
        print(f"{COLOR_GREEN}正在验证 API Key，请稍候...{COLOR_RESET}")
        if validate_api(api_key, api_endpoint):
            print("\033[F\033[K", end="")  # 清除“正在验证 API Key，请稍候...”行
            break
        print(f"{COLOR_RED}API Key 无效或不可用，请重新输入。{COLOR_RESET}")
        time.sleep(1)
        print("\033[F\033[K", end="")  # 清除上一行
    system_prompt = input(f"{COLOR_YELLOW}请输入系统提示词（System Prompt）：{COLOR_RESET}").strip()
    model_name = input(f"{COLOR_YELLOW}请输入模型名称（默认 deepseek-chat，输入 deepseek-reasoner 使用推理模型）：{COLOR_RESET}").strip() or "deepseek-chat"
    return api_key, api_endpoint, system_prompt, model_name

def main_init():
    # 启动后立即清屏
    print("\033[H\033[J", end="")
    global api_key, api_endpoint, system_prompt, model_name, config
    config_loaded = False
    if os.path.exists(CONFIG_PATH):
        config = load_config(CONFIG_PATH)
        if config:
            api_key = config.get("API_key")
            api_endpoint = config.get("API_endpoint")
            system_prompt = config.get("system_Prompt")
            model_name = config.get("model-name", "deepseek-chat")
            if api_key and api_endpoint and validate_api(api_key, api_endpoint):
                print(f"{COLOR_GREEN}配置加载成功，API 有效。{COLOR_RESET}")
                config_loaded = True
            else:
                print(f"{COLOR_YELLOW}配置文件中的 API Key 无效或缺失，需重新输入。{COLOR_RESET}")
    if not config_loaded:
        api_key, api_endpoint, system_prompt, model_name = input_config()
        save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
        print(f"{COLOR_GREEN}配置已保存到 config.yaml{COLOR_RESET}")

main_init()
client = OpenAI(api_key=api_key, base_url=api_endpoint)

print(f"{COLOR_GREEN}已完成初始设置！{COLOR_RESET}")
time.sleep(1)
print("\033[H\033[J", end="")  # 清屏

def handle_command(user_input):
    global api_key, api_endpoint, system_prompt, model_name
    # 检查用户输入是否为 'help'
    if user_input.lower() == '/help':
        print(HELP_MSG)
        return True
    # 检查用户输入是否为 'set'
    if user_input.lower() == '/set':
        print(SET_MSG)
        return True
    # 检查用户输入是否为 'exit'
    if user_input.lower() == '/exit':
        # 清空 config 文件
        try:
            if os.path.exists(CONFIG_PATH):
                os.remove(CONFIG_PATH)
                print(f"{COLOR_YELLOW}已清空配置文件（{CONFIG_PATH}）{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}清空配置文件失败: {e}{COLOR_RESET}")
        print(f"{COLOR_RED}正在退出 COCTool{COLOR_RESET}")
        sys.exit(0)
    # 检查用户输入是否为 'clear'
    if user_input.lower() == '/clear':
        print("\033[H\033[J", end="")  # 清屏
        print(WELCOME_MSG)
        return True
    # 检查用户输入是否为 'key'
    if user_input.lower() == '/key':
        print(f"""{COLOR_YELLOW}当前 DeepSeek API Key: {COLOR_RESET} {api_key}""")
        return True
    if user_input.lower() == '/set key':
        new_api_key = input(f"{COLOR_YELLOW}请输入新的 API Key(直接回车取消更改): {COLOR_RESET}").strip()
        if new_api_key:
            print(f"{COLOR_GREEN}正在验证新的 API Key，请稍候...{COLOR_RESET}")
            if validate_api(new_api_key, api_endpoint):
                api_key = new_api_key
                save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
                print(f"{COLOR_GREEN}API Key 已更新，并已保存到配置文件。{COLOR_RESET}")
            else:
                print(f"{COLOR_RED}API Key 验证失败，未进行更改。{COLOR_RESET}")
        else:
            print(f"{COLOR_YELLOW}API Key 未更改。{COLOR_RESET}")
        return True
    # 检查用户输入是否为 'sys'
    if user_input.lower() == '/sys':
        print(f"""{COLOR_YELLOW}当前系统提示词: {COLOR_RESET} {system_prompt}""")
        return True
    if user_input.lower() == '/set sys':   
        new_system_prompt = input(f"{COLOR_YELLOW}请输入新的系统提示词（直接回车取消更改）: {COLOR_RESET}").strip()
        if new_system_prompt:
            system_prompt = new_system_prompt
            save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
            print(f"{COLOR_GREEN}系统提示词已更新，并已保存到配置文件。{COLOR_RESET}")
        else:
            print(f"{COLOR_YELLOW}系统提示词未更改。{COLOR_RESET}")
        return True
    # 检查用户输入是否为 'model'
    if user_input.lower() == '/model':
        print(f"""{COLOR_YELLOW}当前模型名称: {COLOR_RESET} {model_name}""")
        return True
    # 新增：更换模型指令
    if user_input.lower() == '/set model':
        new_model = input(f"{COLOR_YELLOW}请输入模型名称（默认 deepseek-chat，输入 deepseek-reasoner 使用推理模型）：{COLOR_RESET}").strip() or "deepseek-chat"
        model_name = new_model
        # 更新config并保存
        save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
        print("\033[F\033[K", end="")  # 清除上一行
        print(f"{COLOR_GREEN}模型已更换为: {model_name}，并已保存到配置文件。{COLOR_RESET}")
        return True
    if user_input.lower() == '/set model 0':
        new_model = "deepseek-chat"
        model_name = new_model
        # 更新config并保存
        save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
        print(f"{COLOR_GREEN}模型已更换为: {model_name}，并已保存到配置文件。{COLOR_RESET}")
        return True
    if user_input.lower() == '/set model 1':
        new_model = "deepseek-reasoner"
        model_name = new_model
        # 更新config并保存
        save_config(CONFIG_PATH, api_key, api_endpoint, system_prompt, model_name)
        print(f"{COLOR_GREEN}模型已更换为: {model_name}，并已保存到配置文件。{COLOR_RESET}")
        return True
    # 检查用户输入是否为空
    if not user_input.strip():
        print(f"""{COLOR_RED}输入不能为空，请重新输入。{COLOR_RESET}""")
        time.sleep(1)
        print("\033[H\033[J", end="") # 清屏
        print(WELCOME_MSG)
        return True
    return False

def main():
    print(WELCOME_MSG)
    while True:
        user_input = input(f"\n{COLOR_YELLOW}给 DeepSeek 发生消息（输入 '/help' 查看帮助）：{COLOR_RESET}\n")
        if handle_command(user_input):
            continue
        # 处理用户输入
        print(f"\n{COLOR_BLUE}正在处理您的请求，请稍候...{COLOR_RESET}")
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            stream=False
        )
        print("\033[F\033[K", end="")  # 清除上一行“正在处理您的请求，请稍候...”
        print(f"{COLOR_CYAN}Deepseek:{COLOR_RESET}")
        print(response.choices[0].message.content)

if __name__ == "__main__":
    main()