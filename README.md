# AI 简历优化器

基于 FastAPI + 多模型 AI 的一站式简历分析与优化平台。支持 ATS 评分、岗位 JD 匹配、求职信生成、面试准备、技能差距分析、ATS 格式检查、批量处理、版本管理、团队协作、PDF/Word 导出等功能。

## 功能概览

```
┌─────────────────────────────────────────────────────────┐
│                     AI 简历优化器                         │
├──────────────┬──────────────┬──────────────┬─────────────┤
│  核心优化     │  求职工具     │  Pro 功能     │  管理后台    │
├──────────────┼──────────────┼──────────────┼─────────────┤
│ ATS 评分     │ 求职信生成    │ 批量处理      │ 数据总览     │
│ JD 匹配     │ 面试准备      │ 版本管理      │ 用户管理     │
│ AI 优化     │ 技能差距分析   │ PDF/Word 导出 │ 简历管理     │
│ 多模型支持   │ ATS 格式检查  │ 团队协作      │ API Key 监控 │
│ 文件上传     │              │ 用量统计      │ 系统配置     │
└──────────────┴──────────────┴──────────────┴─────────────┘
```

## 核心功能

### 简历优化

- **ATS 评分**：模拟简历筛选系统打分，0-100 分直观展示简历质量
- **岗位 JD 匹配**：粘贴职位描述，AI 针对性优化简历并计算匹配度
- **AI 智能优化**：一键生成专业简历，支持多模型切换
- **多模型支持**：DeepSeek / 通义千问 / Kimi / MiMo，用户可自定义 API Key
- **文件上传**：支持 PDF、Word、TXT 文件解析

### 求职工具

- **求职信生成**：基于简历+JD 量身定制求职信，支持语气风格选择（专业/轻松/热情）
- **面试准备**：AI 生成面试题+参考答案+答题技巧，涵盖技术/行为/情景/职业规划
- **技能差距分析**：逐条对比简历与 JD，标注技能匹配度并给出学习建议
- **ATS 格式检查**：检查简历是否能被 ATS 系统正确解析，5 维度评分

### Pro 功能

- **批量处理**：一次提交多份简历，异步队列处理
- **版本管理**：保存多个版本，支持版本对比和回滚
- **PDF/Word 导出**：将优化后的简历导出为格式化文件
- **API 用量统计**：按提供商/日期统计调用量、Token 消耗、费用
- **团队协作**：创建团队、邀请成员、评论简历、审批流程

### 管理后台

- **数据总览**：用户数、优化次数、API 调用、7 天趋势图
- **用户管理**：查看/搜索用户、设为管理员、禁用/启用、重置密码
- **简历管理**：查看所有优化记录、按用户筛选、删除
- **API Key 监控**：查看所有用户的 API Key 配置状态
- **亮暗主题切换**：支持亮色/暗色主题，跨页面同步

## 项目结构

```
ai-resume-optimizer/
├── main.py                          # FastAPI 入口（路由注册 + 启动逻辑）
├── app/
│   ├── config.py                    # 配置管理（pydantic-settings）
│   ├── database.py                  # 数据库连接
│   ├── models.py                    # SQLAlchemy 模型（10 张表）
│   ├── schemas.py                   # Pydantic 数据校验
│   ├── routers/
│   │   ├── pages.py                 # 页面路由（首页/登录页）
│   │   ├── auth.py                  # 认证路由（注册/登录/获取用户信息）
│   │   ├── resume.py                # 核心路由（优化/上传/历史/批量/版本/团队/求职工具）
│   │   ├── api_keys.py              # API Key 管理路由
│   │   ├── export.py                # 导出路由（PDF/Word）
│   │   └── admin.py                 # 管理后台路由
│   └── services/
│       ├── ai_service.py            # AI 分析服务（多模型 + 用量记录 + 求职工具）
│       ├── auth_service.py          # 认证服务（JWT + 密码哈希）
│       └── file_parser.py           # 文件解析（PDF/Word/TXT）
├── templates/
│   ├── index.html                   # 用户首页（亮暗主题 + 求职工具面板）
│   ├── login.html                   # 登录/注册页
│   └── admin.html                   # 管理后台页
├── tests/                           # 测试文件
├── scripts/                         # 部署/调试脚本
├── Dockerfile                       # Docker 镜像构建
├── docker-compose.yml               # Docker Compose 编排
├── requirements.txt                 # Python 依赖
├── secrets.json                     # API Key 配置（本地密钥）
├── .env.example                     # 环境变量模板
└── .gitignore
```

