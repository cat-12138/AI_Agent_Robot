import os
import re
from typing import Dict, Any

def txt_statistics(directory: str) -> str:
    """批量统计指定目录下所有 TXT 文件的信息（行数、词数、字符数）"""
    if not os.path.isdir(directory):
        return f"❌ 错误：目录不存在或不是文件夹 -> {directory}"

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

                    results.append(f"📄 {filepath}\n   行数: {lines} | 词数: {words} | 字符: {chars}")
                except Exception as e:
                    results.append(f"⚠️ 读取失败 {filepath}: {str(e)}")

    if not results:
        return f"✅ 扫描完成：目录 {directory} 中没有找到任何 .txt 文件"

    summary = f"✅ 扫描完成！共找到 {txt_count} 个 TXT 文件\n" + "\n".join(results)
    return summary

# 👇 加在这里，让网页能调用
def file_stat(file_path):
    return txt_statistics(os.path.dirname(file_path))
