"""Pro: 简历导出路由 - PDF/Word 格式导出"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO

from app.database import get_db
from app import models
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/export", tags=["Pro: 导出"])


def _generate_pdf(content: str, filename: str) -> BytesIO:
    """生成 PDF 文件"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    import os

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    # 尝试注册中文字体
    font_name = "Helvetica"
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simhei.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                pdfmetrics.registerFont(TTFont("Chinese", fp))
                font_name = "Chinese"
                break
            except Exception:
                continue

    c.setFont(font_name, 10)
    y = height - 30 * mm

    for line in content.split("\n"):
        if y < 20 * mm:
            c.showPage()
            c.setFont(font_name, 10)
            y = height - 30 * mm
        c.drawString(25 * mm, y, line[:80])
        y -= 14

    c.save()
    buf.seek(0)
    return buf


def _generate_docx(content: str, filename: str) -> BytesIO:
    """生成 Word 文件"""
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    style = doc.styles["Normal"]
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(4)

    for line in content.split("\n"):
        p = doc.add_paragraph(line)
        p.paragraph_format.space_after = Pt(2)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


@router.get("/{resume_id}")
def export_resume(
        resume_id: int,
        format: str = "pdf",
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """导出简历为 PDF 或 Word"""
    r = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")

    content = r.optimized_content or r.original_content or ""
    safe_name = f"resume_{resume_id}"

    if format == "docx":
        buf = _generate_docx(content, safe_name)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={safe_name}.docx"},
        )
    else:
        buf = _generate_pdf(content, safe_name)
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={safe_name}.pdf"},
        )
