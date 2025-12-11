"""
调度算法 - 多天计划生成器

整合时间分配、任务调度和优先级计算，生成完整的多天刷题计划。

算法流程：
1. 题目预处理和优先级计算
2. 初始日程分配（贪心或调度算法）
3. 知识图谱建立（识别依赖关系）
4. 跨天优化（确保连贯性）
5. 最终验证和调整
"""
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import date, timedelta
from collections import defaultdict

from .time_allocator import TimeAllocator, UserHistory
from .task_scheduler import TaskScheduler, ScheduleConstraints, ScheduleResult
from ..greedy.priority_calculator import PriorityCalculator, Problem, UserProfile


@dataclass
class PlanConfig:
    """计划配置"""
    start_date: date
    daily_time_budget: int
    total_days: int
    user_skill_level: str
    difficulty_distribution: Optional[Dict[str, float]] = None  # {"easy": 0.3, "medium": 0.5, "hard": 0.2}
    focus_tags: Optional[List[str]] = None
    target_companies: Optional[List[str]] = None
    enable_dependency_ordering: bool = True  # 启用依赖排序
    enable_tag_grouping: bool = True  # 启用标签分组


@dataclass
class MultiDayPlan:
    """多天计划"""
    plan_id: str
    title: str
    config: PlanConfig
    schedule_result: ScheduleResult
    knowledge_map: Dict[str, List[str]]  # 题目间的知识依赖关系
    weekly_summary: Dict[int, Dict]  # 每周总结
    metadata: Dict


