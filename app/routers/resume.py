"""简历优化路由 - 文本优化、文件上传、历史记录"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.database import get_db
from app import models, schemas
from app.config import settings
from app.services.ai_service import (
    analyze_resume, list_providers,
    generate_cover_letter, generate_interview_prep,
    analyze_skills_gap, check_ats_format,
)
from app.services.file_parser import parse_file, ALLOWED_EXTENSIONS
from app.services.auth_service import get_current_user

router = APIRouter(tags=["简历优化"])


def _build_response(r: models.Resume) -> dict:
    """统一的响应格式，包含 V2 + Pro 新增字段"""
    return {
        "id": r.id,
        "analysis": r.analysis,
        "suggestions": json.loads(r.suggestions) if r.suggestions else [],
        "optimized_content": r.optimized_content,
        "created_at": r.created_at,
        "original_content": r.original_content,
        # V2 新增
        "ats_score": r.ats_score or 0,
        "job_matches": json.loads(r.job_matches) if r.job_matches else [],
        "skills_existing": json.loads(r.skills_existing) if r.skills_existing else [],
        "skills_missing": json.loads(r.skills_missing) if r.skills_missing else [],
        "project_suggestions": json.loads(r.project_suggestions) if r.project_suggestions else [],
        # Pro: JD 匹配
        "job_description": r.job_description,
        "jd_match_score": r.jd_match_score,
        "jd_match_analysis": r.jd_match_analysis,
    }


def _save_ai_result(user_id: int, content: str, ai_result: dict, db: Session,
                    job_description: str = None, batch_id: str = None) -> models.Resume:
    """将 AI 分析结果保存到数据库"""
    db_resume = models.Resume(
        user_id=user_id,
        original_content=content,
        analysis=ai_result.get("analysis", ""),
        suggestions=json.dumps(ai_result.get("suggestions", []), ensure_ascii=False),
        optimized_content=ai_result.get("optimized_resume", ""),
        # V2 新增
        ats_score=ai_result.get("ats_score", 0),
        job_matches=json.dumps(ai_result.get("job_matches", []), ensure_ascii=False),
        skills_existing=json.dumps(ai_result.get("skills_existing", []), ensure_ascii=False),
        skills_missing=json.dumps(ai_result.get("skills_missing", []), ensure_ascii=False),
        project_suggestions=json.dumps(ai_result.get("project_suggestions", []), ensure_ascii=False),
        # Pro
        job_description=job_description,
        jd_match_score=ai_result.get("jd_match_score"),
        jd_match_analysis=ai_result.get("jd_match_analysis"),
        batch_id=batch_id,
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)

    # 自动保存为 V1 版本
    from app.models import ResumeVersion
    v1 = ResumeVersion(
        resume_id=db_resume.id,
        version=1,
        content=content,
        ats_score=db_resume.ats_score or 0,
        jd_match_score=db_resume.jd_match_score,
        change_note="初始版本",
    )
    db.add(v1)
    db.commit()

    return db_resume


# ========== 简历优化 ==========

@router.get("/providers")
def get_providers(
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取可用的模型提供商列表（含用户自定义配置状态）"""
    return list_providers(user_id=user.id, db=db)


