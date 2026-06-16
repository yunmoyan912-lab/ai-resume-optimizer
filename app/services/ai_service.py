"""AI 简历分析服务 - 多模型支持 + 用户自定义 Key"""
from openai import OpenAI
from app.config import settings
import json
from pathlib import Path
from typing import Optional

# ========== 模型提供商注册表 ==========

PROVIDERS = {
    "deepseek": {
        "name": "DeepSeek",
        "env_key": "DEEPSEEK_API_KEY",
        "env_url": "DEEPSEEK_BASE_URL",
        "env_model": "DEEPSEEK_MODEL",
    },
    "qwen": {
        "name": "通义千问",
        "env_key": "QWEN_API_KEY",
        "env_url": "QWEN_BASE_URL",
        "env_model": "QWEN_MODEL",
    },
    "kimi": {
        "name": "Kimi",
        "env_key": "KIMI_API_KEY",
        "env_url": "KIMI_BASE_URL",
        "env_model": "KIMI_MODEL",
    },
    "mimo": {
        "name": "MiMo",
        "env_key": "MIMO_API_KEY",
        "env_url": "MIMO_BASE_URL",
        "env_model": "MIMO_MODEL",
    },
}

# ========== secrets.json 加载 ==========

_secrets = {}
secrets_file = Path(__file__).parent.parent.parent / "secrets.json"
if secrets_file.exists():
    for encoding in ['utf-8-sig', 'utf-8', 'utf-16', 'gbk']:
        try:
            raw = secrets_file.read_text(encoding=encoding)
            _secrets = json.loads(raw)
            break
        except (UnicodeDecodeError, UnicodeError, json.JSONDecodeError):
            continue


def _get_system_config(provider: str) -> dict:
    """获取系统级（secrets.json / .env）的提供商配置"""
    if provider not in PROVIDERS:
        provider = settings.DEFAULT_PROVIDER
    if provider not in PROVIDERS:
        provider = "deepseek"

    p = PROVIDERS[provider]
    api_key = _secrets.get(p["env_key"]) or getattr(settings, p["env_key"], "")
    base_url = _secrets.get(p["env_url"].lower()) or getattr(settings, p["env_url"], "")
    model = _secrets.get(p["env_model"].lower()) or getattr(settings, p["env_model"], "")

    return {"api_key": api_key, "base_url": base_url, "model": model, "name": p["name"]}


def _get_user_config(provider: str, user_id: Optional[int], db=None) -> Optional[dict]:
    """从数据库获取用户自定义的提供商配置，优先级最高"""
    if not user_id or not db:
        return None

    from app.models import UserApiKey
    key = db.query(UserApiKey).filter(
        UserApiKey.user_id == user_id,
        UserApiKey.provider == provider,
        UserApiKey.is_active == 1,
    ).first()

    if not key:
        return None

    p = PROVIDERS.get(provider, {})
    return {
        "api_key": key.api_key,
        "base_url": key.base_url or _get_system_config(provider)["base_url"],
        "model": key.model or _get_system_config(provider)["model"],
        "name": p.get("name", provider),
        "is_custom": True,
    }


def _get_provider_config(provider: str, user_id: Optional[int] = None, db=None) -> dict:
    """获取提供商配置：用户自定义 > 系统配置"""
    user_cfg = _get_user_config(provider, user_id, db)
    if user_cfg:
        return user_cfg
    return _get_system_config(provider)


# ========== 客户端缓存 ==========

_clients: dict[str, OpenAI] = {}


def _get_client(provider: str, user_id: Optional[int] = None, db=None) -> tuple[OpenAI, str]:
    """获取或创建指定提供商的客户端，返回 (client, model)"""
    cfg = _get_provider_config(provider, user_id, db)
    if not cfg["api_key"]:
        raise Exception(f"未配置 {cfg['name']} 的 API Key，请在设置页面配置或联系管理员")

    # 缓存 key 包含 user_id，避免不同用户的 key 冲突
    cache_key = f"{user_id or 0}:{provider}:{cfg['api_key'][:8]}"
    if cache_key not in _clients:
        _clients[cache_key] = OpenAI(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
        )
    return _clients[cache_key], cfg["model"]


