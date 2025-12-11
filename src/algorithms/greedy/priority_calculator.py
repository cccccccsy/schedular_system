"""
贪心算法 - 优先级计算器

计算每道题目的优先级分数，用于快速决策和排序。

优先级公式：
priority = w1 * frequency_score        # 高频题权重
         + w2 * difficulty_match       # 难度匹配度
         + w3 * tag_relevance          # 标签相关性
         + w4 * recency_score          # 新鲜度（避免重复刷题）
         - w5 * time_cost_penalty      # 时间成本惩罚
"""
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
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
        "frequency": 0.3,
        "difficulty_match": 0.25,
        "tag_relevance": 0.25,
        "recency": 0.1,
        "time_cost": 0.1
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
        # 如果已经完成，优先级为0
        if problem.id in user_profile.completed_problems:
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
            self.weights["recency"] * recency_score -
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
        - 最近做过的题目会被过滤掉（在 calculate_priority 开头已处理）

        Returns:
            新鲜度分数 (0-1)
        """
        # 如果从未做过，新鲜度满分
        if problem.id not in user_profile.completed_problems:
            return 1.0

        # 已完成的题目在主函数中已经被过滤，这里不应该到达
        return 0.0

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
