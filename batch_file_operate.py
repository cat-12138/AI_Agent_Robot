import os
import json


# ==================== 内置工具类 ====================
class FileToolkit:
    def __init__(self, encoding="utf-8"):
        self.encoding = encoding

    def read_txt_lines(self, file_path):
        if not os.path.exists(file_path):
            return f"错误：文件{file_path}不存在"
        with open(file_path, "r", encoding=self.encoding) as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]
        return lines

    def write_txt(self, file_path, content, append=False):
        mode = "a" if append else "w"
        with open(file_path, mode, encoding=self.encoding) as f:
            if isinstance(content, list):
                f.write("\n".join(content))
            else:
                f.write(content)
        return f"成功：TXT文件已保存至{file_path}"


# 实例化工具类
ft = FileToolkit()


# ==================== 批量处理逻辑（终极版） ====================
def batch_rename_and_clean(input_dir="txt_files", output_dir="cleaned_files"):
    if not os.path.isdir(input_dir):
        print(f"❌ 未找到文件夹：{input_dir}")
        return

    os.makedirs(output_dir, exist_ok=True)
    file_list = [f for f in os.listdir(input_dir) if f.endswith(".txt")]

    if not file_list:
        print("ℹ️  文件夹内无TXT文件可处理。")
        return

    print(f"🔧 开始处理 {len(file_list)} 个文件...\n")

    # 定义需要过滤的关键词（可自定义添加）
    filter_keywords = ["会被清理", "注释", "说明", "测试"]

    for index, filename in enumerate(file_list, 1):
        src_path = os.path.join(input_dir, filename)
        raw_lines = ft.read_txt_lines(src_path)
        cleaned_lines = []

        for line in raw_lines:
            # 1. 过滤 # 开头的注释行
            if line.startswith("#"):
                continue
            # 2. 过滤包含指定关键词的说明行
            if any(keyword in line for keyword in filter_keywords):
                continue
            # 3. 保留有效行
            cleaned_lines.append(line)

        new_filename = f"file_{index:03d}.txt"
        dest_path = os.path.join(output_dir, new_filename)
        ft.write_txt(dest_path, cleaned_lines)
        print(f"✅ 已处理：{filename} -> {new_filename}")

    print(f"\n🎉 批量处理完成！请查看 {output_dir} 文件夹")


# ==================== 运行 ====================
if __name__ == "__main__":
    batch_rename_and_clean()