## 技术架构

```
用户请求 → Router → Service(AI/DB) → Model(ORM) → MySQL
                                      ↓
                              AI SDK(OpenAI兼容) → DeepSeek/通义千问/Kimi/MiMo
```

| 层 | 职责 | 关键文件 |
|---|------|---------|
| 路由层 | HTTP 请求处理、参数校验、调用服务 | `routers/*.py` |
| 服务层 | 业务逻辑、AI 调用、认证 | `services/*.py` |
| 数据层 | ORM 模型、数据库交互 | `models.py`, `database.py` |
| 配置层 | 环境变量、API Key、数据库连接 | `config.py`, `secrets.json` |
| 前端层 | 原生 HTML/CSS/JS 单页应用 | `templates/*.html` |

## 快速开始

### 环境要求

- Python 3.11+
- MySQL 8.0+
- DeepSeek API Key（或其他模型的 API Key）

### 1. 创建虚拟环境并安装依赖

```bash
cd ai-resume-optimizer
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```

### 2. 配置 API Key

编辑 `secrets.json`，填入你的 API Key：

```json
{
  "deepseek_api_key": "sk-your-api-key",
  "deepseek_base_url": "https://api.deepseek.com",
  "deepseek_model": "deepseek-chat"
}
```

或复制 `.env.example` 为 `.env` 并填入配置。

### 3. 创建数据库

```sql
CREATE DATABASE resume_db CHARACTER SET utf8mb4;
```

### 4. 启动服务

```bash
uvicorn main:app --reload --port 8000
```

服务启动后会自动：
- 创建数据库表
- 添加缺失的字段（兼容旧数据库）
- 创建默认管理员账号 `root` / `root`

### 5. 访问系统

| 地址 | 说明 |
|------|------|
| http://localhost:8000/ | 用户首页 |
| http://localhost:8000/login | 登录/注册 |
| http://localhost:8000/admin/ | 管理后台 |
| http://localhost:8000/docs | Swagger API 文档 |

## API 接口

### 简历优化

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/optimize` | 粘贴文本优化（支持 JD 匹配） |
| POST | `/upload` | 上传文件优化（支持 JD 匹配） |
| GET | `/providers` | 获取可用模型列表 |

### 求职工具

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/cover-letter` | 生成求职信（支持 JD + 公司名 + 语气风格） |
| POST | `/interview-prep` | 生成面试题（3-20 题可选，含答案+技巧） |
| POST | `/skills-gap` | 技能差距分析（匹配度 + 学习建议） |
| POST | `/ats-check` | ATS 格式检查（5 维度评分） |

### 历史记录

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/history` | 获取当前用户优化历史 |
| GET | `/history/{id}` | 获取单条记录详情 |
| DELETE | `/history/{id}` | 删除记录 |

### 批量处理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/batch` | 提交批量优化任务 |
| GET | `/batch/{task_id}` | 查询批量任务状态 |

### 版本管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/history/{id}/versions` | 获取所有版本 |
| POST | `/history/{id}/versions` | 保存为新版本 |
| GET | `/history/{id}/versions/compare` | 对比两个版本 |
| POST | `/history/{id}/versions/{v}/rollback` | 回滚到指定版本 |

### 导出

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/export/{id}?format=pdf` | 导出 PDF |
| GET | `/export/{id}?format=docx` | 导出 Word |

### 用量统计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/usage` | 获取 API 用量统计 |

### 团队协作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/teams` | 创建团队 |
| GET | `/teams` | 获取团队列表 |
| POST | `/teams/{id}/invite` | 邀请成员 |
| GET | `/teams/{id}/members` | 获取成员列表 |
| POST | `/teams/{id}/resumes/{id}/comment` | 添加评论 |
| GET | `/teams/{id}/resumes/{id}/comments` | 获取评论列表 |
| POST | `/teams/{id}/resumes/{id}/approve` | 审批简历 |

