"""计划管理服务 - 核心业务逻辑，整合所有算法"""
from typing import List, Optional, Dict
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.plan import Plan, PlanItem
from models.user import User
from schemas.plan import (
    PlanCreate, PlanResponse, DaySchedule, ScheduledProblemInfo,
    PlanStatistics, PlanProgressUpdate, PlanProgressResponse
)
from services.problem_service import get_problem_service

# 导入算法模块
from algorithms.greedy.priority_calculator import (
    PriorityCalculator, Problem, UserProfile
)
from algorithms.scheduler.multi_day_planner import (
    MultiDayPlanner, PlanConfig
)
from algorithms.scheduler.task_scheduler import ScheduleConstraints
from algorithms.optimizer.dp_optimizer import DPOptimizer, LearningGoals


class PlanService:
    """计划管理服务"""

    def __init__(self):
        """初始化服务"""
        self.problem_service = get_problem_service()
        self.priority_calculator = PriorityCalculator()
        self.multi_day_planner = MultiDayPlanner()
        self.dp_optimizer = DPOptimizer()

    async def create_plan(
        self,
        plan_data: PlanCreate,
        db: AsyncSession
    ) -> PlanResponse:
        """
        创建刷题计划

        Args:
            plan_data: 计划创建请求
            db: 数据库会话

        Returns:
            计划响应
        """
        # Step 1: 获取用户信息
        result = await db.execute(select(User).where(User.id == plan_data.user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"用户不存在: {plan_data.user_id}")

        # Step 2: 准备题目列表
        if plan_data.problem_ids:
            # 使用指定的题目
            problems = [
                self.problem_service.get_problem_by_id(pid)
                for pid in plan_data.problem_ids
            ]
            problems = [p for p in problems if p is not None]
        else:
            # 自动推荐题目
            problems = self._recommend_problems(user, plan_data)

        if not problems:
            raise ValueError("没有可用的题目")

        # Step 3: 创建用户画像
        user_profile = self._create_user_profile(user)

        # Step 4: 生成计划
        multi_day_plan = await self._generate_plan(
            problems=problems,
            user=user,
            user_profile=user_profile,
            plan_data=plan_data
        )

        # Step 5: 保存到数据库
        db_plan = await self._save_plan_to_db(
            multi_day_plan=multi_day_plan,
            user_id=user.id,
            plan_data=plan_data,
            db=db
        )

        # Step 6: 构造响应
        response = await self._build_plan_response(db_plan, multi_day_plan)

        return response

    def _recommend_problems(
        self,
        user: User,
        plan_data: PlanCreate
    ) -> List[Dict]:
        """
        推荐题目

        Args:
            user: 用户对象
            plan_data: 计划数据

        Returns:
            推荐的题目列表
        """
        all_problems = self.problem_service.get_all_problems(limit=200)

        # 根据用户偏好过滤
        if user.preferred_difficulty:
            all_problems = [
                p for p in all_problems
                if p['difficulty'] in user.preferred_difficulty
            ]

        # 根据计划偏好过滤
        if plan_data.preferences and plan_data.preferences.focus_tags:
            all_problems = [
                p for p in all_problems
                if any(tag in p.get('tags', []) for tag in plan_data.preferences.focus_tags)
            ]

        return all_problems

    def _create_user_profile(self, user: User) -> UserProfile:
        """
        创建用户画像

        Args:
            user: 用户对象

        Returns:
            用户画像
        """
        return UserProfile(
            skill_level=user.skill_level,
            completed_problems=set(),  # TODO: 从数据库加载已完成题目
            weak_tags=user.weak_tags or [],
            strong_tags=user.strong_tags or [],
            focus_tags=user.weak_tags or [],  # 优先关注薄弱标签
            target_difficulty=user.preferred_difficulty or ['easy', 'medium']
        )

    async def _generate_plan(
        self,
        problems: List[Dict],
        user: User,
        user_profile: UserProfile,
        plan_data: PlanCreate
    ):
        """
        生成计划（调用算法）

        Args:
            problems: 题目列表
            user: 用户对象
            user_profile: 用户画像
            plan_data: 计划数据

        Returns:
            MultiDayPlan对象
        """
        # 创建计划配置
        config = PlanConfig(
            start_date=plan_data.start_date,
            daily_time_budget=plan_data.daily_time_budget,
            total_days=plan_data.total_days,
            user_skill_level=user.skill_level,
            difficulty_distribution=plan_data.preferences.difficulty_distribution
                if plan_data.preferences else None,
            focus_tags=plan_data.preferences.focus_tags
                if plan_data.preferences else None,
            target_companies=plan_data.preferences.target_companies
                if plan_data.preferences else None,
            enable_dependency_ordering=plan_data.preferences.enable_dependency_ordering
                if plan_data.preferences else True,
            enable_tag_grouping=plan_data.preferences.enable_tag_grouping
                if plan_data.preferences else True
        )

        # 使用多天规划器生成计划
        multi_day_plan = self.multi_day_planner.generate_plan(
            problems=problems,
            user_profile=user_profile,
            config=config,
            user_history=None,  # TODO: 加载用户历史
            plan_title=plan_data.title
        )

        return multi_day_plan

    async def _save_plan_to_db(
        self,
        multi_day_plan,
        user_id: int,
        plan_data: PlanCreate,
        db: AsyncSession
    ) -> Plan:
        """
        保存计划到数据库

        Args:
            multi_day_plan: MultiDayPlan对象
            user_id: 用户ID
            plan_data: 计划数据
            db: 数据库会话

        Returns:
            数据库Plan对象
        """
        # 创建Plan对象
        db_plan = Plan(
            user_id=user_id,
            title=multi_day_plan.title,
            start_date=multi_day_plan.config.start_date,
            end_date=multi_day_plan.config.start_date + timedelta(
                days=multi_day_plan.config.total_days - 1
            ),
            total_problems=multi_day_plan.schedule_result.total_problems,
            total_time=multi_day_plan.schedule_result.total_time,
            status="active",
            config=plan_data.model_dump() if plan_data.preferences else {}
        )

        db.add(db_plan)
        await db.flush()  # 获取plan_id

        # 创建PlanItem对象
        for day_schedule in multi_day_plan.schedule_result.daily_schedules:
            for order, problem in enumerate(day_schedule.problems):
                plan_item = PlanItem(
                    plan_id=db_plan.id,
                    problem_id=problem.problem_id,
                    day_index=day_schedule.day_index,
                    order_in_day=order,
                    scheduled_time=problem.actual_allocated_time,
                    priority_score=problem.priority_score,
                    reason=problem.reason
                )
                db.add(plan_item)

        await db.commit()
        await db.refresh(db_plan)

        return db_plan

    async def _build_plan_response(
        self,
        db_plan: Plan,
        multi_day_plan
    ) -> PlanResponse:
        """
        构建计划响应

        Args:
            db_plan: 数据库Plan对象
            multi_day_plan: MultiDayPlan对象

        Returns:
            计划响应
        """
        # 构建每日计划
        daily_schedules = []
        for day_schedule in multi_day_plan.schedule_result.daily_schedules:
            schedule_date = multi_day_plan.config.start_date + timedelta(days=day_schedule.day_index)

            problems_info = [
                ScheduledProblemInfo(
                    problem_id=p.problem_id,
                    title=p.title,
                    difficulty=p.difficulty,
                    tags=p.tags,
                    estimated_time=p.actual_allocated_time,
                    priority_score=p.priority_score,
                    reason=p.reason
                )
                for p in day_schedule.problems
            ]

            daily_schedules.append(
                DaySchedule(
                    day=day_schedule.day_index + 1,
                    schedule_date=schedule_date,
                    problems=problems_info,
                    total_time=day_schedule.total_time,
                    difficulty_balance=day_schedule.difficulty_distribution
                )
            )

        # 构建统计信息
        tag_coverage = {}
        for day_schedule in multi_day_plan.schedule_result.daily_schedules:
            for tag, count in day_schedule.tag_distribution.items():
                tag_coverage[tag] = tag_coverage.get(tag, 0) + count

        difficulty_dist = {"easy": 0, "medium": 0, "hard": 0}
        for day_schedule in multi_day_plan.schedule_result.daily_schedules:
            for diff, count in day_schedule.difficulty_distribution.items():
                difficulty_dist[diff] += count

        statistics = PlanStatistics(
            tag_coverage=tag_coverage,
            difficulty_distribution=difficulty_dist,
            estimated_completion_rate=0.85,  # TODO: 基于用户历史计算
            avg_daily_time=multi_day_plan.schedule_result.total_time / max(len(daily_schedules), 1)
        )

        return PlanResponse(
            plan_id=db_plan.id,
            user_id=db_plan.user_id,
            title=db_plan.title,
            start_date=db_plan.start_date,
            end_date=db_plan.end_date,
            total_problems=db_plan.total_problems,
            total_estimated_time=db_plan.total_time,
            status=db_plan.status,
            daily_schedule=daily_schedules,
            statistics=statistics,
            created_at=db_plan.created_at
        )

    async def get_plan_by_id(
        self,
        plan_id: int,
        db: AsyncSession
    ) -> Optional[Plan]:
        """
        根据ID获取计划

        Args:
            plan_id: 计划ID
            db: 数据库会话

        Returns:
            计划对象或None
        """
        result = await db.execute(select(Plan).where(Plan.id == plan_id))
        return result.scalar_one_or_none()

    async def get_user_plans(
        self,
        user_id: int,
        db: AsyncSession,
        status: Optional[str] = None
    ) -> List[Plan]:
        """
        获取用户的所有计划

        Args:
            user_id: 用户ID
            db: 数据库会话
            status: 状态过滤（可选）

        Returns:
            计划列表
        """
        query = select(Plan).where(Plan.user_id == user_id)

        if status:
            query = query.where(Plan.status == status)

        query = query.order_by(Plan.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())


# 全局服务实例
_plan_service: Optional[PlanService] = None


def get_plan_service() -> PlanService:
    """获取计划服务单例"""
    global _plan_service
    if _plan_service is None:
        _plan_service = PlanService()
    return _plan_service
