"""
推荐系统 - 基于内容的推荐器

基于题目特征（标签、难度、公司）和用户偏好进行推荐。

核心思想：
1. 构建题目的特征向量
2. 构建用户偏好向量
3. 计算相似度进行推荐

特征维度：
- 标签 (one-hot 编码)
- 难度 (ordinal 编码)
- 公司频率 (TF-IDF)
- 题目属性 (estimated_time, frequency, acceptance_rate)
"""
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math


@dataclass
class Problem:
    """题目数据"""
    id: str
    title: str
    difficulty: str
    tags: List[str]
    estimated_time: int
    frequency: float
    acceptance_rate: float
    companies: List[str]


@dataclass
class UserPreference:
    """用户偏好"""
    skill_level: str  # beginner, intermediate, advanced
    completed_problems: Set[str]  # 已完成的题目ID
    preferred_tags: List[str]  # 偏好的标签
    weak_tags: List[str]  # 薄弱的标签
    target_companies: List[str]  # 目标公司
    preferred_difficulty: List[str]  # 偏好难度
    avg_solve_time: Dict[str, float]  # 各难度平均用时


@dataclass
class RecommendationResult:
    """推荐结果"""
    problem: Problem
    score: float  # 推荐分数
    reasons: List[str]  # 推荐理由
    similarity_breakdown: Dict[str, float]  # 各维度相似度


