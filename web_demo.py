import gradio as gr
import os
import json

from chat_robot_v2 import chat
from tool import txt_statistics
from extract_info import extract_from_txt


def agent_process(message: str, history: list, uploaded_file_obj):
    if not message or not message.strip():
        return history

    msg = message.strip()
    msg_lower = msg.lower()

    current_file_path = uploaded_file_obj.name if uploaded_file_obj is not None else None

    # 未上传文件却使用文件功能
    if current_file_path is None and any(k in msg_lower for k in ["统计", "抽取", "手机号", "邮箱", "日期", "链接", "文件内容", "看文件", "读文件"]):
        response = "⚠️ 请先上传 TXT 文件后再使用文件相关指令！"
        history.append({"role": "user", "content": msg})
        history.append({"role": "assistant", "content": response})
        return history

    # ==================== 工具路由 ====================
    if "统计" in msg_lower and current_file_path:
        folder = os.path.dirname(current_file_path)
        response = txt_statistics(folder)

    elif any(k in msg_lower for k in ["抽取", "手机号", "邮箱", "日期", "链接"]) and current_file_path:
        try:
            data = extract_from_txt(current_file_path)
            response = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            response = f"信息抽取失败: {str(e)}"

    elif any(k in msg_lower for k in ["文件内容", "看文件", "读文件"]) and current_file_path:
        try:
            with open(current_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if len(content) > 3000:
                content = content[:3000] + "\n\n...（内容过长，已截断）"
            response = f"📄 文件内容（{os.path.basename(current_file_path)}）:\n\n{content}"
        except Exception as e:
            response = f"读取文件失败: {str(e)}"

    else:
        try:
            response = chat(msg)
        except Exception as e:
            response = f"星火模型调用失败: {str(e)}"

    history.append({"role": "user", "content": msg})
    history.append({"role": "assistant", "content": response})
    return history


# ====================== 增强版界面 ======================
with gr.Blocks(title="AI智能文件助手", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 AI智能文件助手 (Agent版)")
    gr.Markdown("上传 TXT 文件后，用自然语言指令即可自动执行工具")

    # 文件状态栏
    file_status = gr.Markdown("ℹ️ **当前未上传文件**", elem_id="file_status")

    with gr.Tab("💬 智能对话"):
        chatbot = gr.Chatbot(height=580)

        with gr.Row():
            msg = gr.Textbox(
                label="输入指令",
                placeholder="例如：统计文件 / 抽取手机号和邮箱 / 查看文件内容",
                scale=6
            )
            file_upload = gr.File(
                label="上传 TXT 文件",
                file_types=[".txt"],
                scale=4
            )

        with gr.Row():
            submit_btn = gr.Button("发送", variant="primary", scale=2)
            clear_btn = gr.Button("清空对话", scale=1)

        # 示例问题按钮
        with gr.Row():
            gr.Button("📊 统计文件", size="small").click(
                fn=lambda: "统计文件", inputs=None, outputs=msg
            )
            gr.Button("🔍 抽取信息", size="small").click(
                fn=lambda: "抽取手机号和邮箱", inputs=None, outputs=msg
            )
            gr.Button("📖 查看文件内容", size="small").click(
                fn=lambda: "查看文件内容", inputs=None, outputs=msg
            )

    with gr.Tab("📋 使用说明"):
        gr.Markdown("""
        ### 支持的指令（上传文件后使用）：
        - **统计文件** → 统计行数、词数、字符数
        - **抽取信息 / 手机号 / 邮箱** → 自动提取关键信息
        - **查看文件内容 / 读文件** → 显示文件内容（过长自动截断）
        - 其他问题 → 直接与星火大模型对话
        """)

    # ==================== 事件绑定 ====================
    # 文件上传时更新状态栏
    def update_file_status(file_obj):
        if file_obj is None:
            return "ℹ️ **当前未上传文件**"
        return f"✅ **当前文件**：{os.path.basename(file_obj.name)}"

    file_upload.change(
        fn=update_file_status,
        inputs=file_upload,
        outputs=file_status
    )

    # 发送消息
    submit_btn.click(
        fn=agent_process,
        inputs=[msg, chatbot, file_upload],
        outputs=[chatbot]
    )

    msg.submit(
        fn=agent_process,
        inputs=[msg, chatbot, file_upload],
        outputs=[chatbot]
    )

    # 清空对话
    clear_btn.click(
        fn=lambda: [],
        inputs=None,
        outputs=[chatbot],
        queue=False
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
        theme=gr.themes.Soft()
    )