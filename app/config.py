from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    DATABASE_URL: str = "mysql+pymysql://root:***@localhost:3306/resume_db?charset=utf8mb4"

    # 默认模型配置
    DEFAULT_PROVIDER: str = "deepseek"

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"

    KIMI_API_KEY: str = ""
    KIMI_BASE_URL: str = "https://api.moonshot.cn/v1"
    KIMI_MODEL: str = "moonshot-v1-8k"

    MIMO_API_KEY: str = ""
    MIMO_BASE_URL: str = "https://api.xiaomi.com/v1"
    MIMO_MODEL: str = "mimo-auto"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
