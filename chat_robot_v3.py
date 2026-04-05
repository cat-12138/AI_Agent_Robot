import time
import hashlib
import base64
import hmac
import json
import websocket
import os
import re
import logging
import ssl
from urllib.parse import urlencode
from typing import Dict, Callable

# ==================== 配置区 ====================
APPID = "f34ada10"
API_KEY = "99073aaa514be0ba85e1c5ea7798de31"
API_SECRET = "YWFhN2E1MmI1OTQyYTM4MzVhZDVhMWY5"

HOST = "spark-api.xf-yun.com"
PATH = "/v3.5/chat"
DOMAIN = "generalv3.5"
# =============================================

# ====================== TXT统计工具 ======================
def txt_statistics(directory: str) -> str:
    if not os.path.isdir(directory):
        return f"❌ 错误：目录不存在 -> {directory}"

    results = []
    txt_count = 0

    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.txt'):
                txt_count += 1
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                    lines = len(text.splitlines())
                    words = len(re.findall(r'\w+', text))
                    chars = len(text)
                    results.append(
                        f"📄 {os.path.relpath(filepath, directory)}\n"
                        f"   行数: {lines} | 词数: {words} | 字符数: {chars}"
                    )
                except Exception as e:
                    results.append(f"⚠️ 读取失败 {file}: {e}")

    if not results:
        return f"✅ 目录 {directory} 中没有找到TXT文件"

    return f"✅ 扫描完成！共找到 {txt_count} 个 TXT 文件\n\n" + "\n\n".join(results)


TOOLS: Dict[str, Callable] = {
    "txt_statistics": txt_statistics,
}


class ChatRobot:
    def __init__(self):
        self.history = []
        self.system_prompt = (
            "你是一个严格的AI工具调用助手。\n"
            "当用户要求统计TXT文件信息时，你**只能**输出一行有效的JSON，不能有任何其他文字。\n"
            "严格格式（必须一行）：\n"
            "{\"tool\": \"txt_statistics\", \"args\": {\"directory\": \"D:\\\\pycharm\\\\PythonProject01\\\\txt_files\"}}\n"
            "注意：\n"
            "1. 必须是合法JSON\n"
            "2. directory 使用双反斜杠 \\\\ \n"
            "3. 工具返回结果后，用自然语言回复。\n"
            "现在开始严格执行！"
        )
        self.max_history = 20
        self.logger = logging.getLogger("ChatRobot")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    def set_system_prompt(self, prompt: str):
        self.system_prompt = prompt
        print(f"✅ 系统角色已更新")

    def clear_history(self):
        self.history = []
        print("✅ 对话历史已清空")

    def _generate_url(self):
        now = time.time()
        date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(now))
        signature_origin = f"host: {HOST}\ndate: {date}\nGET {PATH} HTTP/1.1"
        signature = base64.b64encode(
            hmac.new(API_SECRET.encode('utf-8'), signature_origin.encode('utf-8'), hashlib.sha256).digest()
        ).decode('utf-8')

        authorization_origin = f'api_key="{API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode('utf-8')

        params = {"authorization": authorization, "date": date, "host": HOST}
        return f"wss://{HOST}{PATH}?{urlencode(params)}"

    def _build_messages(self, user_message: str):
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        messages.append({"role": "user", "content": user_message})
        return messages

    def _execute_tool(self, tool_name: str, args: Dict) -> str:
        if tool_name not in TOOLS:
            return f"❌ 未知工具: {tool_name}"
        try:
            self.logger.info(f"调用工具: {tool_name} | 参数: {args}")
            result = TOOLS[tool_name](**args)
            self.logger.info(f"工具执行成功: {tool_name}")
            return result
        except Exception as e:
            self.logger.error(f"工具执行异常: {e}", exc_info=True)
            return f"❌ 工具执行失败: {str(e)}"

    def chat(self, user_message: str):
        self.history.append({"role": "user", "content": user_message})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

        current_response = [""]

        ws_url = self._generate_url()

        def on_open(ws):
            req = {
                "header": {"app_id": APPID, "uid": "user123"},
                "parameter": {"chat": {"domain": DOMAIN, "temperature": 0.2, "max_tokens": 4096}},
                "payload": {"message": {"text": self._build_messages(user_message)}}
            }
            ws.send(json.dumps(req))

        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data["header"]["code"] != 0:
                    print(f"\n❌ 错误: {data['header'].get('message')}")
                    ws.close()
                    return

                for item in data["payload"]["choices"]["text"]:
                    content = item.get("content", "")
                    current_response[0] += content
                    print(content, end="", flush=True)

                if data["header"].get("status") == 2:
                    print()
                    ws.close()
            except:
                ws.close()

        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=lambda ws, err: self.logger.error(f"WebSocket错误: {err}")
        )
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        response_text = current_response[0].strip()
        print(f"\n[调试] 模型原始输出: {response_text}")

        # ==================== 强力提取工具调用 ====================
        tool_call = None
        dir_match = re.search(r'"directory"\s*:\s*"([^"]+)"', response_text)
        if dir_match:
            directory = dir_match.group(1)
            tool_call = {"tool": "txt_statistics", "args": {"directory": directory}}
            print(f"[成功提取] directory = {directory}")

        # 执行工具
        if tool_call:
            print("\n[工具调用] 正在统计TXT文件，请稍等...")
            tool_result = self._execute_tool("txt_statistics", tool_call.get("args", {}))

            # 直接打印工具结果（不再发起第二次WebSocket，避免 kernel error）
            print("\n星火回复：")
            print(tool_result)

            self.history.append({"role": "tool", "content": tool_result})
            self.history.append({"role": "assistant", "content": tool_result})
            return tool_result

        # 普通回复（没有工具调用）
        if response_text:
            self.history.append({"role": "assistant", "content": response_text})
            return response_text

        return "抱歉，处理出现问题，请重试。"

    def run(self):
        print("🤖 ChatRobot（带TXT统计工具）已启动")
        print("支持命令: /clear、/system 新提示、exit\n")

        while True:
            try:
                user_input = input("你: ").strip()
                if user_input.lower() in ["exit", "quit", "退出"]:
                    print("👋 再见！")
                    break
                if user_input == "/clear":
                    self.clear_history()
                    continue
                if user_input.startswith("/system "):
                    self.set_system_prompt(user_input[8:].strip())
                    continue

                print("星火: ", end="")
                self.chat(user_input)
                print()

            except KeyboardInterrupt:
                print("\n👋 已退出")
                break
            except Exception as e:
                print(f"\n❌ 发生错误: {e}")


if __name__ == "__main__":
    robot = ChatRobot()
    robot.run()