@router.post("/optimize", response_model=schemas.ResumeOptimizeResponse)
def optimize_resume(
        req: schemas.ResumeOptimizeRequest,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """粘贴文本 → AI 优化（支持 JD 匹配）"""
    content = req.content.encode('utf-8', errors='replace').decode('utf-8')
    jd = req.job_description

    try:
        ai_result = analyze_resume(content, provider=req.provider, user_id=user.id, db=db,
                                   job_description=jd)
    except Exception as e:
        error_msg = str(e)
        if 'ascii' in error_msg.lower() or 'encode' in error_msg.lower():
            raise HTTPException(status_code=502, detail=f"文本编码错误，请确保使用UTF-8编码: {error_msg}")
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {error_msg}")

    db_resume = _save_ai_result(user.id, content, ai_result, db, job_description=jd)
    return _build_response(db_resume)


@router.post("/upload", response_model=schemas.ResumeOptimizeResponse)
async def upload_resume(
        file: UploadFile = File(..., description="上传 PDF 或 Word 简历文件"),
        provider: Optional[str] = Query(None, description="模型提供商"),
        job_description: Optional[str] = Query(None, description="目标岗位 JD"),
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """上传文件 → AI 优化（支持 JD 匹配）"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件名")

    ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式 '{ext}'，仅支持: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    try:
        file_content = await file.read()
        resume_text = parse_file(file.filename, file_content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件解析失败: {str(e)}")

    # 确保文本是 UTF-8 编码的字符串
    if isinstance(resume_text, bytes):
        resume_text = resume_text.decode('utf-8', errors='replace')
    resume_text = resume_text.encode('utf-8', errors='replace').decode('utf-8')

    try:
        ai_result = analyze_resume(resume_text, provider=provider, user_id=user.id, db=db,
                                   job_description=job_description)
    except Exception as e:
        error_msg = str(e)
        if 'ascii' in error_msg.lower() or 'encode' in error_msg.lower():
            raise HTTPException(status_code=502, detail=f"文件内容编码错误，请确保文件使用UTF-8编码保存: {error_msg}")
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {error_msg}")

    db_resume = _save_ai_result(user.id, resume_text, ai_result, db, job_description=job_description)
    return _build_response(db_resume)


# ========== 历史记录 ==========

@router.get("/history", response_model=List[schemas.ResumeOptimizeResponse])
def get_history(
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取当前用户的优化历史"""
    resumes = db.query(models.Resume).filter(
        models.Resume.user_id == user.id
    ).order_by(models.Resume.created_at.desc()).all()
    return [_build_response(r) for r in resumes]


@router.get("/history/{resume_id}", response_model=schemas.ResumeOptimizeResponse)
def get_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取单条记录详情"""
    r = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    return _build_response(r)


@router.delete("/history/{resume_id}")
def delete_resume(
        resume_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """删除记录"""
    r = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(r)
    db.commit()
    return {"detail": "删除成功"}


# ========== Pro: 批量处理 ==========

import uuid
from fastapi import BackgroundTasks


def _batch_process(task_id: str, resumes: list, provider: str, user_id: int, job_description: str):
    """后台批量处理简历"""
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        for content in resumes:
            try:
                ai_result = analyze_resume(content, provider=provider, user_id=user_id, db=db,
                                           job_description=job_description)
                _save_ai_result(user_id, content, ai_result, db, job_description=job_description,
                                batch_id=task_id)
            except Exception:
                continue
    finally:
        db.close()


@router.post("/batch", response_model=schemas.BatchTaskResponse)
def batch_optimize(
        req: schemas.BatchOptimizeRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """批量优化多份简历（异步处理）"""
    task_id = str(uuid.uuid4())
    provider = req.provider or settings.DEFAULT_PROVIDER

    background_tasks.add_task(_batch_process, task_id, req.resumes, provider, user.id,
                              req.job_description or "")

    return schemas.BatchTaskResponse(
        task_id=task_id,
        status="processing",
        total=len(req.resumes),
        completed=0,
    )


@router.get("/batch/{task_id}", response_model=schemas.BatchTaskResponse)
def get_batch_status(
        task_id: str,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """查询批量任务状态"""
    resumes = db.query(models.Resume).filter(
        models.Resume.user_id == user.id,
        models.Resume.batch_id == task_id,
    ).all()

    return schemas.BatchTaskResponse(
        task_id=task_id,
        status="completed" if len(resumes) > 0 else "processing",
        total=len(resumes),
        completed=len(resumes),
        results=[r.id for r in resumes],
    )


# ========== Pro: 版本管理 ==========

@router.get("/history/{resume_id}/versions", response_model=List[schemas.ResumeVersionResponse])
def list_versions(
        resume_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取简历的所有版本"""
    r = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")

    versions = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.resume_id == resume_id,
    ).order_by(models.ResumeVersion.version.desc()).all()
    return versions


@router.post("/history/{resume_id}/versions", response_model=schemas.ResumeVersionResponse)
def create_version(
        resume_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """将当前优化结果保存为新版本"""
    r = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")

    last_version = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.resume_id == resume_id,
    ).order_by(models.ResumeVersion.version.desc()).first()

    new_ver = (last_version.version + 1) if last_version else 1

    v = models.ResumeVersion(
        resume_id=resume_id,
        version=new_ver,
        content=r.optimized_content or r.original_content,
        ats_score=r.ats_score or 0,
        jd_match_score=r.jd_match_score,
        change_note=f"版本 {new_ver}",
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.get("/history/{resume_id}/versions/compare", response_model=schemas.VersionCompareResponse)
def compare_versions(
        resume_id: int,
        v1: int = Query(..., description="版本A"),
        v2: int = Query(..., description="版本B"),
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """对比两个版本"""
    r = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")

    ver_a = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.resume_id == resume_id,
        models.ResumeVersion.version == v1,
    ).first()
    ver_b = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.resume_id == resume_id,
        models.ResumeVersion.version == v2,
    ).first()

    if not ver_a or not ver_b:
        raise HTTPException(status_code=404, detail="版本不存在")

    return schemas.VersionCompareResponse(
        version_a=ver_a,
        version_b=ver_b,
        ats_diff=(ver_b.ats_score or 0) - (ver_a.ats_score or 0),
        jd_match_diff=(ver_b.jd_match_score or 0) - (ver_a.jd_match_score or 0) if ver_b.jd_match_score else None,
    )


@router.post("/history/{resume_id}/versions/{version}/rollback")
def rollback_version(
        resume_id: int,
        version: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """回滚到指定版本"""
    r = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="记录不存在")

    v = db.query(models.ResumeVersion).filter(
        models.ResumeVersion.resume_id == resume_id,
        models.ResumeVersion.version == version,
    ).first()
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")

    r.optimized_content = v.content
    r.ats_score = v.ats_score
    r.jd_match_score = v.jd_match_score
    db.commit()
    return {"detail": f"已回滚到版本 {version}"}


# ========== Pro: 用量统计 ==========

from datetime import date, timedelta


@router.get("/usage", response_model=schemas.UsageStatsResponse)
def get_usage_stats(
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取当前用户的 API 用量统计"""
    from app.models import UsageLog, RateLimit

    logs = db.query(UsageLog).filter(UsageLog.user_id == user.id).all()

    total_tokens = sum(l.tokens_prompt + l.tokens_completion for l in logs)
    total_cost = sum(l.cost_usd for l in logs)

    by_provider = {}
    by_date = {}
    for l in logs:
        by_provider[l.provider] = by_provider.get(l.provider, 0) + 1
        d = l.created_at.strftime("%Y-%m-%d")
        by_date[d] = by_date.get(d, 0) + 1

    today = date.today().isoformat()
    rl = db.query(RateLimit).filter(
        RateLimit.user_id == user.id,
        RateLimit.date == today,
    ).first()
    daily_limit = 100
    remaining = daily_limit - (rl.count if rl else 0)

    return schemas.UsageStatsResponse(
        total_optimizations=len(logs),
        total_tokens_used=total_tokens,
        total_cost_usd=total_cost / 1_000_000,
        by_provider=by_provider,
        by_date=by_date,
        rate_limit_remaining=max(0, remaining),
    )


# ========== Pro: 团队协作 ==========

@router.post("/teams", response_model=schemas.TeamResponse)
def create_team(
        req: schemas.TeamCreate,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """创建团队"""
    team = models.Team(name=req.name, owner_id=user.id)
    db.add(team)
    db.flush()

    member = models.TeamMember(team_id=team.id, user_id=user.id, role="owner")
    db.add(member)
    db.commit()
    db.refresh(team)
    return team


@router.get("/teams", response_model=List[schemas.TeamResponse])
def list_teams(
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取用户所属的团队"""
    memberships = db.query(models.TeamMember).filter(
        models.TeamMember.user_id == user.id,
    ).all()
    team_ids = [m.team_id for m in memberships]
    teams = db.query(models.Team).filter(models.Team.id.in_(team_ids)).all()
    return teams


@router.post("/teams/{team_id}/invite", response_model=schemas.TeamMemberResponse)
def invite_member(
        team_id: int,
        req: schemas.TeamInviteRequest,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """邀请成员加入团队"""
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    # 检查权限
    membership = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id,
        models.TeamMember.user_id == user.id,
        models.TeamMember.role.in_(["owner", "admin"]),
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="无权邀请成员")

    target_user = db.query(models.User).filter(models.User.username == req.username).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    existing = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id,
        models.TeamMember.user_id == target_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该用户已在团队中")

    member = models.TeamMember(team_id=team_id, user_id=target_user.id, role=req.role)
    db.add(member)
    db.commit()
    db.refresh(member)

    return schemas.TeamMemberResponse(
        id=member.id,
        team_id=member.team_id,
        user_id=member.user_id,
        username=req.username,
        role=member.role,
        created_at=member.created_at,
    )


@router.get("/teams/{team_id}/members", response_model=List[schemas.TeamMemberResponse])
def list_members(
        team_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取团队成员列表"""
    members = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id,
    ).all()

    result = []
    for m in members:
        u = db.query(models.User).filter(models.User.id == m.user_id).first()
        result.append(schemas.TeamMemberResponse(
            id=m.id,
            team_id=m.team_id,
            user_id=m.user_id,
            username=u.username if u else "unknown",
            role=m.role,
            created_at=m.created_at,
        ))
    return result


@router.post("/teams/{team_id}/resumes/{resume_id}/comment", response_model=schemas.TeamCommentResponse)
def add_comment(
        team_id: int,
        resume_id: int,
        req: schemas.TeamCommentCreate,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """对团队中的简历添加评论"""
    comment = models.TeamComment(
        resume_id=resume_id,
        user_id=user.id,
        content=req.content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return schemas.TeamCommentResponse(
        id=comment.id,
        resume_id=comment.resume_id,
        user_id=comment.user_id,
        username=user.username,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.get("/teams/{team_id}/resumes/{resume_id}/comments", response_model=List[schemas.TeamCommentResponse])
def list_comments(
        team_id: int,
        resume_id: int,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """获取简历的评论列表"""
    comments = db.query(models.TeamComment).filter(
        models.TeamComment.resume_id == resume_id,
    ).order_by(models.TeamComment.created_at.desc()).all()

    result = []
    for c in comments:
        u = db.query(models.User).filter(models.User.id == c.user_id).first()
        result.append(schemas.TeamCommentResponse(
            id=c.id,
            resume_id=c.resume_id,
            user_id=c.user_id,
            username=u.username if u else "unknown",
            content=c.content,
            created_at=c.created_at,
        ))
    return result


@router.post("/teams/{team_id}/resumes/{resume_id}/approve")
def approve_resume(
        team_id: int,
        resume_id: int,
        req: schemas.TeamApprovalRequest,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """审批简历"""
    membership = db.query(models.TeamMember).filter(
        models.TeamMember.team_id == team_id,
        models.TeamMember.user_id == user.id,
        models.TeamMember.role.in_(["owner", "admin"]),
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="无权审批")

    tr = db.query(models.TeamResume).filter(
        models.TeamResume.team_id == team_id,
        models.TeamResume.resume_id == resume_id,
    ).first()
    if not tr:
        raise HTTPException(status_code=404, detail="未找到该简历")

    tr.approval_status = "approved" if req.action == "approve" else "rejected"
    db.commit()
    return {"detail": f"已{req.action}"}


# ========== 实用功能: 求职信生成 ==========

@router.post("/cover-letter", response_model=schemas.CoverLetterResponse)
def create_cover_letter(
        req: schemas.CoverLetterRequest,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """基于简历+JD生成求职信"""
    r = db.query(models.Resume).filter(
        models.Resume.id == req.resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="简历记录不存在")

    try:
        ai_result = generate_cover_letter(
            r.optimized_content or r.original_content,
            job_description=req.job_description or r.job_description,
            company_name=req.company_name,
            tone=req.tone,
            user_id=user.id, db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)}")

    feature = models.ResumeFeature(
        resume_id=req.resume_id,
        feature_type="cover_letter",
        result=json.dumps(ai_result, ensure_ascii=False),
    )
    db.add(feature)
    db.commit()
    db.refresh(feature)

    return schemas.CoverLetterResponse(
        id=feature.id,
        resume_id=feature.resume_id,
        cover_letter=ai_result.get("cover_letter", ""),
        created_at=feature.created_at,
    )


# ========== 实用功能: 面试准备 ==========

@router.post("/interview-prep", response_model=schemas.InterviewPrepResponse)
def create_interview_prep(
        req: schemas.InterviewPrepRequest,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """基于简历+JD生成面试问题和参考答案"""
    r = db.query(models.Resume).filter(
        models.Resume.id == req.resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="简历记录不存在")

    try:
        ai_result = generate_interview_prep(
            r.optimized_content or r.original_content,
            job_description=req.job_description or r.job_description,
            question_count=req.question_count,
            user_id=user.id, db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)}")

    feature = models.ResumeFeature(
        resume_id=req.resume_id,
        feature_type="interview_prep",
        result=json.dumps(ai_result, ensure_ascii=False),
    )
    db.add(feature)
    db.commit()
    db.refresh(feature)

    questions = [schemas.InterviewQuestion(**q) for q in ai_result.get("questions", [])]
    return schemas.InterviewPrepResponse(
        id=feature.id,
        resume_id=feature.resume_id,
        questions=questions,
        created_at=feature.created_at,
    )


# ========== 实用功能: 技能差距分析 ==========

@router.post("/skills-gap", response_model=schemas.SkillsGapResponse)
def create_skills_gap(
        req: schemas.SkillsGapRequest,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """基于简历+JD分析技能差距"""
    r = db.query(models.Resume).filter(
        models.Resume.id == req.resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="简历记录不存在")

    try:
        ai_result = analyze_skills_gap(
            r.optimized_content or r.original_content,
            job_description=req.job_description,
            user_id=user.id, db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)}")

    feature = models.ResumeFeature(
        resume_id=req.resume_id,
        feature_type="skills_gap",
        result=json.dumps(ai_result, ensure_ascii=False),
    )
    db.add(feature)
    db.commit()
    db.refresh(feature)

    gap_items = [schemas.SkillsGapItem(**item) for item in ai_result.get("gap_items", [])]
    return schemas.SkillsGapResponse(
        id=feature.id,
        resume_id=feature.resume_id,
        match_percentage=ai_result.get("match_percentage", 0),
        gap_items=gap_items,
        summary=ai_result.get("summary", ""),
        created_at=feature.created_at,
    )


# ========== 实用功能: ATS 格式检查 ==========

@router.post("/ats-check", response_model=schemas.AtsCheckResponse)
def create_ats_check(
        req: schemas.AtsCheckRequest,
        db: Session = Depends(get_db),
        user: models.User = Depends(get_current_user),
):
    """检查简历的ATS兼容性"""
    r = db.query(models.Resume).filter(
        models.Resume.id == req.resume_id,
        models.Resume.user_id == user.id,
    ).first()
    if not r:
        raise HTTPException(status_code=404, detail="简历记录不存在")

    try:
        ai_result = check_ats_format(
            r.optimized_content or r.original_content,
            user_id=user.id, db=db,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI服务调用失败: {str(e)}")

    feature = models.ResumeFeature(
        resume_id=req.resume_id,
        feature_type="ats_check",
        result=json.dumps(ai_result, ensure_ascii=False),
    )
    db.add(feature)
    db.commit()
    db.refresh(feature)

    dimensions = [schemas.AtsCheckDimension(**d) for d in ai_result.get("dimensions", [])]
    return schemas.AtsCheckResponse(
        id=feature.id,
        resume_id=feature.resume_id,
        total_score=ai_result.get("total_score", 0),
        dimensions=dimensions,
        summary=ai_result.get("summary", ""),
        created_at=feature.created_at,
    )
