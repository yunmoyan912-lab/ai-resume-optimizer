"""页面路由 - 负责返回前端 HTML 页面"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from pathlib import Path
import os

router = APIRouter()

# 使用项目根目录（main.py 所在目录）
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"
print(f"[DEBUG] __file__={__file__}")
print(f"[DEBUG] TEMPLATES_DIR={TEMPLATES_DIR}")
print(f"[DEBUG] exists={TEMPLATES_DIR.exists()}")
print(f"[DEBUG] cwd={os.getcwd()}")


@router.get("/", response_class=HTMLResponse)
async def read_root():
    index_file = TEMPLATES_DIR / "index.html"
    print(f"[DEBUG] index_file={index_file}, is_file={index_file.is_file()}")
    if index_file.is_file():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    # Fallback: try from cwd
    cwd_index = Path("templates/index.html")
    if cwd_index.is_file():
        return HTMLResponse(content=cwd_index.read_text(encoding="utf-8"))
    return HTMLResponse(content=f"<h1>AI简历优化器</h1><p>前端文件未找到</p><p>路径: {TEMPLATES_DIR}</p>")


@router.get("/login", response_class=HTMLResponse)
async def login_page():
    login_file = TEMPLATES_DIR / "login.html"
    if login_file.is_file():
        return HTMLResponse(content=login_file.read_text(encoding="utf-8"))
    cwd_login = Path("templates/login.html")
    if cwd_login.is_file():
        return HTMLResponse(content=cwd_login.read_text(encoding="utf-8"))
    return HTMLResponse(content=f"<h1>登录页面未找到</h1><p>路径: {TEMPLATES_DIR}</p>")