def list_providers(user_id: Optional[int] = None, db=None) -> list[dict]:
    """返回可用的模型提供商列表，标记用户是否已配置"""
    result = []
    for key, p in PROVIDERS.items():
        sys_cfg = _get_system_config(key)
        user_cfg = _get_user_config(key, user_id, db) if user_id and db else None

        available = bool(user_cfg["api_key"] if user_cfg else sys_cfg["api_key"])
        model = user_cfg["model"] if user_cfg else sys_cfg["model"]
        is_custom = bool(user_cfg and user_cfg.get("is_custom"))

        result.append({
            "id": key,
            "name": p["name"],
            "model": model,
            "available": available,
            "is_custom": is_custom,
        })
    return result


# ========== Prompt ==========

SYSTEM_PROMPT = """你是一位拥有15年经验的资深HR总监和简历优化专家，同时精通ATS（简历筛选系统）的评分机制。
请对用户提供的简历进行深度分析，并严格按以下JSON格式返回（不要包含markdown代码块标记）：
{
    "analysis": "对简历现存问题的整体分析，200字以内，要尖锐但建设性",
    "suggestions": [
        "具体可落地的优化建议1",
        "具体可落地的优化建议2",
        "具体可落地的优化建议3"
    ],
    "optimized_resume": "重写后的完整简历，可直接投递，不添加解释性文字",
    "ats_score": 85,
    "job_matches": [
        {"title": "岗位名称", "score": 90},
        {"title": "岗位名称", "score": 85},
        {"title": "岗位名称", "score": 80},
        {"title": "岗位名称", "score": 70}
    ],
    "skills_existing": ["Python", "SQL", "FastAPI", "Docker"],
    "skills_missing": ["Redis", "Kubernetes", "CI/CD"],
    "project_suggestions": [
        "项目经历优化建议1",
        "项目经历优化建议2"
    ]
}

评分规则：
1. ats_score: 0-100 整数。考虑关键词匹配度、格式规范度、内容完整度、量化成果
   - 90+ 优秀（可直接投递大厂）
   - 80+ 良好（稍加优化即可）
   - 70+ 合格（需要较多优化）
   - 70以下 需大幅优化
2. job_matches: 根据简历内容推测4个最匹配岗位，每个给出匹配度百分比(整数)
3. skills_existing: 从简历中提取出的已有技术技能关键词（5-10个）
4. skills_missing: 根据匹配岗位分析，该简历缺少但应该补充的技能（3-6个）
5. project_suggestions: 针对项目经历的具体优化建议（2-3条）
6. suggestions: 3-5条可落地的整体修改建议
7. optimized_resume: 必须是一篇专业简历，不添加任何解释性文字
"""

JD_PROMPT_SUFFIX = """

【重要】用户提供了目标岗位的职位描述(JD)，请额外完成以下任务：
1. 逐条对比简历与JD的要求，找出匹配点和差距
2. 重点优化简历中与JD相关的部分，突出匹配的技能和经验
3. 在 JSON 中额外返回以下字段：
   - "jd_match_score": 0-100整数，简历与该JD的匹配度评分
   - "jd_match_analysis": 200字以内的匹配分析，说明匹配点和改进方向
4. optimized_resume 必须针对该JD量身定制，突出JD要求的技能和经验
"""


# ========== 核心分析函数 ==========

