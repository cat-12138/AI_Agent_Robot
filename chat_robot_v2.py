import time
import hashlib
import base64
import hmac
import json
import websocket
import ssl
import logging
from urllib.parse import urlencode
from concurrent.futures import ThreadPoolExecutor

# ==================== 配置 ====================
APPID = "f34ada10"
API_KEY = "99073aaa514be0ba85e1c5ea7798de31"
API_SECRET = "YWFhN2E1MmI1OTQyYTM4MzVhZDVhMWY5"

HOST = "spark-api.xf-yun.com"
PATH = "/v3.5/chat"
DOMAIN = "generalv3.5"
# ==============================================

# ==================== logging 配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("robot_log.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
# ======================================================


class ChatRobot:
    def __init__(self):
        self.history = []
        self.system_prompt = "你是一个简洁专业的AI助手。"
        self.max_history = 10
        self.current_reply = ""
        self.executor = ThreadPoolExecutor(max_workers=1)  # 线程池解决异步冲突
        logging.info("✅ 对话机器人初始化成功")

    def set_system_prompt(self, prompt):
        self.system_prompt = prompt
        logging.info(f"🔧 系统提示词已更新：{prompt[:30]}...")

    def _build_message(self):
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(self.history)
        return messages

    def _generate_auth_url(self):
        try:
            now = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
            signature_origin = f"host: {HOST}\ndate: {now}\nGET {PATH} HTTP/1.1"

            sha = hmac.new(
                API_SECRET.encode(),
                signature_origin.encode(),
                hashlib.sha256
            ).digest()

            signature = base64.b64encode(sha).decode()
            auth_origin = f'api_key="{API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
            authorization = base64.b64encode(auth_origin.encode()).decode()

            params = urlencode({
                "authorization": authorization,
                "date": now,
                "host": HOST
            })
            return f"wss://{HOST}{PATH}?{params}"

        except Exception as e:
            logging.error(f"❌ 鉴权URL生成失败：{str(e)}")
            return None

    def _on_message(self, ws, msg):
        try:
            data = json.loads(msg)
            if data["header"]["code"] != 0:
                err = data["header"]["message"]
                logging.error(f"❌ 接口返回错误：{err}")
                ws.close()
                return

            content = data["payload"]["choices"]["text"][0]["content"]
            self.current_reply += content

            if data["header"]["status"] == 2:
                self.history.append({"role": "assistant", "content": self.current_reply})
                logging.info(f"🤖 AI回复：{self.current_reply[:50]}...")
                ws.close()

        except Exception as e:
            logging.error(f"❌ 消息解析异常：{str(e)}")
            ws.close()

    def _on_open(self, ws):
        try:
            req = {
                "header": {"app_id": APPID},
                "parameter": {"chat": {"domain": DOMAIN, "temperature": 0.7}},
                "payload": {"message": {"text": self._build_message()}}
            }
            ws.send(json.dumps(req))
        except Exception as e:
            logging.error(f"❌ 发送消息失败：{str(e)}")

    def _run_websocket(self, question):
        """线程中运行WebSocket，避免阻塞Gradio"""
        self.current_reply = ""
        self.history.append({"role": "user", "content": question})
        logging.info(f"👤 用户提问：{question}")

        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2:]

        url = self._generate_auth_url()
        if not url:
            logging.error("❌ URL生成失败，无法发送请求")
            return "请求生成失败，请重试"

        ws = websocket.WebSocketApp(
            url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=lambda ws, err: logging.error(f"❌ WebSocket错误：{err}"),
            on_close=lambda ws, c, m: logging.info("🔌 连接已关闭")
        )

        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        return self.current_reply

    def ask(self, question):
        try:
            if not question or not question.strip():
                logging.warning("⚠️ 用户输入为空")
                return "请输入有效问题"  # 必须返回字符串，不能返回None

            # 在线程中运行，避免阻塞Gradio
            future = self.executor.submit(self._run_websocket, question)
            result = future.result(timeout=30)  # 30秒超时
            return result if result else "未获取到有效回复"

        except Exception as e:
            logging.error(f"❌ 对话异常：{str(e)}")
            return f"程序出错：{str(e)}"


# ==================== 全局单例 + 提供给 Gradio 调用的 chat 函数 ====================
robot = ChatRobot()

def chat(message, history=None):
    """Gradio 兼容的聊天函数，必须返回字符串"""
    return robot.ask(message)


# ==================== 运行 ====================
if __name__ == "__main__":
    print("=== 稳定版对话机器人（带日志）===")
    print("输入 exit 退出\n")

    while True:
        user_input = input("你：").strip()
        if user_input.lower() == "exit":
            logging.info("👋 用户退出程序")
            print("再见！")
            break
        print("AI：", end="")
        print(robot.ask(user_input))
