"""
动态规划 - DP优化器

最大化学习价值，优化题目选择和顺序。

问题建模：
- 目标：在时间约束下，最大化学习价值和标签覆盖度
- 状态：dp[day][time_used][tags_covered] = max_value
- 转移：选择或不选择当前题目

价值函数：
value = difficulty_gain + tag_coverage + frequency_bonus - time_cost

算法复杂度：
- 完整DP：O(n * t * 2^k)，n=题目数，t=总时间，k=标签数
- 优化版本：O(n * t)，使用贪心 + 局部优化
"""
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
import math


@dataclass
class LearningGoals:
    """学习目标"""
    target_tags: List[str]  # 目标标签
    target_companies: List[str]  # 目标公司
    min_tag_coverage: float = 0.7  # 最小标签覆盖率
    difficulty_preference: Dict[str, float] = field(default_factory=dict)  # 难度偏好


@dataclass
class Problem:
    """题目数据"""
    id: str
    title: str
    difficulty: str
    tags: List[str]
    estimated_time: int
    frequency: float
    priority: float
    companies: List[str]


@dataclass
class OptimizationResult:
    """优化结果"""
    selected_problems: List[Problem]
    total_value: float
    total_time: int
    tag_coverage: Dict[str, float]  # 每个标签的覆盖率
    difficulty_distribution: Dict[str, int]
    optimization_method: str
    metadata: Dict


