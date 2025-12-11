"""用户数据模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """用户表"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)

    # 用户技能水平: beginner, intermediate, advanced
    skill_level = Column(String(20), default="beginner")

    # 每日时间预算（分钟）
    daily_time_budget = Column(Integer, default=60)

    # 偏好设置（JSON）
    preferred_difficulty = Column(JSON, default=list)  # ["easy", "medium"]
    weak_tags = Column(JSON, default=list)  # 需要加强的标签
    strong_tags = Column(JSON, default=list)  # 擅长的标签

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    plans = relationship("Plan", back_populates="user", cascade="all, delete-orphan")
    progress_records = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', skill_level='{self.skill_level}')>"
