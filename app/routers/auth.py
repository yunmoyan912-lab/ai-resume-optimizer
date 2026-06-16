"""认证路由 - 注册、登录、获取用户信息"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.auth_service import (
    hash_password, verify_password, create_access_token, get_current_user
)

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=schemas.UserInfo)
def register(req: schemas.UserRegister, db: Session = Depends(get_db)):
    """注册新用户"""
    existing = db.query(models.User).filter(models.User.username == req.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = models.User(
        username=req.username,
        hashed_password=hash_password(req.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
def login(req: schemas.UserLogin, db: Session = Depends(get_db)):
    """用户登录，返回 JWT Token"""
    user = db.query(models.User).filter(models.User.username == req.username).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = create_access_token(data={"sub": str(user.id)})
    return {"access_token": token, "username": user.username}


@router.get("/me", response_model=schemas.UserInfo)
def get_me(user: models.User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return user
