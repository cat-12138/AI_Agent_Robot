import time
import hashlib
import base64
import hmac
import json
import websocket
import ssl
import os
from urllib.parse import urlencode

# ==================== 星火配置（直接用你自己的） ====================
APPID = "f34ada10"
API_KEY = "99073aaa514be0ba85e1c5ea7798de31"
API_SECRET = "YWFhN2E1MmI1OTQyYTM4MzVhZDVhMWY5"
HOST = "spark-api.xf-yun.com"
PATH = "/v3.5/chat"
DOMAIN = "generalv3.5"

# ==================== 本地知识库（读取txt_files所有文件） ====================
class LocalRAG:
    def __init__(self, txt_folder="txt_files"):
        self.txt_folder = txt_folder
        self.files = []
        self._load_all()

    def _load_all(self):
        """加载文件夹内所有txt文件"""
        if not os.path.exists(self.txt_folder):
            print(f"❌ 错误：文件夹 {self.txt_folder} 不存在")
            return
        for fname in os.listdir(self.txt_folder):
            if fname.endswith(".txt"):
                path = os.path.join(self.txt_folder, fname)
                with open(path, "r", encoding="utf-8") as f:
                    self.files.append({
                        "name": fname,
                        "content": f.read()
                    })
        print(f"✅ 已加载 {len(self.files)} 个TXT文件到知识库")

    def get_all_content(self):
        """拼接所有文件内容，用于给AI做上下文"""
        return "\n\n".join(f["content"] for f in self.files)

# ==================== 星火对话机器人（流式输出） ====================
class SparkChat:
    def __init__(self):
        self.result = ""

    def generate_url(self):
        """生成星火鉴权URL（官方标准）"""
        now = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
        signature_origin = f"host: {HOST}\ndate: {now}\nGET {PATH} HTTP/1.1"
        sha = hmac.new(
            API_SECRET.encode(),
            signature_origin.encode(),
            hashlib.sha256
        ).digest()
        signature = base64.b64encode(sha).decode()
        auth = f'api_key="{API_KEY}", algorithm="hmac-sha256", headers="host date request-line", signature="{signature}"'
        authorization = base64.b64encode(auth.encode()).decode()
        params = urlencode({"authorization": authorization, "date": now, "host": HOST})
        return f"wss://{HOST}{PATH}?{params}"

    def on_message(self, ws, msg):
        """接收流式响应"""
        data = json.loads(msg)
        if data["header"]["code"] != 0:
            print(f"\n❌ 接口错误：{data['header']['message']}")
            ws.close()
            return
        content = data["payload"]["choices"]["text"][0]["content"]
        self.result += content
        print(content, end="", flush=True)
        if data["header"]["status"] == 2:
            print("\n")
            ws.close()

    def ask(self, prompt):
        """发送请求并获取回答"""
        self.result = ""
        url = self.generate_url()
        # 修复了括号不匹配的问题，完全对齐
        ws = websocket.WebSocketApp(
            url,
            on_open=lambda w: w.send(json.dumps({
                "header": {"app_id": APPID},
                "parameter": {"chat": {"domain": DOMAIN, "temperature": 0.7}},
                "payload": {"message": {"text": [{"role": "user", "content": prompt}]}}
            })),
            on_message=self.on_message,
            on_error=lambda ws, err: print(f"\n❌ 连接错误：{err}")
        )
        ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
        return self.result

# ==================== RAG + AI 主程序 ====================
if __name__ == "__main__":
    # 初始化知识库和AI
    rag = LocalRAG()
    all_text = rag.get_all_content()
    bot = SparkChat()

    print("\n=== 本地知识库 + 星火AI 对话机器人 ===")
    print("提示：输入问题即可对话，输入 exit/退出 关闭\n")

    while True:
        user_input = input("你：").strip()
        if user_input.lower() in ["exit", "quit", "退出"]:
            print("👋 再见！")
            break
        if not user_input:
            continue

        # 构建RAG提示词：把本地文档+用户问题发给AI
        prompt = f"""
你是一个专业的助手，请严格基于下面的本地文档内容回答用户的问题。
如果文档里没有相关信息，就直接说「根据现有文档无法回答这个问题」，不要编造内容。

【本地文档内容】：
{all_text}

【用户问题】：
{user_input}

请用简洁、自然的中文回答：
"""
        print("AI：", end="")
        bot.ask(prompt)