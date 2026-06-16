from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


# ========== 简历相关 ==========

class JobMatch(BaseModel):
    title: str
    score: int


class ResumeOptimizeRequest(BaseModel):
    content: str
    provider: Optional[str] = Field(None, description="模型提供商: deepseek/qwen/kimi/mimo")
    job_description: Optional[str] = Field(None, description="目标岗位的职位描述 JD，用于精准匹配优化")

    class Config:
        json_schema_extra = {
            "example": {
                "content": "张三\n电话：138xxxx\n经验：3年Java开发...",
                "provider": "deepseek",
                "job_description": "岗位职责：负责后端系统开发..."
            }
        }


class ResumeOptimizeResponse(BaseModel):
    id: int
    analysis: str
    suggestions: List[str]
    optimized_content: str
    created_at: datetime
    original_content: Optional[str] = None

    # V2 新增
    ats_score: int = 0
    job_matches: List[JobMatch] = []
    skills_existing: List[str] = []
    skills_missing: List[str] = []
    project_suggestions: List[str] = []

    # Pro: JD 匹配
    job_description: Optional[str] = None
    jd_match_score: Optional[int] = None
    jd_match_analysis: Optional[str] = None

    class Config:
        from_attributes = True


# ========== 用户认证相关 ==========

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, description="用户名（3-50个字符）")
    password: str = Field(..., min_length=6, max_length=100, description="密码（至少6个字符）")


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class UserInfo(BaseModel):
    id: int
    username: str
    is_admin: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


# ========== Pro: 批量处理 ==========

class BatchOptimizeRequest(BaseModel):
    resumes: List[str] = Field(..., min_length=1, max_length=10, description="简历文本列表，最多10份")
    provider: Optional[str] = Field(None, description="模型提供商")
    job_description: Optional[str] = Field(None, description="目标岗位 JD")


class BatchTaskResponse(BaseModel):
    task_id: str
    status: str
    total: int
    completed: int
    results: List[Optional[int]] = Field(default_factory=list, description="已完成的简历ID列表")


# ========== Pro: 版本管理 ==========

class ResumeVersionResponse(BaseModel):
    id: int
    resume_id: int
    version: int
    content: str
    ats_score: int = 0
    jd_match_score: Optional[int] = None
    change_note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class VersionCompareResponse(BaseModel):
    version_a: ResumeVersionResponse
    version_b: ResumeVersionResponse
    ats_diff: int
    jd_match_diff: Optional[int] = None


# ========== Pro: 团队协作 ==========

class TeamCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class TeamResponse(BaseModel):
    id: int
    name: str
    owner_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TeamMemberResponse(BaseModel):
    id: int
    team_id: int
    user_id: int
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class TeamInviteRequest(BaseModel):
    username: str
    role: str = Field("member", description="角色: member/admin")


class TeamCommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class TeamCommentResponse(BaseModel):
    id: int
    resume_id: int
    user_id: int
    username: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class TeamApprovalRequest(BaseModel):
    action: str = Field(..., description="approve/reject")
    comment: Optional[str] = None


# ========== Pro: 用量统计 ==========

class UsageStatsResponse(BaseModel):
    total_optimizations: int
    total_tokens_used: int
    total_cost_usd: float
    by_provider: dict
    by_date: dict
    rate_limit_remaining: int


# ========== Pro: PDF/Word 导出 ==========

class ExportRequest(BaseModel):
    resume_id: int
    format: str = Field("pdf", description="导出格式: pdf/docx")


# ========== API Key 管理 ==========

class ApiKeyCreate(BaseModel):
    provider: str = Field(..., description="提供商: deepseek/qwen/kimi/mimo")
    api_key: str = Field(..., min_length=1, description="API Key")
    base_url: Optional[str] = Field(None, description="自定义 Base URL")
    model: Optional[str] = Field(None, description="自定义模型名称")


class ApiKeyUpdate(BaseModel):
    api_key: Optional[str] = Field(None, description="API Key")
    base_url: Optional[str] = Field(None, description="自定义 Base URL")
    model: Optional[str] = Field(None, description="自定义模型名称")
    is_active: Optional[int] = Field(None, description="是否启用 1=是 0=否")


class ApiKeyResponse(BaseModel):
    id: int
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None
    is_active: int
    created_at: datetime

    class Config:
        from_attributes = True


# ========== 实用功能 ==========

class CoverLetterRequest(BaseModel):
    resume_id: int
    job_description: Optional[str] = Field(None, description="目标岗位JD")
    company_name: Optional[str] = Field(None, description="公司名称")
    tone: Optional[str] = Field("professional", description="语气: professional/casual/enthusiastic")


class CoverLetterResponse(BaseModel):
    id: int
    resume_id: int
    cover_letter: str
    created_at: datetime

    class Config:
        from_attributes = True


class InterviewPrepRequest(BaseModel):
    resume_id: int
    job_description: Optional[str] = Field(None, description="目标岗位JD")
    question_count: Optional[int] = Field(10, ge=3, le=20, description="问题数量")


class InterviewQuestion(BaseModel):
    question: str
    category: str
    difficulty: str
    suggested_answer: str
    tips: str


class InterviewPrepResponse(BaseModel):
    id: int
    resume_id: int
    questions: List[InterviewQuestion]
    created_at: datetime

    class Config:
        from_attributes = True


class SkillsGapRequest(BaseModel):
    resume_id: int
    job_description: str = Field(..., description="目标岗位JD（必填）")


class SkillsGapItem(BaseModel):
    skill: str
    importance: str
    category: str
    suggestion: str
    has_in_resume: bool


class SkillsGapResponse(BaseModel):
    id: int
    resume_id: int
    match_percentage: int
    gap_items: List[SkillsGapItem]
    summary: str
    created_at: datetime

    class Config:
        from_attributes = True


class AtsCheckRequest(BaseModel):
    resume_id: int
    job_description: Optional[str] = Field(None, description="目标岗位JD")


class AtsCheckDimension(BaseModel):
    name: str
    score: int
    issues: List[str]
    suggestions: List[str]


class AtsCheckResponse(BaseModel):
    id: int
    resume_id: int
    total_score: int
    dimensions: List[AtsCheckDimension]
    summary: str
    created_at: datetime

    class Config:
        from_attributes = True
