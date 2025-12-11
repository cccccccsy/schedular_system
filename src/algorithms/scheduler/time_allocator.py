"""
调度算法 - 时间分配器

基于题目难度和用户历史数据估算每道题的完成时间。

核心公式：
estimated_time = base_time * difficulty_multiplier * user_factor * tag_factor

其中：
- base_time: 题目标准时间（来自题目数据）
- difficulty_multiplier: 难度系数 {easy: 1.0, medium: 1.5, hard: 2.5}
- user_factor: 用户能力调整系数（基于历史表现）
- tag_factor: 标签熟悉度调整系数
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
import statistics


@dataclass
class UserHistory:
    """用户历史数据"""
    problem_attempts: List['ProblemAttempt']  # 题目尝试记录
    avg_time_by_difficulty: Dict[str, float]  # 各难度平均用时
    avg_time_by_tag: Dict[str, float]  # 各标签平均用时
    overall_avg_time: float  # 总体平均用时


@dataclass
class ProblemAttempt:
    """题目尝试记录"""
    problem_id: str
    difficulty: str
    tags: List[str]
    time_spent: int  # 实际花费时间（分钟）
    success: bool


class TimeAllocator:
    """时间分配器"""

    # 默认难度系数
    DEFAULT_DIFFICULTY_MULTIPLIERS = {
        "easy": 1.0,
        "medium": 1.5,
        "hard": 2.5
    }

    # 默认技能水平时间系数
    DEFAULT_SKILL_MULTIPLIERS = {
        "beginner": 1.3,
        "intermediate": 1.0,
        "advanced": 0.8
    }

    def __init__(
        self,
        difficulty_multipliers: Optional[Dict[str, float]] = None,
        skill_multipliers: Optional[Dict[str, float]] = None
    ):
        """
        初始化时间分配器

        Args:
            difficulty_multipliers: 自定义难度系数
            skill_multipliers: 自定义技能水平系数
        """
        self.difficulty_multipliers = difficulty_multipliers or self.DEFAULT_DIFFICULTY_MULTIPLIERS.copy()
        self.skill_multipliers = skill_multipliers or self.DEFAULT_SKILL_MULTIPLIERS.copy()

    def allocate_time(
        self,
        problem_base_time: int,
        problem_difficulty: str,
        problem_tags: List[str],
        user_skill_level: str,
        user_history: Optional[UserHistory] = None
    ) -> int:
        """
        为单个题目分配时间

        Args:
            problem_base_time: 题目基础时间（分钟）
            problem_difficulty: 题目难度
            problem_tags: 题目标签
            user_skill_level: 用户技能水平
            user_history: 用户历史数据（可选）

        Returns:
            估算时间（分钟）
        """
        # 基础时间
        base_time = problem_base_time

        # 难度系数
        difficulty_mult = self.difficulty_multipliers.get(problem_difficulty, 1.5)

        # 用户技能系数
        skill_mult = self.skill_multipliers.get(user_skill_level, 1.0)

        # 如果有历史数据，计算更精确的用户因子
        if user_history and user_history.problem_attempts:
            user_factor = self._calculate_user_factor(
                problem_difficulty,
                problem_tags,
                user_history
            )
            # 标签熟悉度因子
            tag_factor = self._calculate_tag_factor(problem_tags, user_history)
        else:
            # 无历史数据，使用默认技能系数
            user_factor = skill_mult
            tag_factor = 1.0

        # 计算估算时间
        estimated_time = base_time * difficulty_mult * user_factor * tag_factor

        # 四舍五入到5的倍数（实际刷题通常是5分钟刻度）
        estimated_time = round(estimated_time / 5) * 5

        # 设置合理范围：最少10分钟，最多120分钟
        estimated_time = max(10, min(120, int(estimated_time)))

        return estimated_time

    def _calculate_user_factor(
        self,
        difficulty: str,
        tags: List[str],
        history: UserHistory
    ) -> float:
        """
        计算用户能力因子

        基于用户在相同难度和标签的历史表现

        Returns:
            用户因子 (0.5 - 2.0)
        """
        # 如果有该难度的历史数据
        if difficulty in history.avg_time_by_difficulty:
            # 比较用户实际用时与标准用时的比率
            user_avg_time = history.avg_time_by_difficulty[difficulty]
            overall_avg = history.overall_avg_time

            if overall_avg > 0:
                # 用户用时 / 总体平均用时
                ratio = user_avg_time / overall_avg
                # 限制在合理范围内
                user_factor = max(0.5, min(2.0, ratio))
                return user_factor

        # 无足够数据，返回1.0（中性）
        return 1.0

    def _calculate_tag_factor(
        self,
        tags: List[str],
        history: UserHistory
    ) -> float:
        """
        计算标签熟悉度因子

        如果用户在某些标签上表现好，相关题目预估时间可以减少

        Returns:
            标签因子 (0.7 - 1.3)
        """
        if not tags or not history.avg_time_by_tag:
            return 1.0

        # 找到用户在这些标签上的平均表现
        relevant_tag_times = []
        for tag in tags:
            if tag in history.avg_time_by_tag:
                relevant_tag_times.append(history.avg_time_by_tag[tag])

        if not relevant_tag_times:
            return 1.0

        # 计算这些标签的平均用时
        avg_tag_time = statistics.mean(relevant_tag_times)

        # 与整体平均对比
        if history.overall_avg_time > 0:
            ratio = avg_tag_time / history.overall_avg_time
            # 限制在 [0.7, 1.3] 范围
            tag_factor = max(0.7, min(1.3, ratio))
            return tag_factor

        return 1.0

    def allocate_for_day(
        self,
        problems_with_base_time: List[tuple],  # [(problem_id, base_time, difficulty, tags), ...]
        user_skill_level: str,
        target_time: int,
        user_history: Optional[UserHistory] = None
    ) -> List[tuple]:
        """
        为一天的题目列表分配时间，并调整以接近目标时间

        Args:
            problems_with_base_time: 题目列表（问题ID、基础时间、难度、标签）
            user_skill_level: 用户技能水平
            target_time: 目标总时间（分钟）
            user_history: 用户历史

        Returns:
            [(problem_id, allocated_time), ...] 列表
        """
        if not problems_with_base_time:
            return []

        # Step 1: 为每道题分配初始时间
        allocations = []
        total_allocated = 0

        for problem_id, base_time, difficulty, tags in problems_with_base_time:
            allocated_time = self.allocate_time(
                base_time,
                difficulty,
                tags,
                user_skill_level,
                user_history
            )
            allocations.append((problem_id, allocated_time))
            total_allocated += allocated_time

        # Step 2: 如果总时间与目标相差较大，进行调整
        if total_allocated > 0:
            adjustment_ratio = target_time / total_allocated

            # 只在差异超过10%时才调整
            if not (0.9 <= adjustment_ratio <= 1.1):
                allocations = [
                    (pid, max(10, int(time * adjustment_ratio)))
                    for pid, time in allocations
                ]

        return allocations

    def estimate_total_time(
        self,
        problems: List[Dict],  # [{id, base_time, difficulty, tags}, ...]
        user_skill_level: str,
        user_history: Optional[UserHistory] = None
    ) -> int:
        """
        估算完成所有题目的总时间

        Args:
            problems: 题目列表
            user_skill_level: 用户技能水平
            user_history: 用户历史

        Returns:
            总时间（分钟）
        """
        total_time = 0

        for problem in problems:
            estimated = self.allocate_time(
                problem["base_time"],
                problem["difficulty"],
                problem.get("tags", []),
                user_skill_level,
                user_history
            )
            total_time += estimated

        return total_time


def build_user_history_from_attempts(
    attempts: List[ProblemAttempt]
) -> UserHistory:
    """
    从题目尝试记录构建用户历史数据

    Args:
        attempts: 题目尝试列表

    Returns:
        用户历史数据
    """
    if not attempts:
        return UserHistory(
            problem_attempts=[],
            avg_time_by_difficulty={},
            avg_time_by_tag={},
            overall_avg_time=0.0
        )

    # 按难度分组
    time_by_difficulty = {"easy": [], "medium": [], "hard": []}
    for attempt in attempts:
        if attempt.difficulty in time_by_difficulty:
            time_by_difficulty[attempt.difficulty].append(attempt.time_spent)

    # 计算各难度平均时间
    avg_time_by_difficulty = {}
    for difficulty, times in time_by_difficulty.items():
        if times:
            avg_time_by_difficulty[difficulty] = statistics.mean(times)

    # 按标签分组
    time_by_tag = {}
    for attempt in attempts:
        for tag in attempt.tags:
            if tag not in time_by_tag:
                time_by_tag[tag] = []
            time_by_tag[tag].append(attempt.time_spent)

    # 计算各标签平均时间
    avg_time_by_tag = {}
    for tag, times in time_by_tag.items():
        if times:
            avg_time_by_tag[tag] = statistics.mean(times)

    # 整体平均时间
    all_times = [a.time_spent for a in attempts]
    overall_avg_time = statistics.mean(all_times) if all_times else 0.0

    return UserHistory(
        problem_attempts=attempts,
        avg_time_by_difficulty=avg_time_by_difficulty,
        avg_time_by_tag=avg_time_by_tag,
        overall_avg_time=overall_avg_time
    )


# 便捷函数
def quick_allocate(
    base_time: int,
    difficulty: str,
    skill_level: str = "intermediate"
) -> int:
    """
    快速分配时间（不考虑历史数据）

    Args:
        base_time: 基础时间
        difficulty: 难度
        skill_level: 技能水平

    Returns:
        估算时间
    """
    allocator = TimeAllocator()
    return allocator.allocate_time(
        base_time,
        difficulty,
        [],
        skill_level,
        None
    )
