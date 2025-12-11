"""用户进度数据模型"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from .database import Base


class UserProgress(Base):
    """用户刷题进度表"""

    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    problem_id = Column(String(50), nullable=False, index=True)

    # 状态: not_started, in_progress, completed, skipped
    status = Column(String(20), default="not_started", index=True)

    # 统计信息
    attempts = Column(Integer, default=0)  # 尝试次数
    time_spent = Column(Integer, default=0)  # 实际花费时间（分钟）
    difficulty_rating = Column(Integer)  # 用户主观难度评分 1-5

    # 笔记
    notes = Column(Text)

    # 时间戳
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="progress_records")

    # 唯一约束：每个用户的每道题目只有一条记录
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", name="uq_user_problem"),
    )

    def __repr__(self):
        return f"<UserProgress(user_id={self.user_id}, problem_id='{self.problem_id}', status='{self.status}')>"


class ProblemSubmission(Base):
    """题目提交记录表（用于历史分析）"""

    __tablename__ = "problem_submissions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    problem_id = Column(String(50), nullable=False, index=True)

    # 提交信息
    success = Column(Boolean, default=False)  # 是否成功
    time_spent = Column(Integer)  # 花费时间（分钟）
    approach = Column(Text)  # 解题方法描述

    # 时间戳
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ProblemSubmission(user_id={self.user_id}, problem_id='{self.problem_id}', success={self.success})>"
