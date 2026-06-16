from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    hashed_password = Column(String(128), nullable=False, comment="密码哈希")
    is_admin = Column(Integer, default=0, comment="是否管理员 1=是 0=否")
    is_active = Column(Integer, default=1, comment="是否启用 1=是 0=否")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    resumes = relationship("Resume", back_populates="owner", cascade="all, delete-orphan")
    api_keys = relationship("UserApiKey", back_populates="owner", cascade="all, delete-orphan")


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(20), nullable=False, comment="提供商: deepseek/qwen/kimi/mimo")
    api_key = Column(String(200), nullable=False, comment="API Key")
    base_url = Column(String(200), nullable=True, comment="自定义 Base URL")
    model = Column(String(50), nullable=True, comment="自定义模型名称")
    is_active = Column(Integer, default=1, comment="是否启用 1=是 0=否")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="api_keys")

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_provider"),
    )


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="所属用户")
    original_content = Column(Text, nullable=False, comment="原始简历")
    analysis = Column(Text, comment="AI问题分析")
    suggestions = Column(Text, comment="优化建议JSON")
    optimized_content = Column(Text, comment="优化后的简历")

    # V2 新增字段
    ats_score = Column(Integer, default=0, comment="ATS评分 0-100")
    job_matches = Column(Text, comment="岗位匹配JSON [{title, score}]")
    skills_existing = Column(Text, comment="已有技能JSON [str]")
    skills_missing = Column(Text, comment="缺失技能JSON [str]")
    project_suggestions = Column(Text, comment="项目优化建议JSON [str]")

    # Pro: JD 匹配
    job_description = Column(Text, nullable=True, comment="目标岗位JD")
    jd_match_score = Column(Integer, nullable=True, comment="JD匹配度 0-100")
    jd_match_analysis = Column(Text, nullable=True, comment="JD匹配分析")

    # Pro: 批量处理
    batch_id = Column(String(36), nullable=True, comment="批量任务ID")

    created_at = Column(DateTime, nullable=False, server_default=func.now())

    owner = relationship("User", back_populates="resumes")
    versions = relationship("ResumeVersion", back_populates="resume", cascade="all, delete-orphan")
    comments = relationship("TeamComment", back_populates="resume", cascade="all, delete-orphan")


# ========== Pro: 版本管理 ==========

class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    version = Column(Integer, nullable=False, comment="版本号")
    content = Column(Text, nullable=False, comment="简历内容")
    ats_score = Column(Integer, default=0)
    jd_match_score = Column(Integer, nullable=True)
    change_note = Column(String(200), nullable=True, comment="变更说明")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    resume = relationship("Resume", back_populates="versions")


# ========== Pro: 团队协作 ==========

class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    resumes = relationship("TeamResume", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    role = Column(String(20), nullable=False, default="member", comment="owner/admin/member")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    team = relationship("Team", back_populates="members")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_user"),
    )


class TeamResume(Base):
    __tablename__ = "team_resumes"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    approval_status = Column(String(20), default="pending", comment="pending/approved/rejected")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    team = relationship("Team", back_populates="resumes")
    resume = relationship("Resume")
    added_by_user = relationship("User")


class TeamComment(Base):
    __tablename__ = "team_comments"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    resume = relationship("Resume", back_populates="comments")
    user = relationship("User")


# ========== Pro: 用量统计 ==========

class UsageLog(Base):
    __tablename__ = "usage_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(20), nullable=False)
    model = Column(String(50), nullable=False)
    tokens_prompt = Column(Integer, default=0)
    tokens_completion = Column(Integer, default=0)
    cost_usd = Column(Integer, default=0, comment="费用，单位: 微美元")
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User")


# ========== 实用功能 ==========

class ResumeFeature(Base):
    __tablename__ = "resume_features"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    feature_type = Column(String(30), nullable=False, comment="cover_letter/interview_prep/skills_gap/ats_check")
    result = Column(Text, nullable=False, comment="功能结果JSON")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    resume = relationship("Resume")


# ========== Pro: 限流 ==========

class RateLimit(Base):
    __tablename__ = "rate_limits"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String(10), nullable=False, comment="日期 YYYY-MM-DD")
    count = Column(Integer, default=0, comment="当日调用次数")
    tokens = Column(Integer, default=0, comment="当日 token 消耗")

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
    )