### 认证

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/auth/register` | 注册新用户 |
| POST | `/auth/login` | 用户登录 |
| GET | `/auth/me` | 获取当前用户信息 |

### API Key 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api-keys` | 获取用户的 API Key |
| POST | `/api-keys` | 添加/更新 API Key |
| PUT | `/api-keys/{id}` | 更新 API Key |
| DELETE | `/api-keys/{id}` | 删除 API Key |
| POST | `/api-keys/{id}/toggle` | 启用/禁用 API Key |
| POST | `/api-keys/test` | 测试 API Key 连接 |

### 管理后台

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/` | 管理后台页面 |
| GET | `/admin/stats` | 系统统计数据 |
| GET | `/admin/users` | 用户列表 |
| PUT | `/admin/users/{id}` | 更新用户状态 |
| DELETE | `/admin/users/{id}` | 删除用户 |
| POST | `/admin/users/{id}/reset-password` | 重置密码 |
| GET | `/admin/resumes` | 简历列表 |
| DELETE | `/admin/resumes/{id}` | 删除简历 |
| GET | `/admin/api-keys` | API Key 列表 |
| GET | `/admin/config` | 系统配置 |

## Docker 部署

### 一键启动

```bash
docker-compose up -d --build
```

自动完成：
- 拉取 MySQL 8.0 镜像
- 构建 FastAPI 后端镜像
- 等待 MySQL 健康检查通过后启动后端
- 自动建表 + 创建管理员

### 常用命令

```bash
docker-compose ps                    # 查看状态
docker-compose logs -f web           # 查看日志
docker-compose down                  # 停止服务
docker-compose down -v               # 停止并清除数据
docker-compose up -d --build         # 重新构建
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | MySQL 连接串 | `mysql+pymysql://root:***@localhost:3306/resume_db` |
| `DEFAULT_PROVIDER` | 默认 AI 提供商 | `deepseek` |
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | 无 |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | DeepSeek 模型名称 | `deepseek-chat` |
| `QWEN_API_KEY` | 通义千问 API 密钥 | 无 |
| `QWEN_BASE_URL` | 通义千问 API 地址 | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `QWEN_MODEL` | 通义千问模型名称 | `qwen-plus` |
| `KIMI_API_KEY` | Kimi API 密钥 | 无 |
| `KIMI_BASE_URL` | Kimi API 地址 | `https://api.moonshot.cn/v1` |
| `KIMI_MODEL` | Kimi 模型名称 | `moonshot-v1-8k` |
| `MIMO_API_KEY` | MiMo API 密钥 | 无 |
| `MIMO_BASE_URL` | MiMo API 地址 | `https://api.xiaomi.com/v1` |
| `MIMO_MODEL` | MiMo 模型名称 | `mimo-auto` |

## 数据库表结构

| 表名 | 说明 |
|------|------|
| `users` | 用户表（含 is_admin/is_active） |
| `resumes` | 简历表（含 ATS 评分、JD 匹配、批量 ID） |
| `resume_versions` | 简历版本表 |
| `resume_features` | 求职工具结果表（求职信/面试题/技能差距/ATS 检查） |
| `user_api_keys` | 用户 API Key 配置 |
| `teams` | 团队表 |
| `team_members` | 团队成员表 |
| `team_resumes` | 团队简历关联表 |
| `team_comments` | 团队评论表 |
| `usage_logs` | API 用量日志 |
| `rate_limits` | 每日限流计数 |

## 技术栈

- **后端**：FastAPI + SQLAlchemy + Pydantic
- **数据库**：MySQL 8.0
- **AI**：OpenAI SDK（兼容 DeepSeek/通义千问/Kimi/MiMo）
- **认证**：JWT Token + bcrypt 密码哈希
- **前端**：原生 HTML/CSS/JS（亮暗主题切换）
- **导出**：reportlab（PDF）+ python-docx（Word）
- **部署**：Docker + Docker Compose

## 默认管理员

系统启动时自动创建管理员账号：

- 用户名：`root`
- 密码：`root`

登录后自动跳转管理后台。

## License

MIT