def analyze_resume(resume_text: str, provider: Optional[str] = None,
                   user_id: Optional[int] = None, db=None,
                   job_description: Optional[str] = None) -> dict:
    """调用 AI 分析简历
    Args:
        resume_text: 简历文本内容
        provider: 模型提供商 (deepseek/qwen/kimi/mimo)，None 使用默认
        user_id: 当前用户 ID，用于查询自定义 API Key
        db: 数据库会话
        job_description: 目标岗位 JD，用于精准匹配优化
    """
    if isinstance(resume_text, bytes):
        resume_text = resume_text.decode('utf-8', errors='replace')
    resume_text = resume_text.encode('utf-8', errors='replace').decode('utf-8')

    use_provider = provider or settings.DEFAULT_PROVIDER
    client, model = _get_client(use_provider, user_id, db)

    user_msg = f"请分析并优化以下简历：\n\n{resume_text}"
    if job_description:
        user_msg += f"\n\n以下是目标岗位的职位描述(JD)，请针对该岗位进行精准优化：\n\n{job_description}"

    system_msg = SYSTEM_PROMPT
    if job_description:
        system_msg += JD_PROMPT_SUFFIX

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            temperature=0.7,
            max_tokens=6000,
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        result = json.loads(content)

        # 记录用量
        if db and user_id:
            _log_usage(user_id, use_provider, model, response, db)

        return result
    except json.JSONDecodeError as e:
        raise Exception(f"AI 返回的 JSON 格式错误: {str(e)}")
    except Exception as e:
        if 'ascii' in str(e).lower() or 'encode' in str(e).lower():
            raise Exception(f"文本编码错误，请确保简历内容使用 UTF-8 编码: {str(e)}")
        raise


def _log_usage(user_id: int, provider: str, model: str, response, db):
    """记录 API 调用用量"""
    from app.models import UsageLog, RateLimit
    from datetime import date

    usage = response.usage
    if not usage:
        return

    prompt_tokens = usage.prompt_tokens or 0
    completion_tokens = usage.completion_tokens or 0
    total_tokens = prompt_tokens + completion_tokens

    # 简单估算费用（微美元），实际应根据各提供商价格表
    cost = total_tokens * 2  # 粗略估算

    log = UsageLog(
        user_id=user_id,
        provider=provider,
        model=model,
        tokens_prompt=prompt_tokens,
        tokens_completion=completion_tokens,
        cost_usd=cost,
    )
    db.add(log)

    # 更新每日限流计数
    today = date.today().isoformat()
    rl = db.query(RateLimit).filter(
        RateLimit.user_id == user_id,
        RateLimit.date == today,
    ).first()
    if rl:
        rl.count += 1
        rl.tokens += total_tokens
    else:
        rl = RateLimit(user_id=user_id, date=today, count=1, tokens=total_tokens)
        db.add(rl)

    db.commit()


# ========== 求职信生成 ==========

COVER_LETTER_PROMPT = """你是一位专业的求职信撰写专家。请根据用户的简历和目标岗位信息，生成一封专业、有说服力的求职信。
要求：
1. 结构清晰：开头自我介绍 → 表达兴趣 → 匹配能力 → 结尾期望
2. 突出与JD匹配的技能和经验
3. 语气{tone}，控制在300-500字
4. 用中文撰写
5. 直接输出求职信内容，不要包含标题或额外说明

严格按以下JSON格式返回（不要包含markdown代码块标记）：
{{
    "cover_letter": "求职信正文内容"
}}"""


def generate_cover_letter(resume_text: str, job_description: str = None,
                          company_name: str = None, tone: str = "professional",
                          provider: str = None, user_id: int = None, db=None) -> dict:
    """生成求职信"""
    use_provider = provider or settings.DEFAULT_PROVIDER
    client, model = _get_client(use_provider, user_id, db)

    tone_map = {"professional": "专业正式", "casual": "轻松自然", "enthusiastic": "热情积极"}
    tone_text = tone_map.get(tone, "专业正式")

    system_msg = COVER_LETTER_PROMPT.format(tone=tone_text)
    user_msg = f"以下是我的简历：\n\n{resume_text}"
    if job_description:
        user_msg += f"\n\n以下是目标岗位的职位描述(JD)：\n\n{job_description}"
    if company_name:
        user_msg += f"\n\n目标公司：{company_name}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=2000,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    if db and user_id:
        _log_usage(user_id, use_provider, model, response, db)

    return result


# ========== 面试准备 ==========

INTERVIEW_PREP_PROMPT = """你是一位资深面试官和职业顾问。请根据用户的简历和目标岗位JD，生成{count}个面试问题及参考答案。
要求：
1. 问题涵盖不同类别：技术能力、项目经验、行为面试、情景模拟、职业规划
2. 每个问题标注难度：easy/medium/hard
3. 参考答案要结合简历中的具体经历
4. 给出实用的答题技巧
5. 用中文

严格按以下JSON格式返回（不要包含markdown代码块标记）：
{{
    "questions": [
        {{
            "question": "面试问题",
            "category": "类别（技术能力/项目经验/行为面试/情景模拟/职业规划）",
            "difficulty": "easy/medium/hard",
            "suggested_answer": "参考答案（结合简历经历）",
            "tips": "答题技巧"
        }}
    ]
}}"""


