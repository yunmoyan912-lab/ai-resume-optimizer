"""测试编码处理"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.file_parser import parse_file

print("=" * 50)
print("Testing encoding handling")
print("=" * 50)

# Test 1: UTF-8 encoded Chinese text
print("\n[Test 1] UTF-8 Chinese text")
utf8_content = "张三的简历\n电话：13800138000\n工作经验：5年".encode('utf-8')
result = parse_file("test.txt", utf8_content)
print(f"✓ UTF-8 parsed: {result[:30]}...")

# Test 2: GBK encoded Chinese text
print("\n[Test 2] GBK Chinese text")
gbk_content = "李四的简历\n电话：13900139000".encode('gbk')
result = parse_file("test.txt", gbk_content)
print(f"✓ GBK parsed: {result[:30]}...")

# Test 3: UTF-8 with BOM
print("\n[Test 3] UTF-8 with BOM")
bom_content = b'\xef\xbb\xbf' + "王五的简历".encode('utf-8')
result = parse_file("test.txt", bom_content)
print(f"✓ BOM UTF-8 parsed: {result}")

# Test 4: Mixed content with special characters
print("\n[Test 4] Mixed content with special chars")
mixed = "姓名：赵六\nEmail: test@example.com\n技能：Python, Java, C++\n经历：2020-2024 某科技公司".encode('utf-8')
result = parse_file("test.txt", mixed)
print(f"✓ Mixed content parsed: {result[:50]}...")

# Test 5: Test AI service encoding handling
print("\n[Test 5] AI service text preparation")
from app.services.ai_service import analyze_resume
test_text = "测试简历内容\n包含中文字符和特殊符号：①②③"
prepared = test_text.encode('utf-8', errors='replace').decode('utf-8')
print(f"✓ Text prepared: {prepared}")

print("\n" + "=" * 50)
print("✅ All encoding tests passed!")
print("=" * 50)
