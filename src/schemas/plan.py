"""计划相关的 Pydantic Schemas"""
from typing import List, Optional, Dict
from datetime import date, datetime
from pydantic import BaseModel, Field


class PlanPreferences(BaseModel):
    """计划偏好设置"""
    difficulty_distribution: Optional[Dict[str, float]] = Field(
        None,
        description="难度分布，如 {'easy': 0.3, 'medium': 0.5, 'hard': 0.2}"
    )
    focus_tags: Optional[List[str]] = Field(None, description="重点标签")
    target_companies: Optional[List[str]] = Field(None, description="目标公司")
    algorithm_mode: str = Field(
        default="balanced",
        description="算法模式: balanced(均衡), aggressive(激进), conservative(保守)"
    )
    enable_dependency_ordering: bool = Field(default=True, description="启用依赖排序")
    enable_tag_grouping: bool = Field(default=True, description="启用标签分组")


class PlanCreate(BaseModel):
    """创建计划的请求模型"""
    user_id: int = Field(..., description="用户ID")
    title: Optional[str] = Field(None, max_length=200, description="计划标题")
    problem_ids: Optional[List[str]] = Field(None, description="指定题目ID列表（可选，不提供则自动推荐）")
    start_date: date = Field(..., description="开始日期")
    daily_time_budget: int = Field(..., ge=10, le=480, description="每日时间预算（分钟）")
    total_days: int = Field(..., ge=1, le=365, description="总天数")
    preferences: Optional[PlanPreferences] = None


class ScheduledProblemInfo(BaseModel):
    """计划中的题目信息"""
    problem_id: str
    title: str
    difficulty: str
    tags: List[str]
    estimated_time: int
    priority_score: float
    reason: str  # 选择这道题的原因


class DaySchedule(BaseModel):
    """单日计划"""
    day: int = Field(..., description="第几天（1-based）")
    schedule_date: date = Field(..., description="日期", alias="date")
    problems: List[ScheduledProblemInfo]
    total_time: int = Field(..., description="总时间（分钟）")
    difficulty_balance: Dict[str, int] = Field(..., description="难度分布")

    model_config = {"populate_by_name": True}


class PlanStatistics(BaseModel):
    """计划统计信息"""
    tag_coverage: Dict[str, int]  # 标签覆盖次数
    difficulty_distribution: Dict[str, int]
    estimated_completion_rate: float
    avg_daily_time: float
    optimization_score: Optional[float] = None


class PlanResponse(BaseModel):
    """计划响应模型"""
    plan_id: int
    user_id: int
    title: str
    start_date: date
    end_date: date
    total_problems: int
    total_estimated_time: int
    status: str
    daily_schedule: List[DaySchedule]
    statistics: PlanStatistics
    created_at: datetime

    class Config:
        from_attributes = True


class PlanProgressUpdate(BaseModel):
    """更新计划进度的请求模型"""
    problem_id: str = Field(..., description="题目ID")
    status: str = Field(..., description="状态: completed, skipped, in_progress")
    time_spent: Optional[int] = Field(None, ge=0, description="实际花费时间")
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5, description="难度评分")
    notes: Optional[str] = None


class PlanProgressResponse(BaseModel):
    """计划进度响应"""
    plan_id: int
    completed_problems: int
    total_problems: int
    days_elapsed: int
    total_days: int
    on_track: bool
    completion_rate: float
    next_recommendation: Optional[ScheduledProblemInfo] = None


class PlanAdjustRequest(BaseModel):
    """调整计划的请求模型"""
    reason: str = Field(..., description="调整原因")
    new_daily_budget: Optional[int] = Field(None, ge=10, le=480, description="新的每日时间预算")
    new_end_date: Optional[date] = Field(None, description="新的结束日期")
    keep_remaining_days: bool = Field(True, description="保持剩余天数不变")


class PlanListResponse(BaseModel):
    """计划列表响应"""
    plans: List[PlanResponse]
    total: int
    page: int = 1
    page_size: int = 20


class QuickPlanRequest(BaseModel):
    """快速生成计划的请求（简化版）"""
    user_id: int
    daily_time_budget: int = Field(60, ge=10, le=480)
    total_days: int = Field(30, ge=1, le=365)
    focus_tags: Optional[List[str]] = None
    target_companies: Optional[List[str]] = None