class MultiDayPlanner:
    """多天计划生成器"""

    def __init__(
        self,
        priority_calculator: Optional[PriorityCalculator] = None,
        task_scheduler: Optional[TaskScheduler] = None,
        time_allocator: Optional[TimeAllocator] = None
    ):
        """
        初始化多天计划生成器

        Args:
            priority_calculator: 优先级计算器
            task_scheduler: 任务调度器
            time_allocator: 时间分配器
        """
        self.priority_calculator = priority_calculator or PriorityCalculator()
        self.task_scheduler = task_scheduler or TaskScheduler(time_allocator)
        self.time_allocator = time_allocator or TimeAllocator()

    def generate_plan(
        self,
        problems: List[Dict],  # 题目列表
        user_profile: UserProfile,
        config: PlanConfig,
        user_history: Optional[UserHistory] = None,
        plan_title: Optional[str] = None
    ) -> MultiDayPlan:
        """
        生成完整的多天刷题计划

        Args:
            problems: 题目列表
            user_profile: 用户画像
            config: 计划配置
            user_history: 用户历史数据
            plan_title: 计划标题

        Returns:
            多天计划
        """
        # Step 1: 题目预处理和优先级排序
        processed_problems = self._preprocess_and_prioritize(
            problems,
            user_profile,
            config
        )

        # Step 2: 难度过滤（如果有难度分布要求）
        if config.difficulty_distribution:
            processed_problems = self._filter_by_difficulty_distribution(
                processed_problems,
                config.difficulty_distribution
            )

        # Step 3: 建立知识依赖图（如果启用）
        knowledge_map = {}
        if config.enable_dependency_ordering:
            knowledge_map = self._build_knowledge_map(processed_problems)
            # 根据依赖关系调整顺序
            processed_problems = self._order_by_dependencies(
                processed_problems,
                knowledge_map
            )

        # Step 4: 标签分组优化（如果启用）
        if config.enable_tag_grouping and config.focus_tags:
            processed_problems = self._group_by_tags(
                processed_problems,
                config.focus_tags
            )

        # Step 5: 使用任务调度器生成日程
        constraints = ScheduleConstraints(
            daily_time_budget=config.daily_time_budget,
            max_problems_per_day=5,
            max_hard_per_day=1 if config.user_skill_level != "advanced" else 2,
            enable_fatigue_model=True,
            enable_tag_coherence=config.enable_tag_grouping
        )

        schedule_result = self.task_scheduler.schedule(
            problems=processed_problems,
            user_skill_level=config.user_skill_level,
            total_days=config.total_days,
            constraints=constraints,
            user_history=user_history,
            preferred_tags=config.focus_tags
        )

        # Step 6: 生成每周总结
        weekly_summary = self._generate_weekly_summary(schedule_result)

        # Step 7: 构建最终计划
        plan_title = plan_title or f"{config.total_days}天刷题计划"
        plan_id = f"plan_{int(config.start_date.timestamp() if hasattr(config.start_date, 'timestamp') else 0)}"

        plan = MultiDayPlan(
            plan_id=plan_id,
            title=plan_title,
            config=config,
            schedule_result=schedule_result,
            knowledge_map=knowledge_map,
            weekly_summary=weekly_summary,
            metadata={
                "generated_at": date.today().isoformat(),
                "algorithm_version": "1.0",
                "total_problems_available": len(problems),
                "problems_scheduled": schedule_result.total_problems,
                "coverage_rate": schedule_result.total_problems / len(problems) if problems else 0
            }
        )

        return plan

    def _preprocess_and_prioritize(
        self,
        problems: List[Dict],
        user_profile: UserProfile,
        config: PlanConfig
    ) -> List[Dict]:
        """
        预处理题目并计算优先级

        Args:
            problems: 原始题目列表
            user_profile: 用户画像
            config: 配置

        Returns:
            处理后的题目列表（添加 priority 字段）
        """
        processed_problems = []

        for prob_dict in problems:
            # 转换为 Problem 对象
            problem = Problem(
                id=prob_dict["id"],
                title=prob_dict.get("title", ""),
                difficulty=prob_dict["difficulty"],
                tags=prob_dict.get("tags", []),
                estimated_time=prob_dict.get("estimated_time", prob_dict.get("base_time", 30)),
                frequency=prob_dict.get("frequency", 0.5),
                acceptance_rate=prob_dict.get("acceptance_rate", 0.5),
                companies=prob_dict.get("companies", [])
            )

            # 计算优先级
            priority = self.priority_calculator.calculate_priority(
                problem,
                user_profile,
                config.target_companies
            )

            # 添加到处理后列表
            processed_dict = prob_dict.copy()
            processed_dict["priority"] = priority
            processed_dict["base_time"] = problem.estimated_time

            processed_problems.append(processed_dict)

        return processed_problems

    def _filter_by_difficulty_distribution(
        self,
        problems: List[Dict],
        difficulty_distribution: Dict[str, float]
    ) -> List[Dict]:
        """
        根据难度分布过滤题目

        例如：{"easy": 0.3, "medium": 0.5, "hard": 0.2}

        Args:
            problems: 题目列表
            difficulty_distribution: 难度分布要求

        Returns:
            过滤后的题目列表
        """
        # 按难度分组
        by_difficulty = defaultdict(list)
        for prob in problems:
            by_difficulty[prob["difficulty"]].append(prob)

        # 计算每个难度应选择的数量
        total_count = len(problems)
        selected = []

        for difficulty, ratio in difficulty_distribution.items():
            target_count = int(total_count * ratio)
            available = by_difficulty.get(difficulty, [])

            # 按优先级排序后取前 target_count 个
            sorted_probs = sorted(available, key=lambda x: x.get("priority", 0), reverse=True)
            selected.extend(sorted_probs[:target_count])

        # 按优先级重新排序
        selected.sort(key=lambda x: x.get("priority", 0), reverse=True)

        return selected

    def _build_knowledge_map(
        self,
        problems: List[Dict]
    ) -> Dict[str, List[str]]:
        """
        建立题目间的知识依赖关系

        基于 metadata 中的 prerequisites 和 follow_ups 字段

        Args:
            problems: 题目列表

        Returns:
            依赖关系图 {problem_id: [prerequisite_ids]}
        """
        knowledge_map = {}

        for prob in problems:
            problem_id = prob["id"]
            metadata = prob.get("metadata", {})

            # 前置题目
            prerequisites = metadata.get("prerequisites", [])
            if prerequisites:
                knowledge_map[problem_id] = prerequisites

        return knowledge_map

    def _order_by_dependencies(
        self,
        problems: List[Dict],
        knowledge_map: Dict[str, List[str]]
    ) -> List[Dict]:
        """
        根据依赖关系调整题目顺序（拓扑排序）

        Args:
            problems: 题目列表
            knowledge_map: 依赖关系图

        Returns:
            排序后的题目列表
        """
        if not knowledge_map:
            return problems

        # 简化版：将有前置依赖的题目往后排
        problem_dict = {p["id"]: p for p in problems}
        has_dependencies = set(knowledge_map.keys())

        # 分成两组：无依赖和有依赖
        no_deps = [p for p in problems if p["id"] not in has_dependencies]
        with_deps = [p for p in problems if p["id"] in has_dependencies]

        # 合并：无依赖在前，有依赖在后
        return no_deps + with_deps

    def _group_by_tags(
        self,
        problems: List[Dict],
        focus_tags: List[str]
    ) -> List[Dict]:
        """
        按标签分组，相同标签的题目聚在一起

        Args:
            problems: 题目列表
            focus_tags: 关注的标签

        Returns:
            分组后的题目列表
        """
        # 按主标签分组（取第一个 focus_tag）
        grouped = defaultdict(list)
        ungrouped = []

        for prob in problems:
            prob_tags = set(prob.get("tags", []))
            matched_tag = None

            for tag in focus_tags:
                if tag in prob_tags:
                    matched_tag = tag
                    break

            if matched_tag:
                grouped[matched_tag].append(prob)
            else:
                ungrouped.append(prob)

        # 重新组合：按 focus_tags 顺序排列各组
        result = []
        for tag in focus_tags:
            if tag in grouped:
                # 组内按优先级排序
                sorted_group = sorted(grouped[tag], key=lambda x: x.get("priority", 0), reverse=True)
                result.extend(sorted_group)

        # 添加未分组的题目
        result.extend(ungrouped)

        return result

    def _generate_weekly_summary(
        self,
        schedule_result: ScheduleResult
    ) -> Dict[int, Dict]:
        """
        生成每周总结

        Args:
            schedule_result: 调度结果

        Returns:
            每周总结 {week_num: {统计信息}}
        """
        weekly_summary = {}

        for day_schedule in schedule_result.daily_schedules:
            week_num = day_schedule.day_index // 7

            if week_num not in weekly_summary:
                weekly_summary[week_num] = {
                    "total_problems": 0,
                    "total_time": 0,
                    "difficulty_distribution": {"easy": 0, "medium": 0, "hard": 0},
                    "tag_distribution": defaultdict(int)
                }

            # 累加统计
            weekly_summary[week_num]["total_problems"] += len(day_schedule.problems)
            weekly_summary[week_num]["total_time"] += day_schedule.total_time

            for difficulty, count in day_schedule.difficulty_distribution.items():
                weekly_summary[week_num]["difficulty_distribution"][difficulty] += count

            for tag, count in day_schedule.tag_distribution.items():
                weekly_summary[week_num]["tag_distribution"][tag] += count

        # 转换 defaultdict 为 dict
        for week in weekly_summary:
            weekly_summary[week]["tag_distribution"] = dict(weekly_summary[week]["tag_distribution"])

        return weekly_summary


