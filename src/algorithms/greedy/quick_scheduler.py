"""
贪心算法 - 快速调度器

使用简单贪心策略快速生成刷题计划。
适用场景：
- 题目数量大（>500）
- 需要实时响应
- 对最优性要求不高

算法复杂度：O(n log n)
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import date, timedelta

from .priority_calculator import PriorityCalculator, Problem, UserProfile


@dataclass
class DaySchedule:
    """单日计划"""
    day_index: int
    date: date
    problems: List[Tuple[Problem, int, float]]  # (problem, allocated_time, priority)
    total_time: int
    difficulty_distribution: Dict[str, int]


@dataclass
class QuickScheduleResult:
    """快速调度结果"""
    daily_schedules: List[DaySchedule]
    total_problems: int
    total_time: int
    total_days: int
    unscheduled_problems: List[Problem]  # 未能安排的题目
    metadata: Dict


class QuickScheduler:
    """
    快速调度器

    核心思想：
    1. 按优先级排序所有题目（O(n log n)）
    2. 顺序填充每天的时间槽（O(n)）
    3. 不做复杂优化，只保证基本约束
    """

    def __init__(self, priority_calculator: Optional[PriorityCalculator] = None):
        """
        初始化快速调度器

        Args:
            priority_calculator: 优先级计算器实例，如果为None则创建新实例
        """
        self.priority_calculator = priority_calculator or PriorityCalculator()

    def schedule(
        self,
        problems: List[Problem],
        user_profile: UserProfile,
        daily_time_budget: int,
        total_days: int,
        start_date: Optional[date] = None,
        target_companies: Optional[List[str]] = None
    ) -> QuickScheduleResult:
        """
        快速生成刷题计划

        Args:
            problems: 题目列表
            user_profile: 用户画像
            daily_time_budget: 每日时间预算（分钟）
            total_days: 总天数
            start_date: 开始日期，默认为今天
            target_companies: 目标公司列表

        Returns:
            快速调度结果
        """
        if not start_date:
            start_date = date.today()

        # Step 1: 过滤已完成的题目
        available_problems = [
            p for p in problems
            if p.id not in user_profile.completed_problems
        ]

        # Step 2: 按优先级排序（贪心核心）
        ranked_problems = self.priority_calculator.rank_problems(
            available_problems,
            user_profile,
            target_companies
        )

        # Step 3: 顺序填充每天的计划
        daily_schedules = []
        problem_index = 0
        unscheduled = []

        for day in range(total_days):
            day_schedule = self._fill_day(
                day_index=day,
                schedule_date=start_date + timedelta(days=day),
                ranked_problems=ranked_problems,
                start_index=problem_index,
                time_budget=daily_time_budget
            )

            daily_schedules.append(day_schedule)
            problem_index += len(day_schedule.problems)

            # 如果所有题目都已安排，提前结束
            if problem_index >= len(ranked_problems):
                break

        # 未能安排的题目
        if problem_index < len(ranked_problems):
            unscheduled = [p for p, _ in ranked_problems[problem_index:]]

        # 统计信息
        total_problems_scheduled = sum(len(ds.problems) for ds in daily_schedules)
        total_time_scheduled = sum(ds.total_time for ds in daily_schedules)

        # 构造结果
        result = QuickScheduleResult(
            daily_schedules=daily_schedules,
            total_problems=total_problems_scheduled,
            total_time=total_time_scheduled,
            total_days=len(daily_schedules),
            unscheduled_problems=unscheduled,
            metadata={
                "algorithm": "quick_scheduler",
                "complexity": "O(n log n)",
                "available_problems": len(available_problems),
                "utilization_rate": total_time_scheduled / (total_days * daily_time_budget)
                    if total_days > 0 else 0
            }
        )

        return result

    def _fill_day(
        self,
        day_index: int,
        schedule_date: date,
        ranked_problems: List[Tuple[Problem, float]],
        start_index: int,
        time_budget: int
    ) -> DaySchedule:
        """
        填充单日计划

        贪心策略：从 start_index 开始，顺序选择题目直到时间用完

        Args:
            day_index: 第几天（0-based）
            schedule_date: 日期
            ranked_problems: 已排序的题目列表
            start_index: 起始索引
            time_budget: 时间预算（分钟）

        Returns:
            单日计划
        """
        selected_problems = []
        time_used = 0
        difficulty_dist = {"easy": 0, "medium": 0, "hard": 0}

        index = start_index
        while index < len(ranked_problems) and time_used < time_budget:
            problem, priority = ranked_problems[index]

            # 估算时间（简单估算，可以更复杂）
            allocated_time = problem.estimated_time

            # 检查是否还有足够时间
            if time_used + allocated_time <= time_budget:
                selected_problems.append((problem, allocated_time, priority))
                time_used += allocated_time
                difficulty_dist[problem.difficulty] += 1
                index += 1
            else:
                # 尝试找一道时间更短的题目填充剩余时间
                remaining_time = time_budget - time_used
                found = False

                for j in range(index + 1, min(index + 10, len(ranked_problems))):
                    candidate, candidate_priority = ranked_problems[j]
                    if candidate.estimated_time <= remaining_time:
                        selected_problems.append((
                            candidate,
                            candidate.estimated_time,
                            candidate_priority
                        ))
                        time_used += candidate.estimated_time
                        difficulty_dist[candidate.difficulty] += 1
                        found = True
                        # 注意：这里不增加 index，因为主循环还会继续处理
                        break

                if not found:
                    break

        return DaySchedule(
            day_index=day_index,
            date=schedule_date,
            problems=selected_problems,
            total_time=time_used,
            difficulty_distribution=difficulty_dist
        )

    def schedule_with_constraints(
        self,
        problems: List[Problem],
        user_profile: UserProfile,
        daily_time_budget: int,
        total_days: int,
        max_hard_per_day: int = 1,
        min_easy_per_day: int = 1,
        start_date: Optional[date] = None,
        target_companies: Optional[List[str]] = None
    ) -> QuickScheduleResult:
        """
        带约束的快速调度

        额外约束：
        - 每天最多 max_hard_per_day 道 hard 题
        - 每天至少 min_easy_per_day 道 easy 题

        Args:
            problems: 题目列表
            user_profile: 用户画像
            daily_time_budget: 每日时间预算
            total_days: 总天数
            max_hard_per_day: 每天最多 hard 题数
            min_easy_per_day: 每天最少 easy 题数
            start_date: 开始日期
            target_companies: 目标公司列表

        Returns:
            调度结果
        """
        if not start_date:
            start_date = date.today()

        # 过滤已完成的题目
        available_problems = [
            p for p in problems
            if p.id not in user_profile.completed_problems
        ]

        # 按难度分组
        problems_by_difficulty = {
            "easy": [],
            "medium": [],
            "hard": []
        }
        for p in available_problems:
            problems_by_difficulty[p.difficulty].append(p)

        # 分别对每个难度级别排序
        ranked_by_difficulty = {}
        for difficulty, prob_list in problems_by_difficulty.items():
            ranked = self.priority_calculator.rank_problems(
                prob_list,
                user_profile,
                target_companies
            )
            ranked_by_difficulty[difficulty] = ranked

        # 填充每天的计划（带约束）
        daily_schedules = []
        indices = {"easy": 0, "medium": 0, "hard": 0}

        for day in range(total_days):
            day_schedule = self._fill_day_with_constraints(
                day_index=day,
                schedule_date=start_date + timedelta(days=day),
                ranked_by_difficulty=ranked_by_difficulty,
                indices=indices,
                time_budget=daily_time_budget,
                max_hard=max_hard_per_day,
                min_easy=min_easy_per_day
            )

            daily_schedules.append(day_schedule)

            # 检查是否所有题目都已用完
            if all(indices[d] >= len(ranked_by_difficulty[d]) for d in ["easy", "medium", "hard"]):
                break

        # 收集未安排的题目
        unscheduled = []
        for difficulty in ["easy", "medium", "hard"]:
            remaining = ranked_by_difficulty[difficulty][indices[difficulty]:]
            unscheduled.extend([p for p, _ in remaining])

        # 统计
        total_problems_scheduled = sum(len(ds.problems) for ds in daily_schedules)
        total_time_scheduled = sum(ds.total_time for ds in daily_schedules)

        result = QuickScheduleResult(
            daily_schedules=daily_schedules,
            total_problems=total_problems_scheduled,
            total_time=total_time_scheduled,
            total_days=len(daily_schedules),
            unscheduled_problems=unscheduled,
            metadata={
                "algorithm": "quick_scheduler_with_constraints",
                "constraints": {
                    "max_hard_per_day": max_hard_per_day,
                    "min_easy_per_day": min_easy_per_day
                },
                "utilization_rate": total_time_scheduled / (total_days * daily_time_budget)
                    if total_days > 0 else 0
            }
        )

        return result

    def _fill_day_with_constraints(
        self,
        day_index: int,
        schedule_date: date,
        ranked_by_difficulty: Dict[str, List[Tuple[Problem, float]]],
        indices: Dict[str, int],
        time_budget: int,
        max_hard: int,
        min_easy: int
    ) -> DaySchedule:
        """
        填充单日计划（带约束）

        策略：
        1. 先尝试满足 min_easy 约束
        2. 添加 medium 题目
        3. 在不超过 max_hard 的前提下添加 hard 题
        4. 继续添加其他题目直到时间用完

        Args:
            day_index: 天索引
            schedule_date: 日期
            ranked_by_difficulty: 按难度分组的排序题目
            indices: 当前各难度的索引位置
            time_budget: 时间预算
            max_hard: 最多 hard 题数
            min_easy: 最少 easy 题数

        Returns:
            单日计划
        """
        selected_problems = []
        time_used = 0
        difficulty_dist = {"easy": 0, "medium": 0, "hard": 0}

        # Step 1: 先满足 min_easy 约束
        while (difficulty_dist["easy"] < min_easy and
               indices["easy"] < len(ranked_by_difficulty["easy"]) and
               time_used < time_budget):
            problem, priority = ranked_by_difficulty["easy"][indices["easy"]]
            if time_used + problem.estimated_time <= time_budget:
                selected_problems.append((problem, problem.estimated_time, priority))
                time_used += problem.estimated_time
                difficulty_dist["easy"] += 1
                indices["easy"] += 1
            else:
                break

        # Step 2: 轮流添加 medium, easy, hard（按优先级）
        while time_used < time_budget:
            added = False

            # 尝试添加题目的顺序（优先级从高到低）
            for difficulty in ["medium", "easy", "hard"]:
                # 检查 hard 约束
                if difficulty == "hard" and difficulty_dist["hard"] >= max_hard:
                    continue

                # 检查是否还有该难度的题目
                if indices[difficulty] >= len(ranked_by_difficulty[difficulty]):
                    continue

                problem, priority = ranked_by_difficulty[difficulty][indices[difficulty]]

                # 检查时间是否足够
                if time_used + problem.estimated_time <= time_budget:
                    selected_problems.append((problem, problem.estimated_time, priority))
                    time_used += problem.estimated_time
                    difficulty_dist[difficulty] += 1
                    indices[difficulty] += 1
                    added = True
                    break

            if not added:
                break

        return DaySchedule(
            day_index=day_index,
            date=schedule_date,
            problems=selected_problems,
            total_time=time_used,
            difficulty_distribution=difficulty_dist
        )


# 便捷函数
def quick_schedule(
    problems: List[Problem],
    user_profile: UserProfile,
    daily_time_budget: int,
    total_days: int,
    **kwargs
) -> QuickScheduleResult:
    """
    快速生成刷题计划的便捷函数

    Args:
        problems: 题目列表
        user_profile: 用户画像
        daily_time_budget: 每日时间预算
        total_days: 总天数
        **kwargs: 其他可选参数

    Returns:
        调度结果
    """
    scheduler = QuickScheduler()
    return scheduler.schedule(
        problems,
        user_profile,
        daily_time_budget,
        total_days,
        **kwargs
    )
