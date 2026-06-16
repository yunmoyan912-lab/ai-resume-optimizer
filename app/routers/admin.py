"""管理员后台路由"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, timedelta
from pathlib import Path

from app.database import get_db
from app import models, schemas
from app.services.auth_service import get_admin_user, hash_password, get_optional_user

router = APIRouter(prefix="/admin", tags=["管理员后台"])

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"


# ========== 管理后台页面（不强制验证，JS 自行检查） ==========

@router.get("/", response_class=HTMLResponse)
async def admin_page():
    """管理员后台页面"""
    admin_file = TEMPLATES_DIR / "admin.html"
    if admin_file.is_file():
        return HTMLResponse(content=admin_file.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>管理后台</h1><p>admin.html 未找到</p>")


# ========== 用户管理 ==========

@router.get("/users")
def list_users(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        search: Optional[str] = None,
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """获取用户列表"""
    q = db.query(models.User)
    if search:
        q = q.filter(models.User.username.contains(search))

    total = q.count()
    users = q.order_by(models.User.created_at.desc()).offset((page - 1) * size).limit(size).all()

    result = []
    for u in users:
        resume_count = db.query(models.Resume).filter(models.Resume.user_id == u.id).count()
        result.append({
            "id": u.id,
            "username": u.username,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "resume_count": resume_count,
            "created_at": u.created_at,
        })

    return {"total": total, "page": page, "size": size, "items": result}


@router.put("/users/{user_id}")
def update_user(
        user_id: int,
        is_admin: Optional[int] = None,
        is_active: Optional[int] = None,
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """更新用户状态（设为管理员/禁用）"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的状态")

    if is_admin is not None:
        user.is_admin = is_admin
    if is_active is not None:
        user.is_active = is_active
    db.commit()
    return {"detail": "更新成功"}


@router.delete("/users/{user_id}")
def delete_user(
        user_id: int,
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """删除用户"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    db.delete(user)
    db.commit()
    return {"detail": "删除成功"}


@router.post("/users/{user_id}/reset-password")
def reset_password(
        user_id: int,
        new_password: str = Query(..., min_length=6),
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """重置用户密码"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.hashed_password = hash_password(new_password)
    db.commit()
    return {"detail": "密码已重置"}


# ========== 简历管理 ==========

@router.get("/resumes")
def list_all_resumes(
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
        user_id: Optional[int] = None,
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """获取所有简历列表"""
    q = db.query(models.Resume)
    if user_id:
        q = q.filter(models.Resume.user_id == user_id)

    total = q.count()
    resumes = q.order_by(models.Resume.created_at.desc()).offset((page - 1) * size).limit(size).all()

    result = []
    for r in resumes:
        owner = db.query(models.User).filter(models.User.id == r.user_id).first()
        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "username": owner.username if owner else "unknown",
            "ats_score": r.ats_score or 0,
            "jd_match_score": r.jd_match_score,
            "created_at": r.created_at,
        })

    return {"total": total, "page": page, "size": size, "items": result}


@router.delete("/resumes/{resume_id}")
def admin_delete_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """管理员删除简历"""
    r = db.query(models.Resume).filter(models.Resume.id == resume_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(r)
    db.commit()
    return {"detail": "删除成功"}


# ========== 系统统计 ==========

@router.get("/stats")
def get_system_stats(
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """获取系统全局统计"""
    total_users = db.query(models.User).count()
    total_resumes = db.query(models.Resume).count()
    total_teams = db.query(models.Team).count()

    today = date.today().isoformat()
    today_resumes = db.query(models.Resume).filter(
        func.date(models.Resume.created_at) == today
    ).count()
    today_users = db.query(models.User).filter(
        func.date(models.User.created_at) == today
    ).count()

    total_tokens = db.query(func.sum(models.UsageLog.tokens_prompt + models.UsageLog.tokens_completion)).scalar() or 0
    total_cost = db.query(func.sum(models.UsageLog.cost_usd)).scalar() or 0
    total_api_calls = db.query(models.UsageLog).count()

    provider_stats = db.query(
        models.UsageLog.provider,
        func.count(models.UsageLog.id),
        func.sum(models.UsageLog.tokens_prompt + models.UsageLog.tokens_completion),
    ).group_by(models.UsageLog.provider).all()

    by_provider = {}
    for provider, count, tokens in provider_stats:
        by_provider[provider] = {"calls": count, "tokens": tokens or 0}

    daily_trend = []
    for i in range(6, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        count = db.query(models.Resume).filter(func.date(models.Resume.created_at) == d).count()
        daily_trend.append({"date": d, "count": count})

    return {
        "total_users": total_users,
        "total_resumes": total_resumes,
        "total_teams": total_teams,
        "today_users": today_users,
        "today_resumes": today_resumes,
        "total_tokens": total_tokens,
        "total_cost_usd": total_cost / 1_000_000 if total_cost else 0,
        "total_api_calls": total_api_calls,
        "by_provider": by_provider,
        "daily_trend": daily_trend,
    }


# ========== API Key 全局管理 ==========

@router.get("/api-keys")
def list_all_api_keys(
        db: Session = Depends(get_db),
        admin: models.User = Depends(get_admin_user),
):
    """获取所有用户的 API Key 配置"""
    keys = db.query(models.UserApiKey).all()
    result = []
    for k in keys:
        user = db.query(models.User).filter(models.User.id == k.user_id).first()
        result.append({
            "id": k.id,
            "user_id": k.user_id,
            "username": user.username if user else "unknown",
            "provider": k.provider,
            "api_key": k.api_key[:8] + "****",
            "is_active": k.is_active,
            "created_at": k.created_at,
        })
    return result


# ========== 系统配置 ==========

@router.get("/config")
def get_system_config(
        admin: models.User = Depends(get_admin_user),
):
    """获取系统配置"""
    from app.config import settings
    return {
        "default_provider": settings.DEFAULT_PROVIDER,
        "providers": {
            "deepseek": {"model": settings.DEEPSEEK_MODEL, "base_url": settings.DEEPSEEK_BASE_URL},
            "qwen": {"model": settings.QWEN_MODEL, "base_url": settings.QWEN_BASE_URL},
            "kimi": {"model": settings.KIMI_MODEL, "base_url": settings.KIMI_BASE_URL},
            "mimo": {"model": settings.MIMO_MODEL, "base_url": settings.MIMO_BASE_URL},
        },
    }
