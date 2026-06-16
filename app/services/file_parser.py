import io
import re
from docx import Document


ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def parse_file(filename: str, file_content: bytes) -> str:
    """根据文件类型解析内容，返回纯文本"""
    ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {ext}，仅支持 {ALLOWED_EXTENSIONS}")

    if ext == ".pdf":
        return _parse_pdf(file_content)
    elif ext == ".docx":
        return _parse_docx(file_content)
    elif ext == ".txt":
        return _parse_txt(file_content)

    raise ValueError(f"未处理的文件类型: {ext}")


def _parse_pdf(file_content: bytes) -> str:
    """PDF 文本提取，三级降级 + OCR 兜底"""
    text = ""

    # 方案1：pdfplumber（对中文 PDF 最佳）
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            pages_text = []
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            text = "\n".join(pages_text).strip()
    except Exception as e:
        print(f"[PDF] pdfplumber 提取失败: {e}")

    # 方案2：pymupdf 备用
    if not text:
        try:
            import fitz
            doc = fitz.open(stream=file_content, filetype="pdf")
            pages_text = []
            for page in doc:
                page_text = page.get_text("text")
                if page_text:
                    pages_text.append(page_text)
            text = "\n".join(pages_text).strip()
            doc.close()
        except Exception as e:
            print(f"[PDF] pymupdf 提取失败: {e}")

    # 方案3：PyPDF2 兜底
    if not text:
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(io.BytesIO(file_content))
            pages_text = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    pages_text.append(page_text)
            text = "\n".join(pages_text).strip()
        except Exception as e:
            print(f"[PDF] PyPDF2 提取失败: {e}")

    # 清理文本
    if text:
        text = _clean_pdf_text(text)

    # 方案4：OCR 识别图片型 PDF
    if not text:
        text = _ocr_pdf(file_content)

    if not text:
        raise ValueError("无法从该 PDF 中提取文本。可能原因：文件为扫描件（图片PDF）或文件已加密/损坏。请尝试使用 Word 文档或直接粘贴文本")

    return text


def _ocr_pdf(file_content: bytes) -> str:
    """对图片型 PDF 进行 OCR 识别（rapidocr-onnxruntime）"""
    try:
        import fitz
        doc = fitz.open(stream=file_content, filetype="pdf")
    except Exception as e:
        print(f"[OCR] 无法打开 PDF: {e}")
        return ""

    # 将每页转为图片
    images = []
    for page in doc:
        mat = fitz.Matrix(2, 2)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        images.append(img_bytes)
    doc.close()

    if not images:
        return ""

    try:
        from rapidocr_onnxruntime import RapidOCR
        import numpy as np
        from PIL import Image

        ocr = RapidOCR()
        all_text = []
        for img_bytes in images:
            img = Image.open(io.BytesIO(img_bytes))
            img_np = np.array(img)
            result, _ = ocr(img_np)
            if result:
                page_text = "\n".join([item[1] for item in result]).strip()
                if page_text:
                    all_text.append(page_text)

        text = "\n".join(all_text).strip()
        if text:
            text = _clean_pdf_text(text)
        return text
    except ImportError:
        print("[OCR] rapidocr 未安装，跳过 OCR")
        return ""
    except Exception as e:
        print(f"[OCR] OCR 识别失败: {e}")
        return ""


def _clean_pdf_text(text: str) -> str:
    """清理 PDF 提取的文本，修复常见问题"""
    # 修复中文 PDF 常见的字间距问题（如 "我 们" → "我们"）
    text = re.sub(r'([\u4e00-\u9fff])\s+([\u4e00-\u9fff])', r'\1\2', text)

    # 合并被断行的段落：仅当前行末尾是中文且下一行开头也是中文时合并
    lines = text.split('\n')
    merged = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            merged.append("")
            continue
        if merged and merged[-1] and not merged[-1].endswith("\n"):
            prev = merged[-1]
            # 前一行末尾是中文，当前行开头是中文 → 合并（无空格）
            if re.search(r'[\u4e00-\u9fff]$', prev) and re.match(r'^[\u4e00-\u9fff]', stripped):
                merged[-1] = prev + stripped
                continue
        merged.append(stripped)

    return "\n".join(merged).strip()


def _parse_docx(file_content: bytes) -> str:
    doc = Document(io.BytesIO(file_content))
    text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
    text = "\n".join(text_parts).strip()
    if not text:
        raise ValueError("Word 文件内容为空")
    return text


def _parse_txt(file_content: bytes) -> str:
    """解析纯文本文件，尝试多种编码"""
    for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'gb18030']:
        try:
            text = file_content.decode(encoding)
            return text.strip()
        except UnicodeDecodeError:
            continue
    return file_content.decode('utf-8', errors='replace').strip()
