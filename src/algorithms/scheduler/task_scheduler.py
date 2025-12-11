"""
调度算法 - 任务调度核心

将题目列表分配到多天，满足时间约束和优化目标。

算法思路：
1. 背包问题变种 - 每天的时间是背包容量，题目是物品
2. 约束条件：
   - 硬约束：每天时间不超过用户预算
   - 软约束：难度平衡、知识连贯性、疲劳度模型

复杂度：O(n * d)，n = 题目数，d = 天数
"""
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import statistics

from .time_allocator import TimeAllocator, UserHistory


@dataclass
class ScheduleConstraints:
    """调度约束"""
    daily_time_budget: int  # 每日时间预算（分钟）
    max_problems_per_day: int = 5  # 每天最多题目数
    max_hard_per_day: int = 1  # 每天最多 hard 题数
    difficulty_variance_threshold: float = 0.8  # 难度方差阈值
    enable_fatigue_model: bool = True  # 是否启用疲劳度模型
    enable_tag_coherence: bool = True  # 是否启用标签连贯性


@dataclass
class ScheduledProblem:
    """已调度的题目"""
    problem_id: str
    title: str
    difficulty: str
    tags: List[str]
    estimated_time: int
    actual_allocated_time: int
    priority_score: float
    reason: str  # 选择这道题的原因


@dataclass
class DailySchedule:
    """每日调度"""
    day_index: int
    problems: List[ScheduledProblem]
    total_time: int
    difficulty_distribution: Dict[str, int]
    tag_distribution: Dict[str, int]
    fatigue_score: float = 0.0
    difficulty_variance: float = 0.0


@dataclass
class ScheduleResult:
    """调度结果"""
    daily_schedules: List[DailySchedule]
    total_problems: int
    total_time: int
    total_days: int
    unscheduled_problems: List[str]  # 未能安排的题目ID
    metadata: Dict = field(default_factory=dict)


