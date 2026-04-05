import time
import hashlib
import base64
import hmac
import json
import websocket
import os
import re
from urllib.parse import urlencode

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
    """统计目录下所有TXT文件的信息"""
    if not os.path.isdir(directory):
        return f"❌ 目录不存在: {directory}"

    results = []
    count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith('.txt'):
                count += 1
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        text = f.read()
                    lines = len(text.splitlines())
                    words = len(re.findall(r'\w+', text))
                    chars = len(text)
                    results.append(f"📄 {file}\n   行数:{lines} | 词数:{words} | 字符:{chars}")
                except Exception as e:
                    results.append(f"⚠️ 读取失败 {file}: {e}")

    if not results:
        return f"✅ {directory} 中没有找到TXT文件"

    return f"✅ 共找到 {count} 个TXT文件\n\n" + "\n\n".join(results)


class ChatRobot:
    def __init__(self):
        self.history = []
        self.system_prompt = (
            "你是一个严格服从指令的AI助手。\n"
            "当用户要求统计TXT文件信息时，**必须只输出一行纯JSON**，不要输出任何其他文字！\n"
            "格式必须严格如下（一行，不能换行，不能加说明）：\n"
            "{\"tool\": \"txt_statistics\", \"args\": {\"directory\": \"D:\\\\pycharm\\\\PythonProject01\\\\txt_files\"}}\n\n"
            "工具返回结果后，你再用自然语言回复用户。\n"
            "其他问题正常回答。\n现在开始严格执行！"
        )
        self.max_history = 12
        self.current_user_message = ""
        self.current_reply = ""

    def _build_messages(self):
        """构建消息列表（修复后的正确名称）"""
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        return messages

    def _generate_auth_url(self):
        now = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        signature_origin = f"host: {HOST}\ndate: {now}\nGET {PATH} HTTP/1.1"
        signature = base64.b64encode(
            hmac.new(API_SECRET.encode(), signature_origin.encode(), hashlib.sha256).digest()
        ).decode()
        auth_origin = f'api_key="{API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
        authorization = base64.b64encode(auth_origin.encode()).decode()
        params = urlencode({"authorization": authorization, "date": now, "host": HOST})
        return f"wss://{HOST}{PATH}?{params}"

    def _execute_tool(self, tool_call: dict) -> str:
        """执行工具"""
        if tool_call.get("tool") != "txt_statistics":
            return "未知工具"
        try:
            directory = tool_call["args"]["directory"]
            return txt_statistics(directory)
        except Exception as e:
            return f"工具执行失败: {e}"

    def _on_open(self, ws):
        req = {
            "header": {"app_id": APPID, "uid": "user123"},
            "parameter": {
                "chat": {
                    "domain": DOMAIN,
                    "temperature": 0.3,
                    "max_tokens": 4096
                }
            },
            "payload": {
                "message": {
                    "text": self._build_messages()  # 使用正确的复数方法
                }
            }
        }
        ws.send(json.dumps(req))

    def _on_message(self, ws, msg):
        data = json.loads(msg)
        if data["header"]["code"] != 0:
            print("错误：", data["header"].get("message"))
            ws.close()
            return

        content = data["payload"]["choices"]["text"][0]["content"]
        self.current_reply += content
        print(content, end="", flush=True)

        if data["header"]["status"] == 2:
            print()
            ws.close()

    def ask(self, question: str):
        """支持工具调用的提问方法"""
        self.current_user_message = question
        self.current_reply = ""

        # 添加用户消息到历史
        self.history.append({"role": "user", "content": question})
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

        url = self._generate_auth_url()

        ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=lambda ws, err: print(f"错误: {err}")
        )
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        # ==================== 工具调用处理（新增核心逻辑） ====================
        response_text = self.current_reply.strip()

        # 尝试提取JSON（容错处理）
        json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
        if json_match:
            try:
                tool_call = json.loads(json_match.group(0))
                if isinstance(tool_call, dict) and tool_call.get("tool") == "txt_statistics":
                    print("\n[工具调用] 正在统计TXT文件...")
                    tool_result = self._execute_tool(tool_call)

                    # 把工具结果加入历史，让AI基于结果继续回复
                    self.history.append({"role": "tool", "content": tool_result})

                    # 再请求一次，让AI用自然语言回复结果
                    print("AI：", end="")
                    self.current_reply = ""
                    ws = websocket.WebSocketApp(
                        url,
                        on_open=self._on_open,
                        on_message=self._on_message
                    )
                    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
                    return

            except:
                pass  # 不是有效JSON，正常处理

        # 普通回复：把AI回答加入历史
        if self.current_reply:
            self.history.append({"role": "assistant", "content": self.current_reply})


# ==================== 测试运行 ====================
if __name__ == "__main__":
    robot = ChatRobot()
    print("=== ChatRobot（支持TXT统计工具）已启动 ===")
    print("输入 exit 退出\n")

    while True:
        user = input("你：").strip()
        if user.lower() == "exit":
            print("再见！")
            break
        if not user:
            continue

        print("AI：", end="")
        robot.ask(user)