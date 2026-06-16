"""测试 PDF 解析功能"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.file_parser import parse_file

# 查找项目目录下的 PDF 文件
pdf_files = glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "*.pdf"))
pdf_files += glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), "**", "*.pdf"), recursive=False)

if not pdf_files:
    print("未找到 PDF 测试文件。请将一个 PDF 文件放到项目目录下再运行此脚本。")
    print("示例: 将简历.pdf 放到 ai-resume-optimizer/ 目录下")
    sys.exit(0)

print(f"找到 {len(pdf_files)} 个 PDF 文件:\n")

for pdf_path in pdf_files[:3]:  # 最多测试3个
    filename = os.path.basename(pdf_path)
    print(f"{'='*50}")
    print(f"文件: {filename}")
    print(f"{'='*50}")

    try:
        with open(pdf_path, 'rb') as f:
            content = f.read()

        text = parse_file(filename, content)
        print(f"提取成功! 共 {len(text)} 字符")
        print(f"预览 (前300字):\n{text[:300]}")
        print()
    except Exception as e:
        print(f"提取失败: {e}")
        print()

print("测试完成!")