class TaskScheduler:
    """任务调度器"""

    # 难度数值映射（用于计算方差）
    DIFFICULTY_VALUES = {
        "easy": 1.0,
        "medium": 2.0,
        "hard": 3.0
    }

    def __init__(
        self,
        time_allocator: Optional[TimeAllocator] = None
    ):
        """
        初始化任务调度器

        Args:
            time_allocator: 时间分配器实例
        """
        self.time_allocator = time_allocator or TimeAllocator()

    def schedule(
        self,
        problems: List[Dict],  # [{id, title, difficulty, tags, base_time, priority}, ...]
        user_skill_level: str,
        total_days: int,
        constraints: ScheduleConstraints,
        user_history: Optional[UserHistory] = None,
        preferred_tags: Optional[List[str]] = None
    ) -> ScheduleResult:
        """
        主调度算法

        步骤：
        1. 题目预处理和排序
        2. 初始分配（均匀分布）
        3. 约束检查和调整
        4. 难度平衡优化
        5. 标签连贯性优化

        Args:
            problems: 题目列表
            user_skill_level: 用户技能水平
            total_days: 总天数
            constraints: 调度约束
            user_history: 用户历史数据
            preferred_tags: 优先标签

        Returns:
            调度结果
        """
        if not problems or total_days <= 0:
            return ScheduleResult(
                daily_schedules=[],
                total_problems=0,
                total_time=0,
                total_days=0,
                unscheduled_problems=[],
                metadata={"error": "Invalid input"}
            )

        # Step 1: 预处理题目 - 计算每道题的估算时间
        processed_problems = self._preprocess_problems(
            problems,
            user_skill_level,
            user_history
        )

        # Step 2: 按优先级排序
        sorted_problems = sorted(
            processed_problems,
            key=lambda x: x["priority"],
            reverse=True
        )

        # Step 3: 初始分配 - 贪心填充
        daily_schedules = self._initial_allocation(
            sorted_problems,
            total_days,
            constraints
        )

        # Step 4: 难度平衡调整
        if constraints.difficulty_variance_threshold > 0:
            daily_schedules = self._balance_difficulty(
                daily_schedules,
                constraints
            )

        # Step 5: 标签连贯性优化（可选）
        if constraints.enable_tag_coherence and preferred_tags:
            daily_schedules = self._optimize_tag_coherence(
                daily_schedules,
                preferred_tags
            )

        # Step 6: 计算疲劳度（如果启用）
        if constraints.enable_fatigue_model:
            for schedule in daily_schedules:
                schedule.fatigue_score = self._calculate_fatigue(schedule)

        # 收集未调度的题目
        scheduled_ids = set()
        for day_schedule in daily_schedules:
            for problem in day_schedule.problems:
                scheduled_ids.add(problem.problem_id)

        unscheduled = [p["id"] for p in problems if p["id"] not in scheduled_ids]

        # 统计信息
        total_problems_scheduled = sum(len(ds.problems) for ds in daily_schedules)
        total_time_scheduled = sum(ds.total_time for ds in daily_schedules)

        return ScheduleResult(
            daily_schedules=daily_schedules,
            total_problems=total_problems_scheduled,
            total_time=total_time_scheduled,
            total_days=len(daily_schedules),
            unscheduled_problems=unscheduled,
            metadata={
                "algorithm": "task_scheduler",
                "constraints_applied": {
                    "max_problems_per_day": constraints.max_problems_per_day,
                    "max_hard_per_day": constraints.max_hard_per_day,
                    "fatigue_model": constraints.enable_fatigue_model,
                    "tag_coherence": constraints.enable_tag_coherence
                }
            }
        )

    def _preprocess_problems(
        self,
        problems: List[Dict],
        user_skill_level: str,
        user_history: Optional[UserHistory]
    ) -> List[Dict]:
        """
        预处理题目：计算估算时间

        Args:
            problems: 原始题目列表
            user_skill_level: 用户技能水平
            user_history: 用户历史

        Returns:
            处理后的题目列表（添加 estimated_time 字段）
        """
        processed = []

        for problem in problems:
            # 计算估算时间
            estimated_time = self.time_allocator.allocate_time(
                problem.get("base_time", problem.get("estimated_time", 30)),
                problem["difficulty"],
                problem.get("tags", []),
                user_skill_level,
                user_history
            )

            # 复制题目并添加估算时间
            processed_problem = problem.copy()
            processed_problem["estimated_time"] = estimated_time

            processed.append(processed_problem)

        return processed

    def _initial_allocation(
        self,
        problems: List[Dict],
        total_days: int,
        constraints: ScheduleConstraints
    ) -> List[DailySchedule]:
        """
        初始分配：使用贪心策略填充每天

        Args:
            problems: 排序后的题目列表
            total_days: 总天数
            constraints: 调度约束

        Returns:
            每日调度列表
        """
        daily_schedules = []
        problem_index = 0

        for day in range(total_days):
            day_schedule = self._fill_day_greedy(
                day_index=day,
                problems=problems,
                start_index=problem_index,
                constraints=constraints
            )

            daily_schedules.append(day_schedule)
            problem_index += len(day_schedule.problems)

            # 如果所有题目都已分配，结束
            if problem_index >= len(problems):
                break

        return daily_schedules

    def _fill_day_greedy(
        self,
        day_index: int,
        problems: List[Dict],
        start_index: int,
        constraints: ScheduleConstraints
    ) -> DailySchedule:
        """
        贪心填充单日计划

        约束检查：
        - 总时间不超过 daily_time_budget
        - 题目数不超过 max_problems_per_day
        - hard 题数不超过 max_hard_per_day

        Args:
            day_index: 天索引
            problems: 题目列表
            start_index: 起始索引
            constraints: 约束

        Returns:
            单日调度
        """
        selected_problems = []
        time_used = 0
        difficulty_dist = {"easy": 0, "medium": 0, "hard": 0}
        tag_dist = defaultdict(int)

        index = start_index
        while (index < len(problems) and
               len(selected_problems) < constraints.max_problems_per_day and
               time_used < constraints.daily_time_budget):

            problem = problems[index]
            estimated_time = problem["estimated_time"]

            # 检查 hard 题约束
            if problem["difficulty"] == "hard" and difficulty_dist["hard"] >= constraints.max_hard_per_day:
                index += 1
                continue

            # 检查时间是否足够
            if time_used + estimated_time <= constraints.daily_time_budget:
                # 创建已调度题目
                scheduled = ScheduledProblem(
                    problem_id=problem["id"],
                    title=problem.get("title", ""),
                    difficulty=problem["difficulty"],
                    tags=problem.get("tags", []),
                    estimated_time=problem.get("base_time", estimated_time),
                    actual_allocated_time=estimated_time,
                    priority_score=problem.get("priority", 0.5),
                    reason=self._generate_reason(problem, day_index)
                )

                selected_problems.append(scheduled)
                time_used += estimated_time
                difficulty_dist[problem["difficulty"]] += 1

                # 更新标签分布
                for tag in problem.get("tags", []):
                    tag_dist[tag] += 1

                index += 1
            else:
                # 时间不够，跳到下一题
                index += 1

        # 计算难度方差
        difficulty_variance = self._calculate_difficulty_variance(selected_problems)

        return DailySchedule(
            day_index=day_index,
            problems=selected_problems,
            total_time=time_used,
            difficulty_distribution=difficulty_dist,
            tag_distribution=dict(tag_dist),
            difficulty_variance=difficulty_variance
        )

    def _balance_difficulty(
        self,
        daily_schedules: List[DailySchedule],
        constraints: ScheduleConstraints
    ) -> List[DailySchedule]:
        """
        难度平衡调整

        目标：让每天的难度分布更均匀，避免某一天过难或过易

        策略：
        - 识别难度方差过大的天
        - 尝试与相邻天交换题目

        Args:
            daily_schedules: 原始调度
            constraints: 约束

        Returns:
            平衡后的调度
        """
        # 简化版实现：检查并报告方差过大的天
        for schedule in daily_schedules:
            if schedule.difficulty_variance > constraints.difficulty_variance_threshold:
                # 可以在这里实现交换逻辑
                # 为了简化，这里只标记
                pass

        return daily_schedules

    def _optimize_tag_coherence(
        self,
        daily_schedules: List[DailySchedule],
        preferred_tags: List[str]
    ) -> List[DailySchedule]:
        """
        标签连贯性优化

        目标：相关标签的题目安排在相邻的天，减少上下文切换

        Args:
            daily_schedules: 原始调度
            preferred_tags: 优先标签

        Returns:
            优化后的调度
        """
        # 简化版：保持现状，后续可以实现更复杂的优化
        return daily_schedules

    def _calculate_difficulty_variance(
        self,
        problems: List[ScheduledProblem]
    ) -> float:
        """
        计算题目难度方差

        Args:
            problems: 题目列表

        Returns:
            难度方差
        """
        if len(problems) <= 1:
            return 0.0

        difficulty_values = [
            self.DIFFICULTY_VALUES[p.difficulty]
            for p in problems
        ]

        return statistics.variance(difficulty_values)

    def _calculate_fatigue(
        self,
        day_schedule: DailySchedule
    ) -> float:
        """
        计算疲劳度分数

        疲劳度模型：
        fatigue = base_fatigue + difficulty_factor + consecutive_factor

        Args:
            day_schedule: 单日调度

        Returns:
            疲劳度分数 (0-1)
        """
        if not day_schedule.problems:
            return 0.0

        # 基础疲劳度（时间因素）
        time_ratio = day_schedule.total_time / 120.0  # 假设120分钟为满负荷
        base_fatigue = min(1.0, time_ratio)

        # 难度因素
        hard_count = day_schedule.difficulty_distribution.get("hard", 0)
        medium_count = day_schedule.difficulty_distribution.get("medium", 0)
        difficulty_factor = (hard_count * 0.3 + medium_count * 0.1)

        # 连续相同难度题目惩罚（简化）
        consecutive_penalty = 0.0

        total_fatigue = base_fatigue + difficulty_factor + consecutive_penalty

        return min(1.0, total_fatigue)

    def _generate_reason(
        self,
        problem: Dict,
        day_index: int
    ) -> str:
        """
        生成选择题目的原因

        Args:
            problem: 题目信息
            day_index: 天索引

        Returns:
            原因描述
        """
        reasons = []

        # 优先级高
        if problem.get("priority", 0) > 0.8:
            reasons.append("高优先级")

        # 高频题
        if problem.get("frequency", 0) > 0.85:
            reasons.append("高频题")

        # 基础题（第一天）
        if day_index == 0 and problem["difficulty"] == "easy":
            reasons.append("适合热身")

        # 默认原因
        if not reasons:
            reasons.append(f"匹配难度: {problem['difficulty']}")

        return "、".join(reasons)


# 便捷函数
def schedule_problems(
    problems: List[Dict],
    user_skill_level: str,
    daily_time_budget: int,
    total_days: int,
    **kwargs
) -> ScheduleResult:
    """
    快速调度题目的便捷函数

    Args:
        problems: 题目列表
        user_skill_level: 用户技能水平
        daily_time_budget: 每日时间预算
        total_days: 总天数
        **kwargs: 其他参数

    Returns:
        调度结果
    """
    constraints = ScheduleConstraints(daily_time_budget=daily_time_budget)
    scheduler = TaskScheduler()

    return scheduler.schedule(
        problems,
        user_skill_level,
        total_days,
        constraints,
        **kwargs
    )
