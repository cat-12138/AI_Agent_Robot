import re
import os
import json


# ==================== 内置工具类（直接写在脚本里，无需导入） ====================
class FileToolkit:
    def __init__(self, encoding="utf-8"):
        self.encoding = encoding

    def read_txt(self, file_path):
        if not os.path.exists(file_path):
            return f"错误：文件{file_path}不存在"
        with open(file_path, "r", encoding=self.encoding) as f:
            return f.read()

    def read_txt_lines(self, file_path):
        if not os.path.exists(file_path):
            return f"错误：文件{file_path}不存在"
        with open(file_path, "r", encoding=self.encoding) as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        return lines

    def write_json(self, file_path, data, indent=4):
        with open(file_path, "w", encoding=self.encoding) as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        return f"成功：JSON文件已保存至{file_path}"


# 实例化工具类
ft = FileToolkit()

# ==================== 正则提取规则 ====================
REGEX_RULES = {
    "手机号": r"1[3-9]\d{9}",
    "邮箱": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "日期": r"\d{4}-\d{2}-\d{2}",
    "URL链接": r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
}


# ==================== 提取逻辑 ====================
def extract_from_txt(file_path):
    content = ft.read_txt(file_path)
    if isinstance(content, str) and "错误" in content:
        print(f"❌ 无法读取文件：{file_path}")
        return None

    result = {}
    for name, pattern in REGEX_RULES.items():
        matches = re.findall(pattern, content)
        result[name] = list(set(matches))  # 去重
    return result


def batch_extract(folder_path="txt_files"):
    if not os.path.exists(folder_path):
        print(f"❌ 文件夹 '{folder_path}' 不存在，请在项目根目录创建并放入测试TXT文件。")
        return

    all_data = {}
    print(f"🔎 开始扫描文件夹：{folder_path}\n")

    for filename in os.listdir(folder_path):
        if filename.endswith(".txt"):
            print(f"📄 正在处理：{filename}")
            full_path = os.path.join(folder_path, filename)
            result = extract_from_txt(full_path)
            if result:
                all_data[filename] = result

    # 保存结果
    ft.write_json("extracted_info.json", all_data)
    print("\n✅ 批量提取完成！结果已写入 extracted_info.json")


# ==================== 运行 ====================
if __name__ == "__main__":
    batch_extract()