class ContentRecommender:
    """基于内容的推荐器"""

    # 难度数值映射
    DIFFICULTY_VALUES = {
        "easy": 1.0,
        "medium": 2.0,
        "hard": 3.0
    }

    # 技能水平到难度的映射
    SKILL_TO_DIFFICULTY = {
        "beginner": ["easy", "medium"],
        "intermediate": ["medium", "hard"],
        "advanced": ["medium", "hard"]
    }

    def __init__(
        self,
        tag_weight: float = 0.35,
        difficulty_weight: float = 0.25,
        company_weight: float = 0.20,
        attribute_weight: float = 0.20
    ):
        """
        初始化推荐器

        Args:
            tag_weight: 标签相似度权重
            difficulty_weight: 难度匹配权重
            company_weight: 公司相关性权重
            attribute_weight: 属性匹配权重
        """
        self.tag_weight = tag_weight
        self.difficulty_weight = difficulty_weight
        self.company_weight = company_weight
        self.attribute_weight = attribute_weight

        # 所有已知的标签和公司（用于构建向量空间）
        self.all_tags: Set[str] = set()
        self.all_companies: Set[str] = set()

        # 标签和公司的IDF值
        self.tag_idf: Dict[str, float] = {}
        self.company_idf: Dict[str, float] = {}

    def fit(self, problems: List[Problem]):
        """
        学习题目特征（构建向量空间）

        Args:
            problems: 题目列表
        """
        # 收集所有标签和公司
        tag_doc_freq = defaultdict(int)
        company_doc_freq = defaultdict(int)

        for problem in problems:
            for tag in problem.tags:
                self.all_tags.add(tag)
                tag_doc_freq[tag] += 1

            for company in problem.companies:
                self.all_companies.add(company)
                company_doc_freq[company] += 1

        # 计算 IDF (Inverse Document Frequency)
        n_docs = len(problems)
        for tag, freq in tag_doc_freq.items():
            self.tag_idf[tag] = math.log(n_docs / (freq + 1)) + 1

        for company, freq in company_doc_freq.items():
            self.company_idf[company] = math.log(n_docs / (freq + 1)) + 1

    def recommend(
        self,
        problems: List[Problem],
        user_preference: UserPreference,
        top_k: int = 10,
        exclude_completed: bool = True,
        diversity_factor: float = 0.2
    ) -> List[RecommendationResult]:
        """
        推荐题目

        Args:
            problems: 候选题目列表
            user_preference: 用户偏好
            top_k: 返回前k个推荐
            exclude_completed: 是否排除已完成的题目
            diversity_factor: 多样性因子（0-1，越高越多样）

        Returns:
            推荐结果列表
        """
        # 过滤已完成的题目
        candidates = problems
        if exclude_completed:
            candidates = [
                p for p in problems
                if p.id not in user_preference.completed_problems
            ]

        if not candidates:
            return []

        # 计算每道题的推荐分数
        scored_problems = []
        for problem in candidates:
            score, breakdown, reasons = self._calculate_recommendation_score(
                problem, user_preference
            )
            scored_problems.append(
                RecommendationResult(
                    problem=problem,
                    score=score,
                    reasons=reasons,
                    similarity_breakdown=breakdown
                )
            )

        # 按分数排序
        scored_problems.sort(key=lambda x: x.score, reverse=True)

        # 应用多样性策略（MMR - Maximal Marginal Relevance）
        if diversity_factor > 0:
            scored_problems = self._apply_diversity(
                scored_problems, diversity_factor, top_k
            )

        return scored_problems[:top_k]

    def _calculate_recommendation_score(
        self,
        problem: Problem,
        user_preference: UserPreference
    ) -> Tuple[float, Dict[str, float], List[str]]:
        """
        计算推荐分数

        Args:
            problem: 题目
            user_preference: 用户偏好

        Returns:
            (总分, 各维度分数, 推荐理由列表)
        """
        reasons = []
        breakdown = {}

        # 1. 标签相似度
        tag_score = self._calculate_tag_similarity(problem, user_preference)
        breakdown["tag"] = tag_score

        # 2. 难度匹配度
        difficulty_score = self._calculate_difficulty_match(problem, user_preference)
        breakdown["difficulty"] = difficulty_score

        # 3. 公司相关性
        company_score = self._calculate_company_relevance(problem, user_preference)
        breakdown["company"] = company_score

        # 4. 属性匹配（时间、频率）
        attribute_score = self._calculate_attribute_match(problem, user_preference)
        breakdown["attribute"] = attribute_score

        # 加权求和
        total_score = (
            self.tag_weight * tag_score +
            self.difficulty_weight * difficulty_score +
            self.company_weight * company_score +
            self.attribute_weight * attribute_score
        )

        # 生成推荐理由
        if tag_score > 0.7:
            matching_tags = set(problem.tags) & set(user_preference.weak_tags)
            if matching_tags:
                reasons.append(f"帮助加强薄弱标签: {', '.join(matching_tags)}")
            else:
                matching_preferred = set(problem.tags) & set(user_preference.preferred_tags)
                if matching_preferred:
                    reasons.append(f"符合你偏好的标签: {', '.join(matching_preferred)}")

        if difficulty_score > 0.8:
            reasons.append(f"难度 {problem.difficulty} 非常适合你当前水平")

        if company_score > 0.6 and user_preference.target_companies:
            matching_companies = set(problem.companies) & set(user_preference.target_companies)
            if matching_companies:
                reasons.append(f"目标公司高频题: {', '.join(matching_companies)}")

        if problem.frequency > 0.85:
            reasons.append("高频面试题")

        if not reasons:
            reasons.append(f"{problem.difficulty.capitalize()} 难度，适合练习")

        return total_score, breakdown, reasons

    def _calculate_tag_similarity(
        self,
        problem: Problem,
        user_preference: UserPreference
    ) -> float:
        """
        计算标签相似度

        优先推荐薄弱标签的题目
        """
        if not problem.tags:
            return 0.5

        problem_tags = set(problem.tags)

        # 薄弱标签匹配（权重最高）
        weak_overlap = problem_tags & set(user_preference.weak_tags)
        weak_score = len(weak_overlap) / max(len(user_preference.weak_tags), 1) if user_preference.weak_tags else 0

        # 偏好标签匹配
        preferred_overlap = problem_tags & set(user_preference.preferred_tags)
        preferred_score = len(preferred_overlap) / max(len(user_preference.preferred_tags), 1) if user_preference.preferred_tags else 0

        # 加权组合：薄弱标签优先
        tag_score = 0.6 * weak_score + 0.4 * preferred_score

        # 如果使用 TF-IDF
        if self.tag_idf:
            tfidf_score = sum(self.tag_idf.get(tag, 1.0) for tag in weak_overlap)
            tfidf_score /= max(sum(self.tag_idf.get(tag, 1.0) for tag in problem_tags), 1)
            tag_score = 0.5 * tag_score + 0.5 * tfidf_score

        return min(1.0, tag_score)

    def _calculate_difficulty_match(
        self,
        problem: Problem,
        user_preference: UserPreference
    ) -> float:
        """
        计算难度匹配度

        考虑用户技能水平和偏好难度
        """
        # 获取推荐难度范围
        recommended_difficulties = self.SKILL_TO_DIFFICULTY.get(
            user_preference.skill_level,
            ["easy", "medium", "hard"]
        )

        # 检查是否在推荐范围内
        if problem.difficulty in recommended_difficulties:
            base_score = 0.8
        else:
            base_score = 0.4

        # 如果用户有明确偏好
        if user_preference.preferred_difficulty:
            if problem.difficulty in user_preference.preferred_difficulty:
                return 1.0
            else:
                # 计算与偏好难度的距离
                problem_value = self.DIFFICULTY_VALUES[problem.difficulty]
                preferred_values = [self.DIFFICULTY_VALUES[d] for d in user_preference.preferred_difficulty]
                min_distance = min(abs(problem_value - pv) for pv in preferred_values)
                distance_penalty = min_distance * 0.2
                return max(0.3, base_score - distance_penalty)

        return base_score

    def _calculate_company_relevance(
        self,
        problem: Problem,
        user_preference: UserPreference
    ) -> float:
        """
        计算公司相关性
        """
        if not user_preference.target_companies or not problem.companies:
            return 0.5

        problem_companies = set(c.lower() for c in problem.companies)
        target_companies = set(c.lower() for c in user_preference.target_companies)

        # 计算重叠
        overlap = problem_companies & target_companies
        if not overlap:
            return 0.3

        # 使用 IDF 加权
        if self.company_idf:
            score = sum(self.company_idf.get(c, 1.0) for c in overlap)
            max_possible = sum(self.company_idf.get(c, 1.0) for c in target_companies)
            return min(1.0, score / max(max_possible, 1))

        # 简单重叠比例
        return len(overlap) / len(target_companies)

    def _calculate_attribute_match(
        self,
        problem: Problem,
        user_preference: UserPreference
    ) -> float:
        """
        计算属性匹配度

        考虑时间、频率、通过率
        """
        scores = []

        # 时间匹配：用户平均用时 vs 题目预估时间
        if user_preference.avg_solve_time:
            avg_time = user_preference.avg_solve_time.get(problem.difficulty, 30)
            time_ratio = problem.estimated_time / max(avg_time, 1)
            # 时间差距越小越好
            time_score = max(0, 1 - abs(time_ratio - 1) * 0.5)
            scores.append(time_score)

        # 频率分数：高频题优先
        frequency_score = problem.frequency
        scores.append(frequency_score)

        # 通过率分数：适中的通过率更好（不要太简单也不要太难）
        # 理想通过率根据技能水平调整
        ideal_acceptance = {
            "beginner": 0.6,
            "intermediate": 0.45,
            "advanced": 0.35
        }
        target_acceptance = ideal_acceptance.get(user_preference.skill_level, 0.45)
        acceptance_diff = abs(problem.acceptance_rate - target_acceptance)
        acceptance_score = max(0, 1 - acceptance_diff * 2)
        scores.append(acceptance_score)

        return sum(scores) / len(scores) if scores else 0.5

    def _apply_diversity(
        self,
        recommendations: List[RecommendationResult],
        diversity_factor: float,
        top_k: int
    ) -> List[RecommendationResult]:
        """
        应用多样性策略（MMR）

        避免推荐过多相似的题目

        Args:
            recommendations: 原始推荐列表
            diversity_factor: 多样性因子
            top_k: 需要的数量

        Returns:
            多样化后的推荐列表
        """
        if len(recommendations) <= top_k:
            return recommendations

        selected = [recommendations[0]]  # 先选最高分的
        remaining = recommendations[1:]

        while len(selected) < top_k and remaining:
            best_idx = 0
            best_score = float('-inf')

            for i, candidate in enumerate(remaining):
                # 计算与已选题目的最大相似度
                max_similarity = max(
                    self._problem_similarity(candidate.problem, s.problem)
                    for s in selected
                )

                # MMR score = λ * relevance - (1 - λ) * max_similarity
                mmr_score = (
                    (1 - diversity_factor) * candidate.score -
                    diversity_factor * max_similarity
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining[best_idx])
            remaining.pop(best_idx)

        return selected

    def _problem_similarity(self, p1: Problem, p2: Problem) -> float:
        """
        计算两道题目的相似度（用于多样性计算）
        """
        # 标签相似度 (Jaccard)
        tags1 = set(p1.tags)
        tags2 = set(p2.tags)
        tag_sim = len(tags1 & tags2) / max(len(tags1 | tags2), 1)

        # 难度相似度
        diff_sim = 1.0 if p1.difficulty == p2.difficulty else 0.0

        # 公司相似度
        companies1 = set(p1.companies)
        companies2 = set(p2.companies)
        company_sim = len(companies1 & companies2) / max(len(companies1 | companies2), 1)

        return 0.5 * tag_sim + 0.3 * diff_sim + 0.2 * company_sim

    def recommend_similar(
        self,
        target_problem: Problem,
        all_problems: List[Problem],
        top_k: int = 5
    ) -> List[Tuple[Problem, float]]:
        """
        推荐与指定题目相似的题目

        适用于"相似题目推荐"功能

        Args:
            target_problem: 目标题目
            all_problems: 所有题目
            top_k: 返回数量

        Returns:
            [(题目, 相似度)] 列表
        """
        similarities = []

        for problem in all_problems:
            if problem.id == target_problem.id:
                continue
            sim = self._problem_similarity(target_problem, problem)
            similarities.append((problem, sim))

        # 按相似度排序
        similarities.sort(key=lambda x: x[1], reverse=True)

        return similarities[:top_k]


