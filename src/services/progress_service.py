"""
进度跟踪服务

管理用户的学习进度，包括：
1. 记录题目完成情况
2. 更新计划进度
3. 统计学习数据
4. 触发推荐系统更新
"""
from typing import List, Optional, Dict, Set
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
from dataclasses import dataclass

from models.plan import Plan, PlanItem
from models.progress import UserProgress as Progress, ProblemSubmission
from models.user import User
from algorithms.recommender.history_analyzer import (
    HistoryAnalyzer, AttemptRecord, analyze_user_history
)


@dataclass
class ProgressStats:
    """进度统计"""
    total_completed: int
    total_in_plan: int
    completion_rate: float
    total_time_spent: int
    streak_days: int
    by_difficulty: Dict[str, int]
    by_tag: Dict[str, int]
    today_completed: int
    today_time_spent: int


@dataclass
class CompletionResult:
    """完成结果"""
    success: bool
    message: str
    updated_progress: Optional[Dict]
    plan_progress: Optional[float]  # 计划完成百分比
    streak_bonus: bool  # 是否获得连续学习加成
    next_recommendation: Optional[str]  # 下一步推荐


class ProgressService:
    """进度跟踪服务"""

    def __init__(self):
        """初始化服务"""
        self.history_analyzer = HistoryAnalyzer()

    async def record_completion(
        self,
        user_id: int,
        plan_id: int,
        problem_id: str,
        time_spent: int,
        success: bool,
        difficulty_rating: Optional[int] = None,
        notes: Optional[str] = None,
        db: AsyncSession = None
    ) -> CompletionResult:
        """
        记录题目完成情况

        Args:
            user_id: 用户ID
            plan_id: 计划ID
            problem_id: 题目ID
            time_spent: 花费时间（分钟）
            success: 是否成功完成
            difficulty_rating: 用户对难度的评价（1-5）
            notes: 笔记
            db: 数据库会话

        Returns:
            完成结果
        """
        # 验证计划和题目
        plan_item = await self._get_plan_item(plan_id, problem_id, db)
        if not plan_item:
            return CompletionResult(
                success=False,
                message=f"计划中未找到题目: {problem_id}",
                updated_progress=None,
                plan_progress=None,
                streak_bonus=False,
                next_recommendation=None
            )

        # 检查是否已完成
        existing_progress = await self._get_progress(user_id, plan_id, problem_id, db)

        if existing_progress and existing_progress.status == "completed":
            # 更新已有记录（允许重新做）
            existing_progress.time_spent = time_spent
            existing_progress.completed_at = datetime.utcnow()
            existing_progress.difficulty_rating = difficulty_rating
            existing_progress.notes = notes
            existing_progress.attempts += 1

            await db.commit()
            await db.refresh(existing_progress)

            return CompletionResult(
                success=True,
                message="已更新完成记录",
                updated_progress=self._progress_to_dict(existing_progress),
                plan_progress=await self._calculate_plan_progress(plan_id, db),
                streak_bonus=False,
                next_recommendation=await self._get_next_recommendation(plan_id, problem_id, db)
            )

        # 创建新的进度记录
        new_progress = Progress(
            user_id=user_id,
            plan_id=plan_id,
            problem_id=problem_id,
            status="completed" if success else "attempted",
            time_spent=time_spent,
            attempts=1,
            completed_at=datetime.utcnow() if success else None,
            difficulty_rating=difficulty_rating,
            notes=notes
        )

        db.add(new_progress)

        # 更新计划项状态
        plan_item.status = "completed" if success else "in_progress"

        await db.commit()
        await db.refresh(new_progress)

        # 计算连续学习加成
        streak_bonus = await self._check_streak_bonus(user_id, db)

        # 获取下一题推荐
        next_rec = await self._get_next_recommendation(plan_id, problem_id, db)

        return CompletionResult(
            success=True,
            message="完成记录已保存" if success else "尝试记录已保存",
            updated_progress=self._progress_to_dict(new_progress),
            plan_progress=await self._calculate_plan_progress(plan_id, db),
            streak_bonus=streak_bonus,
            next_recommendation=next_rec
        )

    async def get_user_progress(
        self,
        user_id: int,
        plan_id: Optional[int] = None,
        db: AsyncSession = None
    ) -> ProgressStats:
        """
        获取用户进度统计

        Args:
            user_id: 用户ID
            plan_id: 计划ID（可选，不指定则统计全部）
            db: 数据库会话

        Returns:
            进度统计
        """
        # 构建查询
        query = select(Progress).where(Progress.user_id == user_id)
        if plan_id:
            query = query.where(Progress.plan_id == plan_id)

        result = await db.execute(query)
        progress_records = result.scalars().all()

        if not progress_records:
            return ProgressStats(
                total_completed=0,
                total_in_plan=0,
                completion_rate=0.0,
                total_time_spent=0,
                streak_days=0,
                by_difficulty={},
                by_tag={},
                today_completed=0,
                today_time_spent=0
            )

        # 统计完成数
        completed_records = [p for p in progress_records if p.status == "completed"]
        total_completed = len(completed_records)

        # 总题目数（从计划中获取）
        total_in_plan = 0
        if plan_id:
            count_query = select(func.count(PlanItem.id)).where(PlanItem.plan_id == plan_id)
            count_result = await db.execute(count_query)
            total_in_plan = count_result.scalar() or 0

        # 完成率
        completion_rate = total_completed / total_in_plan if total_in_plan > 0 else 0.0

        # 总时间
        total_time_spent = sum(p.time_spent or 0 for p in completed_records)

        # 连续天数
        streak_days = await self._calculate_streak(user_id, db)

        # 按难度统计（需要关联题目数据）
        by_difficulty = {"easy": 0, "medium": 0, "hard": 0}

        # 今日统计
        today = date.today()
        today_records = [
            p for p in completed_records
            if p.completed_at and p.completed_at.date() == today
        ]
        today_completed = len(today_records)
        today_time_spent = sum(p.time_spent or 0 for p in today_records)

        return ProgressStats(
            total_completed=total_completed,
            total_in_plan=total_in_plan,
            completion_rate=completion_rate,
            total_time_spent=total_time_spent,
            streak_days=streak_days,
            by_difficulty=by_difficulty,
            by_tag={},
            today_completed=today_completed,
            today_time_spent=today_time_spent
        )

    async def get_user_history_analysis(
        self,
        user_id: int,
        db: AsyncSession
    ) -> Dict:
        """
        获取用户历史分析

        Args:
            user_id: 用户ID
            db: 数据库会话

        Returns:
            历史分析结果
        """
        # 获取所有进度记录
        query = select(Progress).where(
            and_(
                Progress.user_id == user_id,
                Progress.status == "completed"
            )
        ).order_by(Progress.completed_at)

        result = await db.execute(query)
        progress_records = result.scalars().all()

        if not progress_records:
            return analyze_user_history([])

        # 转换为历史记录格式
        history = []
        for record in progress_records:
            # 需要获取题目信息来获取难度和标签
            # 简化处理：使用 plan_item 中缓存的信息
            history.append({
                "problem_id": record.problem_id,
                "difficulty": "medium",  # TODO: 从题目数据获取
                "tags": [],  # TODO: 从题目数据获取
                "success": record.status == "completed",
                "time_spent": record.time_spent or 30,
                "attempts": record.attempts or 1,
                "timestamp": record.completed_at.isoformat() if record.completed_at else None
            })

        return analyze_user_history(history)

    async def get_plan_progress_detail(
        self,
        plan_id: int,
        db: AsyncSession
    ) -> Dict:
        """
        获取计划详细进度

        Args:
            plan_id: 计划ID
            db: 数据库会话

        Returns:
            计划进度详情
        """
        # 获取计划
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()

        if not plan:
            return {"error": "计划不存在"}

        # 获取计划项
        items_result = await db.execute(
            select(PlanItem).where(PlanItem.plan_id == plan_id).order_by(PlanItem.day_index, PlanItem.order_in_day)
        )
        plan_items = items_result.scalars().all()

        # 获取进度记录
        progress_result = await db.execute(
            select(Progress).where(Progress.plan_id == plan_id)
        )
        progress_records = {p.problem_id: p for p in progress_result.scalars().all()}

        # 按天组织数据
        days_progress = {}
        for item in plan_items:
            if item.day_index not in days_progress:
                days_progress[item.day_index] = {
                    "day": item.day_index + 1,
                    "problems": [],
                    "completed_count": 0,
                    "total_time_spent": 0
                }

            progress = progress_records.get(item.problem_id)
            problem_status = {
                "problem_id": item.problem_id,
                "scheduled_time": item.scheduled_time,
                "status": progress.status if progress else "pending",
                "actual_time": progress.time_spent if progress else None,
                "completed_at": progress.completed_at.isoformat() if progress and progress.completed_at else None
            }

            days_progress[item.day_index]["problems"].append(problem_status)

            if progress and progress.status == "completed":
                days_progress[item.day_index]["completed_count"] += 1
                days_progress[item.day_index]["total_time_spent"] += progress.time_spent or 0

        # 统计总体进度
        total_problems = len(plan_items)
        completed_problems = len([p for p in progress_records.values() if p.status == "completed"])

        return {
            "plan_id": plan_id,
            "title": plan.title,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "total_problems": total_problems,
            "completed_problems": completed_problems,
            "completion_rate": completed_problems / total_problems if total_problems > 0 else 0,
            "days_progress": list(days_progress.values()),
            "status": plan.status
        }

    async def update_plan_status(
        self,
        plan_id: int,
        db: AsyncSession
    ) -> str:
        """
        更新计划状态

        根据完成情况自动更新计划状态

        Args:
            plan_id: 计划ID
            db: 数据库会话

        Returns:
            更新后的状态
        """
        # 获取计划进度
        progress = await self._calculate_plan_progress(plan_id, db)

        # 获取计划
        plan_result = await db.execute(select(Plan).where(Plan.id == plan_id))
        plan = plan_result.scalar_one_or_none()

        if not plan:
            return "unknown"

        # 更新状态
        if progress >= 1.0:
            plan.status = "completed"
        elif progress > 0:
            plan.status = "active"
        elif plan.end_date < date.today():
            plan.status = "expired"

        await db.commit()

        return plan.status

    async def _get_plan_item(
        self,
        plan_id: int,
        problem_id: str,
        db: AsyncSession
    ) -> Optional[PlanItem]:
        """获取计划项"""
        result = await db.execute(
            select(PlanItem).where(
                and_(
                    PlanItem.plan_id == plan_id,
                    PlanItem.problem_id == problem_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_progress(
        self,
        user_id: int,
        plan_id: int,
        problem_id: str,
        db: AsyncSession
    ) -> Optional[Progress]:
        """获取进度记录"""
        result = await db.execute(
            select(Progress).where(
                and_(
                    Progress.user_id == user_id,
                    Progress.plan_id == plan_id,
                    Progress.problem_id == problem_id
                )
            )
        )
        return result.scalar_one_or_none()

    async def _calculate_plan_progress(
        self,
        plan_id: int,
        db: AsyncSession
    ) -> float:
        """计算计划完成进度"""
        # 总题目数
        total_query = select(func.count(PlanItem.id)).where(PlanItem.plan_id == plan_id)
        total_result = await db.execute(total_query)
        total = total_result.scalar() or 0

        if total == 0:
            return 0.0

        # 完成数
        completed_query = select(func.count(Progress.id)).where(
            and_(
                Progress.plan_id == plan_id,
                Progress.status == "completed"
            )
        )
        completed_result = await db.execute(completed_query)
        completed = completed_result.scalar() or 0

        return completed / total

    async def _check_streak_bonus(
        self,
        user_id: int,
        db: AsyncSession
    ) -> bool:
        """检查是否获得连续学习加成"""
        streak = await self._calculate_streak(user_id, db)
        # 连续7天以上给予加成
        return streak >= 7

    async def _calculate_streak(
        self,
        user_id: int,
        db: AsyncSession
    ) -> int:
        """计算连续学习天数"""
        # 获取所有完成记录的日期
        query = select(Progress.completed_at).where(
            and_(
                Progress.user_id == user_id,
                Progress.status == "completed",
                Progress.completed_at.isnot(None)
            )
        ).order_by(Progress.completed_at.desc())

        result = await db.execute(query)
        dates = [row[0].date() for row in result.fetchall() if row[0]]

        if not dates:
            return 0

        # 去重并排序
        unique_dates = sorted(set(dates), reverse=True)

        # 计算连续天数
        streak = 0
        today = date.today()

        for i, d in enumerate(unique_dates):
            expected_date = today - timedelta(days=i)
            if d == expected_date:
                streak += 1
            else:
                break

        return streak

    async def _get_next_recommendation(
        self,
        plan_id: int,
        current_problem_id: str,
        db: AsyncSession
    ) -> Optional[str]:
        """获取下一题推荐"""
        # 获取当前题目的计划项
        current_item = await self._get_plan_item(plan_id, current_problem_id, db)
        if not current_item:
            return None

        # 获取同一天的下一题
        query = select(PlanItem).where(
            and_(
                PlanItem.plan_id == plan_id,
                PlanItem.day_index == current_item.day_index,
                PlanItem.order_in_day > current_item.order_in_day
            )
        ).order_by(PlanItem.order_in_day).limit(1)

        result = await db.execute(query)
        next_item = result.scalar_one_or_none()

        if next_item:
            return f"继续今天的计划: 题目 {next_item.problem_id}"

        # 如果今天的题目都完成了，推荐明天的
        query = select(PlanItem).where(
            and_(
                PlanItem.plan_id == plan_id,
                PlanItem.day_index == current_item.day_index + 1
            )
        ).order_by(PlanItem.order_in_day).limit(1)

        result = await db.execute(query)
        next_day_item = result.scalar_one_or_none()

        if next_day_item:
            return f"今天的任务已完成！明天从题目 {next_day_item.problem_id} 开始"

        return "恭喜完成计划中的所有题目！"

    def _progress_to_dict(self, progress: Progress) -> Dict:
        """转换进度记录为字典"""
        return {
            "id": progress.id,
            "user_id": progress.user_id,
            "plan_id": progress.plan_id,
            "problem_id": progress.problem_id,
            "status": progress.status,
            "time_spent": progress.time_spent,
            "attempts": progress.attempts,
            "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
            "difficulty_rating": progress.difficulty_rating,
            "notes": progress.notes
        }


# 全局服务实例
_progress_service: Optional[ProgressService] = None


def get_progress_service() -> ProgressService:
    """获取进度服务单例"""
    global _progress_service
    if _progress_service is None:
        _progress_service = ProgressService()
    return _progress_service

