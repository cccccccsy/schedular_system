"""
贪心算法 - 优先级计算器

计算每道题目的优先级分数，用于快速决策和排序。

优先级公式：
priority = w1 * frequency_score        # 高频题权重
         + w2 * difficulty_match       # 难度匹配度
         + w3 * tag_relevance          # 标签相关性
         + w4 * recency_score          # 新鲜度（避免重复刷题）
         + w5 * spaced_repetition      # 间隔重复（时间越久越需要复习）
         - w6 * time_cost_penalty      # 时间成本惩罚
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math


@dataclass
class UserProfile:
    """用户画像"""
    skill_level: str  # beginner, intermediate, advanced
    completed_problems: Set[str]  # 已完成题目ID集合
    weak_tags: List[str]  # 薄弱标签
    strong_tags: List[str]  # 擅长标签
    focus_tags: List[str]  # 关注标签
    target_difficulty: List[str]  # 目标难度列表
    # 新增：记录每道题的上次完成时间 {problem_id: datetime}
    problem_last_done: Dict[str, datetime] = field(default_factory=dict)


@dataclass
class Problem:
    """题目数据类"""
    id: str
    title: str
    difficulty: str
    tags: List[str]
    estimated_time: int
    frequency: float
    acceptance_rate: float
    companies: List[str]


class PriorityCalculator:
    """优先级计算器"""

    # 默认权重配置
    DEFAULT_WEIGHTS = {
        "frequency": 0.25,
        "difficulty_match": 0.20,
        "tag_relevance": 0.20,
        "recency": 0.10,
        "spaced_repetition": 0.15,  # 间隔重复权重
        "time_cost": 0.10
    }

    # 间隔重复参数（基于艾宾浩斯遗忘曲线）
    SPACED_REPETITION_CONFIG = {
        "optimal_intervals_days": [1, 3, 7, 14, 30, 60],  # 最佳复习间隔
        "decay_rate": 0.1,  # 遗忘衰减率
        "min_interval_hours": 24,  # 最小间隔（小时），低于此时间不推荐重复
    }

    # 难度数值映射
    DIFFICULTY_VALUES = {
        "easy": 1.0,
        "medium": 2.0,
        "hard": 3.0
    }

    # 技能等级数值映射
    SKILL_LEVEL_VALUES = {
        "beginner": 1.0,
        "intermediate": 2.0,
        "advanced": 3.0
    }

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        初始化优先级计算器

        Args:
            weights: 自定义权重配置，如果为None则使用默认权重
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._validate_weights()

    def _validate_weights(self):
        """验证权重配置"""
        total = sum(self.weights.values())
        if not math.isclose(total, 1.0, rel_tol=0.01):
            # 归一化权重
            for key in self.weights:
                self.weights[key] /= total

    def calculate_priority(
        self,
        problem: Problem,
        user_profile: UserProfile,
        target_companies: Optional[List[str]] = None
    ) -> float:
        """
        计算题目优先级

        Args:
            problem: 题目信息
            user_profile: 用户画像
            target_companies: 目标公司列表（可选）

        Returns:
            优先级分数 (0-1之间)
        """
        # 计算间隔重复分数（已完成的题目也可能需要复习）
        spaced_rep_score, should_skip = self._calculate_spaced_repetition_score(
            problem, user_profile
        )

        # 如果刚做过（间隔太近），跳过
        if should_skip:
            return 0.0

        # 计算各个维度的分数
        frequency_score = self._calculate_frequency_score(problem)
        difficulty_match = self._calculate_difficulty_match(problem, user_profile)
        tag_relevance = self._calculate_tag_relevance(problem, user_profile)
        recency_score = self._calculate_recency_score(problem, user_profile)
        time_cost_penalty = self._calculate_time_cost_penalty(problem)

        # 公司加成
        company_bonus = 0.0
        if target_companies:
            company_bonus = self._calculate_company_bonus(problem, target_companies)

        # 加权求和
        priority = (
            self.weights["frequency"] * frequency_score +
            self.weights["difficulty_match"] * difficulty_match +
            self.weights["tag_relevance"] * tag_relevance +
            self.weights["recency"] * recency_score +
            self.weights["spaced_repetition"] * spaced_rep_score -
            self.weights["time_cost"] * time_cost_penalty +
            company_bonus
        )

        # 确保在[0, 1]范围内
        return max(0.0, min(1.0, priority))

    def _calculate_frequency_score(self, problem: Problem) -> float:
        """
        计算频率分数

        高频题目优先级更高

        Returns:
            频率分数 (0-1)
        """
        # frequency 字段本身就是 0-1 范围的标准化值
        return problem.frequency

    def _calculate_difficulty_match(
        self,
        problem: Problem,
        user_profile: UserProfile
    ) -> float:
        """
        计算难度匹配度

        策略：
        - 用户水平 ± 1 级别的题目匹配度最高
        - 过于简单或过于困难的题目匹配度低

        Returns:
            匹配度分数 (0-1)
        """
        problem_level = self.DIFFICULTY_VALUES[problem.difficulty]
        user_level = self.SKILL_LEVEL_VALUES[user_profile.skill_level]

        # 计算难度差距
        level_diff = abs(problem_level - user_level)

        # 使用高斯函数计算匹配度
        # 差距为0时最高，差距越大匹配度越低
        match_score = math.exp(-0.5 * (level_diff ** 2))

        # 如果题目难度在目标难度列表中，给予额外加成
        if problem.difficulty in user_profile.target_difficulty:
            match_score = min(1.0, match_score * 1.2)

        return match_score

    def _calculate_tag_relevance(
        self,
        problem: Problem,
        user_profile: UserProfile
    ) -> float:
        """
        计算标签相关性

        策略：
        - 薄弱标签：高权重（需要加强）
        - 关注标签：中等权重（学习目标）
        - 擅长标签：低权重（已掌握）

        Returns:
            相关性分数 (0-1)
        """
        if not problem.tags:
            return 0.5  # 无标签，返回中等分数

        problem_tags_set = set(problem.tags)

        # 薄弱标签相关性（权重最高）
        weak_overlap = len(problem_tags_set & set(user_profile.weak_tags))
        weak_score = weak_overlap / max(len(user_profile.weak_tags), 1) if user_profile.weak_tags else 0

        # 关注标签相关性（中等权重）
        focus_overlap = len(problem_tags_set & set(user_profile.focus_tags))
        focus_score = focus_overlap / max(len(user_profile.focus_tags), 1) if user_profile.focus_tags else 0

        # 擅长标签相关性（权重较低，避免重复）
        strong_overlap = len(problem_tags_set & set(user_profile.strong_tags))
        strong_score = strong_overlap / max(len(user_profile.strong_tags), 1) if user_profile.strong_tags else 0

        # 加权组合：薄弱标签权重最高
        relevance = 0.5 * weak_score + 0.3 * focus_score + 0.2 * (1.0 - strong_score)

        return min(1.0, relevance)

    def _calculate_recency_score(
        self,
        problem: Problem,
        user_profile: UserProfile
    ) -> float:
        """
        计算新鲜度分数

        策略：
        - 从未做过的题目：高分
        - 做过的题目根据间隔重复逻辑处理

        Returns:
            新鲜度分数 (0-1)
        """
        # 如果从未做过，新鲜度满分
        if problem.id not in user_profile.problem_last_done:
            return 1.0

        # 做过的题目，新鲜度降低（但间隔重复分数会补偿）
        return 0.3

    def _calculate_spaced_repetition_score(
        self,
        problem: Problem,
        user_profile: UserProfile
    ) -> tuple:
        """
        计算间隔重复分数（基于艾宾浩斯遗忘曲线）

        策略：
        - 刚做过的题目（< 24小时）：跳过，返回 should_skip=True
        - 接近最佳复习时间点：高分
        - 时间间隔越长，遗忘程度越高，需要复习

        Returns:
            (score, should_skip): 分数和是否应该跳过
        """
        # 从未做过的题目，给中等分数（鼓励尝试新题）
        if problem.id not in user_profile.problem_last_done:
            return 0.5, False

        last_done = user_profile.problem_last_done[problem.id]
        now = datetime.now()
        hours_since = (now - last_done).total_seconds() / 3600

        # 如果间隔太近（< 24小时），跳过
        min_interval = self.SPACED_REPETITION_CONFIG["min_interval_hours"]
        if hours_since < min_interval:
            return 0.0, True

        days_since = hours_since / 24
        optimal_intervals = self.SPACED_REPETITION_CONFIG["optimal_intervals_days"]

        # 找到最接近的最佳复习间隔
        score = self._compute_retention_score(days_since, optimal_intervals)

        return score, False

    def _compute_retention_score(
        self,
        days_since: float,
        optimal_intervals: List[int]
    ) -> float:
        """
        计算记忆保留/复习需求分数

        使用修改版艾宾浩斯遗忘曲线：
        - 接近最佳复习时间点时分数最高
        - 超过最长间隔时，遗忘程度高，需要复习

        Args:
            days_since: 距离上次完成的天数
            optimal_intervals: 最佳复习间隔列表

        Returns:
            复习需求分数 (0-1)，分数越高越需要复习
        """
        # 找到当前时间落在哪个复习区间
        for i, interval in enumerate(optimal_intervals):
            if days_since <= interval:
                # 计算到达这个复习点的接近程度
                if i == 0:
                    prev_interval = 0
                else:
                    prev_interval = optimal_intervals[i - 1]

                # 在区间内的位置（0-1）
                position = (days_since - prev_interval) / (interval - prev_interval)

                # 使用高斯函数，在接近复习点时分数最高
                # 最佳复习时间点在区间的 70-90% 位置
                optimal_position = 0.8
                distance = abs(position - optimal_position)
                score = math.exp(-2 * (distance ** 2))

                return score

        # 超过最长间隔，根据遗忘曲线计算
        max_interval = optimal_intervals[-1]
        extra_days = days_since - max_interval

        # 遗忘曲线：R = e^(-t/S)，这里反过来用，时间越长越需要复习
        decay_rate = self.SPACED_REPETITION_CONFIG["decay_rate"]
        forgetting_factor = 1 - math.exp(-decay_rate * extra_days)

        # 遗忘越严重，复习需求越高
        return min(1.0, 0.7 + 0.3 * forgetting_factor)

    def _calculate_time_cost_penalty(self, problem: Problem) -> float:
        """
        计算时间成本惩罚

        时间越长，惩罚越大（在时间有限的情况下）

        Returns:
            惩罚分数 (0-1)
        """
        # 假设最大合理时间为60分钟
        max_time = 60.0

        # 归一化时间成本
        normalized_time = min(problem.estimated_time / max_time, 1.0)

        # 使用平方根使惩罚更平缓
        penalty = math.sqrt(normalized_time)

        return penalty

    def _calculate_company_bonus(
        self,
        problem: Problem,
        target_companies: List[str]
    ) -> float:
        """
        计算公司加成

        如果题目出现在目标公司列表中，给予额外加成

        Returns:
            加成分数 (0-0.2)
        """
        if not problem.companies or not target_companies:
            return 0.0

        problem_companies = set(c.lower() for c in problem.companies)
        target_companies_set = set(c.lower() for c in target_companies)

        # 计算重叠公司数量
        overlap = len(problem_companies & target_companies_set)

        # 加成最多0.2分
        bonus = min(0.2, overlap * 0.1)

        return bonus

    def rank_problems(
        self,
        problems: List[Problem],
        user_profile: UserProfile,
        target_companies: Optional[List[str]] = None,
        top_k: Optional[int] = None
    ) -> List[tuple]:
        """
        对题目列表进行排序

        Args:
            problems: 题目列表
            user_profile: 用户画像
            target_companies: 目标公司列表
            top_k: 返回前k个题目，None表示返回全部

        Returns:
            排序后的 (problem, priority_score) 元组列表
        """
        # 计算每道题的优先级
        scored_problems = []
        for problem in problems:
            score = self.calculate_priority(problem, user_profile, target_companies)
            if score > 0:  # 只保留有效分数的题目
                scored_problems.append((problem, score))

        # 按优先级降序排序
        scored_problems.sort(key=lambda x: x[1], reverse=True)

        # 返回前k个
        if top_k:
            return scored_problems[:top_k]

        return scored_problems

    def adjust_weights(self, **kwargs):
        """
        动态调整权重

        Example:
            calculator.adjust_weights(frequency=0.4, difficulty_match=0.2)
        """
        for key, value in kwargs.items():
            if key in self.weights:
                self.weights[key] = value

        self._validate_weights()


# 便捷函数
def calculate_problem_priority(
    problem: Problem,
    user_profile: UserProfile,
    target_companies: Optional[List[str]] = None
) -> float:
    """
    快速计算单个题目的优先级

    Args:
        problem: 题目信息
        user_profile: 用户画像
        target_companies: 目标公司列表

    Returns:
        优先级分数
    """
    calculator = PriorityCalculator()
    return calculator.calculate_priority(problem, user_profile, target_companies)