class DPOptimizer:
    """DP优化器"""

    # 难度权重
    DIFFICULTY_WEIGHTS = {
        "easy": 1.0,
        "medium": 1.5,
        "hard": 2.0
    }

    def __init__(
        self,
        value_weights: Optional[Dict[str, float]] = None
    ):
        """
        初始化DP优化器

        Args:
            value_weights: 价值函数权重配置
        """
        self.value_weights = value_weights or {
            "difficulty": 0.25,
            "tag_coverage": 0.35,
            "frequency": 0.25,
            "time_efficiency": 0.15
        }

    def optimize_selection(
        self,
        problems: List[Problem],
        time_budget: int,
        learning_goals: LearningGoals
    ) -> OptimizationResult:
        """
        优化题目选择

        使用贪心 + 价值函数的方法，在时间约束下最大化学习价值

        Args:
            problems: 题目列表
            time_budget: 时间预算（分钟）
            learning_goals: 学习目标

        Returns:
            优化结果
        """
        if not problems or time_budget <= 0:
            return OptimizationResult(
                selected_problems=[],
                total_value=0.0,
                total_time=0,
                tag_coverage={},
                difficulty_distribution={},
                optimization_method="greedy_value_based",
                metadata={}
            )

        # Step 1: 计算每道题的价值
        problem_values = []
        for problem in problems:
            value = self._calculate_problem_value(problem, learning_goals)
            problem_values.append((problem, value))

        # Step 2: 按价值密度（value per time）排序
        problem_values.sort(
            key=lambda x: x[1] / max(x[0].estimated_time, 1),
            reverse=True
        )

        # Step 3: 贪心选择（类似背包问题）
        selected_problems = []
        total_time = 0
        total_value = 0.0
        covered_tags = set()

        for problem, value in problem_values:
            if total_time + problem.estimated_time <= time_budget:
                selected_problems.append(problem)
                total_time += problem.estimated_time
                total_value += value
                covered_tags.update(problem.tags)

        # Step 4: 局部优化 - 尝试替换以提高价值
        selected_problems = self._local_optimization(
            selected_problems,
            problem_values,
            time_budget,
            learning_goals
        )

        # 重新计算统计数据
        total_time = sum(p.estimated_time for p in selected_problems)
        total_value = sum(self._calculate_problem_value(p, learning_goals) for p in selected_problems)
        tag_coverage = self._calculate_tag_coverage(selected_problems, learning_goals)
        difficulty_dist = self._calculate_difficulty_distribution(selected_problems)

        return OptimizationResult(
            selected_problems=selected_problems,
            total_value=total_value,
            total_time=total_time,
            tag_coverage=tag_coverage,
            difficulty_distribution=difficulty_dist,
            optimization_method="greedy_with_local_optimization",
            metadata={
                "time_budget": time_budget,
                "time_utilization": total_time / time_budget if time_budget > 0 else 0,
                "problems_selected": len(selected_problems),
                "problems_available": len(problems),
                "selection_rate": len(selected_problems) / len(problems) if problems else 0
            }
        )

    def optimize_with_dp(
        self,
        problems: List[Problem],
        time_budget: int,
        learning_goals: LearningGoals,
        max_problems: int = 100
    ) -> OptimizationResult:
        """
        使用动态规划优化（简化版）

        适用于题目数量较少的情况（< 100）

        状态：dp[i][t] = 前i道题，用时t的最大价值
        转移：dp[i][t] = max(dp[i-1][t], dp[i-1][t-time_i] + value_i)

        Args:
            problems: 题目列表
            time_budget: 时间预算
            learning_goals: 学习目标
            max_problems: 最大题目数（超过则使用贪心）

        Returns:
            优化结果
        """
        # 如果题目太多，回退到贪心算法
        if len(problems) > max_problems:
            return self.optimize_selection(problems, time_budget, learning_goals)

        # 计算每道题的价值
        problem_values = [(p, self._calculate_problem_value(p, learning_goals)) for p in problems]

        # DP数组：dp[i][t] = (max_value, selected_problems_indices)
        n = len(problems)
        dp = [[(-math.inf, []) for _ in range(time_budget + 1)] for _ in range(n + 1)]

        # 初始化
        for t in range(time_budget + 1):
            dp[0][t] = (0.0, [])

        # 填充DP表
        for i in range(1, n + 1):
            problem, value = problem_values[i - 1]
            time_needed = problem.estimated_time

            for t in range(time_budget + 1):
                # 不选择当前题目
                dp[i][t] = dp[i - 1][t]

                # 选择当前题目
                if t >= time_needed:
                    prev_value, prev_indices = dp[i - 1][t - time_needed]
                    new_value = prev_value + value

                    if new_value > dp[i][t][0]:
                        dp[i][t] = (new_value, prev_indices + [i - 1])

        # 回溯找到选中的题目
        total_value, selected_indices = dp[n][time_budget]
        selected_problems = [problems[idx] for idx in selected_indices]

        # 计算统计数据
        total_time = sum(p.estimated_time for p in selected_problems)
        tag_coverage = self._calculate_tag_coverage(selected_problems, learning_goals)
        difficulty_dist = self._calculate_difficulty_distribution(selected_problems)

        return OptimizationResult(
            selected_problems=selected_problems,
            total_value=total_value,
            total_time=total_time,
            tag_coverage=tag_coverage,
            difficulty_distribution=difficulty_dist,
            optimization_method="dynamic_programming",
            metadata={
                "dp_state_size": n * time_budget,
                "time_budget": time_budget,
                "time_utilization": total_time / time_budget if time_budget > 0 else 0
            }
        )

    def _calculate_problem_value(
        self,
        problem: Problem,
        learning_goals: LearningGoals
    ) -> float:
        """
        计算题目价值

        考虑因素：
        - 难度适配度
        - 标签相关度
        - 频率权重
        - 时间效率

        Returns:
            价值分数
        """
        # 1. 难度得分
        difficulty_score = self.DIFFICULTY_WEIGHTS[problem.difficulty]
        if learning_goals.difficulty_preference:
            pref = learning_goals.difficulty_preference.get(problem.difficulty, 1.0)
            difficulty_score *= pref

        # 2. 标签覆盖得分
        tag_overlap = len(set(problem.tags) & set(learning_goals.target_tags))
        tag_score = tag_overlap / max(len(learning_goals.target_tags), 1) if learning_goals.target_tags else 0.5

        # 3. 频率得分
        frequency_score = problem.frequency

        # 4. 时间效率得分（短时间高价值）
        time_efficiency = 1.0 / math.sqrt(max(problem.estimated_time, 1))

        # 公司加成
        company_bonus = 0.0
        if learning_goals.target_companies:
            company_overlap = len(set(problem.companies) & set(learning_goals.target_companies))
            company_bonus = company_overlap * 0.1

        # 加权求和
        value = (
            self.value_weights["difficulty"] * difficulty_score +
            self.value_weights["tag_coverage"] * tag_score +
            self.value_weights["frequency"] * frequency_score +
            self.value_weights["time_efficiency"] * time_efficiency +
            company_bonus
        )

        return value

    def _local_optimization(
        self,
        selected_problems: List[Problem],
        all_problem_values: List[Tuple[Problem, float]],
        time_budget: int,
        learning_goals: LearningGoals,
        max_iterations: int = 10
    ) -> List[Problem]:
        """
        局部优化：尝试替换题目以提高总价值

        策略：
        - 尝试用高价值密度的题目替换低价值密度的题目
        - 确保不超过时间预算
        - 最多迭代 max_iterations 次

        Args:
            selected_problems: 已选择的题目
            all_problem_values: 所有题目及其价值
            time_budget: 时间预算
            learning_goals: 学习目标
            max_iterations: 最大迭代次数

        Returns:
            优化后的题目列表
        """
        selected_ids = set(p.id for p in selected_problems)
        unselected = [(p, v) for p, v in all_problem_values if p.id not in selected_ids]

        improved = True
        iteration = 0

        while improved and iteration < max_iterations:
            improved = False
            iteration += 1

            # 尝试每一个未选中的题目
            for candidate_problem, candidate_value in unselected:
                candidate_density = candidate_value / max(candidate_problem.estimated_time, 1)

                # 尝试替换每一个已选中的题目
                for i, current_problem in enumerate(selected_problems):
                    current_value = self._calculate_problem_value(current_problem, learning_goals)
                    current_density = current_value / max(current_problem.estimated_time, 1)

                    # 如果候选题目的价值密度更高，且替换后不超时
                    time_diff = candidate_problem.estimated_time - current_problem.estimated_time
                    current_total_time = sum(p.estimated_time for p in selected_problems)

                    if (candidate_density > current_density * 1.1 and
                        current_total_time + time_diff <= time_budget):

                        # 执行替换
                        selected_problems[i] = candidate_problem
                        selected_ids.remove(current_problem.id)
                        selected_ids.add(candidate_problem.id)

                        # 更新未选列表
                        unselected = [(p, v) for p, v in all_problem_values if p.id not in selected_ids]

                        improved = True
                        break

                if improved:
                    break

        return selected_problems

    def _calculate_tag_coverage(
        self,
        problems: List[Problem],
        learning_goals: LearningGoals
    ) -> Dict[str, float]:
        """
        计算标签覆盖率

        Args:
            problems: 题目列表
            learning_goals: 学习目标

        Returns:
            标签覆盖率字典 {tag: coverage_rate}
        """
        if not learning_goals.target_tags:
            return {}

        # 统计每个目标标签出现的次数
        tag_counts = {tag: 0 for tag in learning_goals.target_tags}
        for problem in problems:
            for tag in problem.tags:
                if tag in tag_counts:
                    tag_counts[tag] += 1

        # 计算覆盖率（至少出现一次算覆盖）
        max_count = max(tag_counts.values()) if tag_counts.values() else 1
        tag_coverage = {
            tag: min(1.0, count / max(max_count, 1))
            for tag, count in tag_counts.items()
        }

        return tag_coverage

    def _calculate_difficulty_distribution(
        self,
        problems: List[Problem]
    ) -> Dict[str, int]:
        """
        计算难度分布

        Args:
            problems: 题目列表

        Returns:
            难度分布 {difficulty: count}
        """
        distribution = {"easy": 0, "medium": 0, "hard": 0}
        for problem in problems:
            distribution[problem.difficulty] += 1
        return distribution


