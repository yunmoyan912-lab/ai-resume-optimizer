"""AI 简历优化器 - FastAPI 入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, SessionLocal
from app import models
from app.routers import pages, auth, resume, api_keys, export, admin

app = FastAPI(title="AI 简历优化器", version="2.0")

# CORS 支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(pages.router)      # 页面: / , /login
app.include_router(auth.router)       # 认证: /auth/register, /auth/login, /auth/me
app.include_router(resume.router)     # 简历: /optimize, /upload, /history, /batch, /teams, /usage
app.include_router(api_keys.router)   # API Key: /api-keys
app.include_router(export.router)     # 导出: /export/{id}?format=pdf|docx
app.include_router(admin.router)      # 管理后台: /admin/


@app.on_event("startup")
def init_db():
    """启动时自动建表 + 补列 + 创建默认管理员"""
    try:
        models.Base.metadata.create_all(bind=engine)
        print("[SUCCESS] 数据库连接成功，表已就绪")
    except Exception as e:
        print(f"[ERROR] 数据库连接失败: {e}")
        print("[ERROR] 请先启动 MySQL 服务")
        return

    # 自动补列（兼容已有旧表）
    from sqlalchemy import text
    db = SessionLocal()
    try:
        alter_sqls = [
            "ALTER TABLE users ADD COLUMN is_admin INT DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_active INT DEFAULT 1",
            "ALTER TABLE resumes ADD COLUMN job_description TEXT",
            "ALTER TABLE resumes ADD COLUMN jd_match_score INT",
            "ALTER TABLE resumes ADD COLUMN jd_match_analysis TEXT",
            "ALTER TABLE resumes ADD COLUMN batch_id VARCHAR(36)",
        ]
        for sql in alter_sqls:
            try:
                db.execute(text(sql))
                db.commit()
            except Exception:
                db.rollback()  # 列已存在则忽略
    finally:
        db.close()

    # 自动创建默认管理员 root/root
    from app.services.auth_service import hash_password
    db = SessionLocal()
    try:
        admin = db.query(models.User).filter(models.User.username == "root").first()
        if not admin:
            admin = models.User(
                username="root",
                hashed_password=hash_password("root"),
                is_admin=1,
                is_active=1,
            )
            db.add(admin)
            db.commit()
            print("[OK] 默认管理员已创建: root / root")
        elif not admin.is_admin:
            admin.is_admin = 1
            db.commit()
            print("[OK] root 用户已设为管理员")
    finally:
        db.close()