def create_problem_from_dict(problem_dict: Dict) -> Problem:
    """
    从字典创建 Problem 对象

    Args:
        problem_dict: 题目字典

    Returns:
        Problem 对象
    """
    return Problem(
        id=problem_dict["id"],
        title=problem_dict.get("title", ""),
        difficulty=problem_dict["difficulty"],
        tags=problem_dict.get("tags", []),
        estimated_time=problem_dict.get("estimated_time", 30),
        frequency=problem_dict.get("frequency", 0.5),
        acceptance_rate=problem_dict.get("acceptance_rate", 0.5),
        companies=problem_dict.get("companies", [])
    )


# 便捷函数
def recommend_problems(
    problems: List[Dict],
    user_skill_level: str,
    completed_problems: Set[str],
    weak_tags: List[str],
    preferred_tags: List[str] = None,
    target_companies: List[str] = None,
    top_k: int = 10
) -> List[Dict]:
    """
    推荐题目的便捷函数

    Args:
        problems: 题目字典列表
        user_skill_level: 用户技能水平
        completed_problems: 已完成的题目ID集合
        weak_tags: 薄弱标签
        preferred_tags: 偏好标签
        target_companies: 目标公司
        top_k: 返回数量

    Returns:
        推荐的题目字典列表
    """
    # 转换为 Problem 对象
    problem_objects = [create_problem_from_dict(p) for p in problems]

    # 创建用户偏好
    user_pref = UserPreference(
        skill_level=user_skill_level,
        completed_problems=completed_problems,
        preferred_tags=preferred_tags or [],
        weak_tags=weak_tags,
        target_companies=target_companies or [],
        preferred_difficulty=["easy", "medium"] if user_skill_level == "beginner" else ["medium", "hard"],
        avg_solve_time={}
    )

    # 创建推荐器并训练
    recommender = ContentRecommender()
    recommender.fit(problem_objects)

    # 获取推荐
    recommendations = recommender.recommend(
        problem_objects,
        user_pref,
        top_k=top_k
    )

    # 转换回字典格式
    return [
        {
            "problem": {
                "id": r.problem.id,
                "title": r.problem.title,
                "difficulty": r.problem.difficulty,
                "tags": r.problem.tags,
                "estimated_time": r.problem.estimated_time,
                "frequency": r.problem.frequency,
                "companies": r.problem.companies
            },
            "score": r.score,
            "reasons": r.reasons
        }
        for r in recommendations
    ]