# 便捷函数
def generate_quick_plan(
    problems: List[Dict],
    user_skill_level: str,
    daily_time_budget: int,
    total_days: int,
    completed_problems: Optional[Set[str]] = None,
    focus_tags: Optional[List[str]] = None,
    start_date: Optional[date] = None
) -> MultiDayPlan:
    """
    快速生成刷题计划的便捷函数

    Args:
        problems: 题目列表
        user_skill_level: 用户技能水平
        daily_time_budget: 每日时间预算
        total_days: 总天数
        completed_problems: 已完成题目ID集合
        focus_tags: 关注标签
        start_date: 开始日期

    Returns:
        多天计划
    """
    # 创建用户画像
    user_profile = UserProfile(
        skill_level=user_skill_level,
        completed_problems=completed_problems or set(),
        weak_tags=[],
        strong_tags=[],
        focus_tags=focus_tags or [],
        target_difficulty=["easy", "medium"] if user_skill_level == "beginner" else ["medium", "hard"]
    )

    # 创建配置
    config = PlanConfig(
        start_date=start_date or date.today(),
        daily_time_budget=daily_time_budget,
        total_days=total_days,
        user_skill_level=user_skill_level,
        focus_tags=focus_tags
    )

    # 生成计划
    planner = MultiDayPlanner()
    return planner.generate_plan(problems, user_profile, config)
