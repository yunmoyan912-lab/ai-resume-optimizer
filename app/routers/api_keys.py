"""API Key 管理路由 - 用户自定义配置模型 API Key"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import models, schemas
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api-keys", tags=["API Key 管理"])


@router.get("", response_model=List[schemas.ApiKeyResponse])
def list_api_keys(
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取当前用户的所有 API Key"""
    keys = db.query(models.UserApiKey).filter(
        models.UserApiKey.user_id == user.id
    ).order_by(models.UserApiKey.created_at.desc()).all()
    return keys


@router.post("", response_model=schemas.ApiKeyResponse)
def create_api_key(
        req: schemas.ApiKeyCreate,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """添加或更新 API Key（同提供商只保留一个）"""
    # 检查是否已存在该提供商的 key
    existing = db.query(models.UserApiKey).filter(
        models.UserApiKey.user_id == user.id,
        models.UserApiKey.provider == req.provider,
    ).first()

    if existing:
        existing.api_key = req.api_key
        if req.base_url is not None:
            existing.base_url = req.base_url
        if req.model is not None:
            existing.model = req.model
        existing.is_active = 1
        db.commit()
        db.refresh(existing)
        return existing

    key = models.UserApiKey(
        user_id=user.id,
        provider=req.provider,
        api_key=req.api_key,
        base_url=req.base_url,
        model=req.model,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return key


@router.put("/{key_id}", response_model=schemas.ApiKeyResponse)
def update_api_key(
        key_id: int,
        req: schemas.ApiKeyUpdate,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """更新指定的 API Key"""
    key = db.query(models.UserApiKey).filter(
        models.UserApiKey.id == key_id,
        models.UserApiKey.user_id == user.id,
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    if req.api_key is not None:
        key.api_key = req.api_key
    if req.base_url is not None:
        key.base_url = req.base_url
    if req.model is not None:
        key.model = req.model
    if req.is_active is not None:
        key.is_active = req.is_active

    db.commit()
    db.refresh(key)
    return key


@router.delete("/{key_id}")
def delete_api_key(
        key_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """删除指定的 API Key"""
    key = db.query(models.UserApiKey).filter(
        models.UserApiKey.id == key_id,
        models.UserApiKey.user_id == user.id,
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    db.delete(key)
    db.commit()
    return {"detail": "删除成功"}


@router.post("/{key_id}/toggle")
def toggle_api_key(
        key_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """启用/禁用 API Key"""
    key = db.query(models.UserApiKey).filter(
        models.UserApiKey.id == key_id,
        models.UserApiKey.user_id == user.id,
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="API Key 不存在")

    key.is_active = 0 if key.is_active else 1
    db.commit()
    db.refresh(key)
    return {"is_active": key.is_active}


class ApiKeyTestRequest(BaseModel):
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None


@router.post("/test")
def test_api_key(
        req: ApiKeyTestRequest,
        user: models.User = Depends(get_current_user),
):
    """测试 API Key 连接"""
    from openai import OpenAI
    from app.services.ai_service import _get_system_config, PROVIDERS

    cfg = _get_system_config(req.provider)
    base_url = req.base_url or cfg["base_url"]
    model = req.model or cfg["model"]

    try:
        client = OpenAI(api_key=req.api_key, base_url=base_url)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        return {"ok": True, "model": model}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