def generate_interview_prep(resume_text: str, job_description: str = None,
                            question_count: int = 10, provider: str = None,
                            user_id: int = None, db=None) -> dict:
    """生成面试准备问题"""
    use_provider = provider or settings.DEFAULT_PROVIDER
    client, model = _get_client(use_provider, user_id, db)

    system_msg = INTERVIEW_PREP_PROMPT.format(count=question_count)
    user_msg = f"以下是我的简历：\n\n{resume_text}"
    if job_description:
        user_msg += f"\n\n以下是目标岗位的职位描述(JD)：\n\n{job_description}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=4000,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    if db and user_id:
        _log_usage(user_id, use_provider, model, response, db)

    return result


# ========== 技能差距分析 ==========

SKILLS_GAP_PROMPT = """你是一位职业发展顾问和技能分析师。请根据用户的简历和目标岗位JD，进行详细的技能差距分析。
要求：
1. 逐条分析JD要求的技能，判断用户是否已具备
2. 评估每项技能的重要程度：critical/important/nice-to-have
3. 为缺失的技能提供具体的学习建议
4. 给出整体匹配度百分比
5. 用中文

严格按以下JSON格式返回（不要包含markdown代码块标记）：
{{
    "match_percentage": 75,
    "gap_items": [
        {{
            "skill": "技能名称",
            "importance": "critical/important/nice-to-have",
            "category": "类别（技术技能/软技能/工具/认证）",
            "suggestion": "具体学习建议",
            "has_in_resume": true/false
        }}
    ],
    "summary": "整体分析总结，200字以内"
}}"""


def analyze_skills_gap(resume_text: str, job_description: str,
                       provider: str = None, user_id: int = None, db=None) -> dict:
    """分析技能差距"""
    use_provider = provider or settings.DEFAULT_PROVIDER
    client, model = _get_client(use_provider, user_id, db)

    user_msg = f"以下是我的简历：\n\n{resume_text}\n\n以下是目标岗位的职位描述(JD)：\n\n{job_description}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SKILLS_GAP_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=3000,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    if db and user_id:
        _log_usage(user_id, use_provider, model, response, db)

    return result


# ========== ATS 格式检查 ==========

ATS_CHECK_PROMPT = """你是一位ATS（简历筛选系统）技术专家。请对用户的简历进行ATS兼容性检查。
检查以下维度（每个维度0-100分）：
1. 格式规范：是否使用标准字体、无表格/图片/特殊字符、纯文本友好
2. 关键词匹配：是否包含行业关键词、技能关键词密度是否合适
3. 结构清晰：是否有清晰的段落划分、标题层级是否合理
4. 量化成果：是否有数据支撑的工作成果（百分比、数字等）
5. 联系信息：是否包含完整的联系方式

严格按以下JSON格式返回（不要包含markdown代码块标记）：
{{
    "total_score": 80,
    "dimensions": [
        {{
            "name": "维度名称",
            "score": 85,
            "issues": ["问题1", "问题2"],
            "suggestions": ["建议1", "建议2"]
        }}
    ],
    "summary": "整体评估总结，150字以内"
}}"""


def check_ats_format(resume_text: str, provider: str = None,
                     user_id: int = None, db=None) -> dict:
    """ATS格式检查"""
    use_provider = provider or settings.DEFAULT_PROVIDER
    client, model = _get_client(use_provider, user_id, db)

    user_msg = f"请对以下简历进行ATS兼容性检查：\n\n{resume_text}"

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": ATS_CHECK_PROMPT},
            {"role": "user", "content": user_msg}
        ],
        temperature=0.7,
        max_tokens=3000,
        response_format={"type": "json_object"}
    )

    content = response.choices[0].message.content
    result = json.loads(content)

    if db and user_id:
        _log_usage(user_id, use_provider, model, response, db)

    return result
