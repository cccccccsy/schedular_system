"""用户相关的 Pydantic Schemas"""
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
import re


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: str = Field(..., description="邮箱")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """验证邮箱格式"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式不正确")
        return v
    skill_level: str = Field(default="beginner", description="技能水平: beginner, intermediate, advanced")
    daily_time_budget: int = Field(default=60, ge=10, le=480, description="每日时间预算（分钟）")


class UserCreate(UserBase):
    """创建用户的请求模型"""
    preferred_difficulty: List[str] = Field(default=["easy", "medium"], description="偏好难度")
    weak_tags: List[str] = Field(default=[], description="薄弱标签")
    strong_tags: List[str] = Field(default=[], description="擅长标签")


class UserUpdate(BaseModel):
    """更新用户的请求模型"""
    email: Optional[str] = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """验证邮箱格式"""
        if v is None:
            return v
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("邮箱格式不正确")
        return v
    skill_level: Optional[str] = None
    daily_time_budget: Optional[int] = Field(None, ge=10, le=480)
    preferred_difficulty: Optional[List[str]] = None
    weak_tags: Optional[List[str]] = None
    strong_tags: Optional[List[str]] = None


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    preferred_difficulty: List[str]
    weak_tags: List[str]
    strong_tags: List[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProgressSummary(BaseModel):
    """用户进度摘要"""
    total_problems: int
    completed_problems: int
    in_progress_problems: int
    completion_rate: float


class UserStatsResponse(BaseModel):
    """用户统计响应"""
    user: UserResponse
    progress_summary: UserProgressSummary
    by_difficulty: Dict[str, int]
    by_tag: Dict[str, int]
    learning_curve: Dict[str, float]  # {date: rating}
    weak_areas: List[str]
    strong_areas: List[str]
    streaks: Dict[str, int]  # {"current": 7, "longest": 15}


class UserProgressCreate(BaseModel):
    """创建/更新进度的请求模型"""
    problem_id: str = Field(..., description="题目ID")
    status: str = Field(..., description="状态: not_started, in_progress, completed, skipped")
    time_spent: Optional[int] = Field(None, ge=0, description="实际花费时间（分钟）")
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5, description="用户主观难度评分 1-5")
    notes: Optional[str] = Field(None, max_length=1000, description="笔记")


class UserProgressResponse(BaseModel):
    """用户进度响应"""
    id: int
    user_id: int
    problem_id: str
    status: str
    attempts: int
    time_spent: int
    difficulty_rating: Optional[int]
    notes: Optional[str]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