def create_problem_from_dict(problem_dict: Dict) -> Problem:
    """
    从字典创建Problem对象

    Args:
        problem_dict: 题目字典

    Returns:
        Problem对象
    """
    return Problem(
        id=problem_dict["id"],
        title=problem_dict.get("title", ""),
        difficulty=problem_dict["difficulty"],
        tags=problem_dict.get("tags", []),
        estimated_time=problem_dict.get("estimated_time", 30),
        frequency=problem_dict.get("frequency", 0.5),
        priority=problem_dict.get("priority", 0.5),
        companies=problem_dict.get("companies", [])
    )


# 便捷函数
def optimize_problem_selection(
    problems: List[Dict],
    time_budget: int,
    target_tags: List[str],
    target_companies: Optional[List[str]] = None,
    use_dp: bool = False
) -> OptimizationResult:
    """
    优化题目选择的便捷函数

    Args:
        problems: 题目字典列表
        time_budget: 时间预算
        target_tags: 目标标签
        target_companies: 目标公司
        use_dp: 是否使用DP算法

    Returns:
        优化结果
    """
    # 转换为Problem对象
    problem_objects = [create_problem_from_dict(p) for p in problems]

    # 创建学习目标
    learning_goals = LearningGoals(
        target_tags=target_tags,
        target_companies=target_companies or []
    )

    # 优化
    optimizer = DPOptimizer()

    if use_dp and len(problem_objects) <= 100:
        return optimizer.optimize_with_dp(problem_objects, time_budget, learning_goals)
    else:
        return optimizer.optimize_selection(problem_objects, time_budget, learning_goals)
