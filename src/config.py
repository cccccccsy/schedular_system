"""应用配置"""
import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """应用配置类"""

    # 应用信息
    app_name: str = "智能刷题计划调度系统"
    app_version: str = "0.1.0"
    debug: bool = True

    # API 配置
    api_v1_prefix: str = "/api/v1"

    # 数据库配置
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/database/app.db"

    # 数据文件路径
    problems_json_path: str = str(BASE_DIR / "data" / "problems" / "problems.json")
    tags_json_path: str = str(BASE_DIR / "data" / "problems" / "tags.json")

    # CORS 配置
    cors_origins: list[str] = ["*"]

    # 算法配置
    default_daily_time_budget: int = 60  # 默认每日时间预算（分钟）
    difficulty_weights: dict = {
        "easy": 1.0,
        "medium": 1.5,
        "hard": 2.5
    }

    # 优先级计算权重
    priority_weights: dict = {
        "frequency": 0.3,
        "difficulty_match": 0.25,
        "tag_relevance": 0.25,
        "recency": 0.1,
        "time_cost": 0.1
    }

    # 性能配置
    max_problems_per_request: int = 500
    cache_ttl_seconds: int = 3600

    class Config:
        env_file = ".env"
        case_sensitive = False


# 创建全局配置实例
settings = Settings()
