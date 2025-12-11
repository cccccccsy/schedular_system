"""计划数据模型"""
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Date, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship

from .database import Base


class Plan(Base):
    """计划表"""

    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # 统计信息
    total_problems = Column(Integer, default=0)
    total_time = Column(Integer, default=0)  # 预估总时间（分钟）

    # 计划状态: active, completed, abandoned
    status = Column(String(20), default="active", index=True)

    # 生成配置（JSON）
    config = Column(JSON, default=dict)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    user = relationship("User", back_populates="plans")
    items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Plan(id={self.id}, title='{self.title}', status='{self.status}')>"


class PlanItem(Base):
    """计划项目表（每天的题目安排）"""

    __tablename__ = "plan_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)

    # 题目信息（引用 JSON 文件中的题目 ID）
    problem_id = Column(String(50), nullable=False, index=True)

    # 调度信息
    day_index = Column(Integer, nullable=False)  # 第几天（0-based）
    order_in_day = Column(Integer, nullable=False)  # 当天的顺序（0-based）
    scheduled_time = Column(Integer)  # 分配的时间（分钟）

    # 算法计算的结果
    priority_score = Column(Float)  # 优先级分数
    reason = Column(String(500))  # 选择这道题的原因

    # 关系
    plan = relationship("Plan", back_populates="items")

    def __repr__(self):
        return f"<PlanItem(id={self.id}, problem_id='{self.problem_id}', day={self.day_index})>"
