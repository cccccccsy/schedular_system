"""
推荐系统 - 难度智能匹配器

根据用户的历史表现和技能水平，智能匹配适合的题目难度。

核心思想：
1. 分析用户在各难度的表现（通过率、用时）
2. 识别用户的"舒适区"和"挑战区"
3. 动态调整推荐难度，实现循序渐进的进步

难度进阶策略：
- Zone of Proximal Development (ZPD) 理论
- 80/20 原则：80% 舒适区 + 20% 挑战区
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import math


@dataclass
class AttemptRecord:
    """尝试记录"""
    problem_id: str
    difficulty: str
    success: bool  # 是否成功
    time_spent: int  # 花费时间（分钟）
    attempts: int  # 尝试次数
    hints_used: int  # 使用提示次数
    timestamp: float  # 时间戳


@dataclass
class DifficultyProfile:
    """用户在某个难度的表现概况"""
    difficulty: str
    total_attempts: int
    success_count: int
    success_rate: float
    avg_time: float
    avg_attempts: float
    recent_performance: float  # 最近表现（用于检测进步）
    confidence_level: float  # 置信度（数据量影响）


@dataclass
class DifficultyRecommendation:
    """难度推荐结果"""
    recommended_difficulty: str
    difficulty_distribution: Dict[str, float]  # 建议的难度分布
    reasoning: str
    next_milestone: str  # 下一个里程碑
    should_challenge: bool  # 是否应该尝试更难的题目


class DifficultyMatcher:
    """难度智能匹配器"""

    # 难度数值映射
    DIFFICULTY_VALUES = {
        "easy": 1.0,
        "medium": 2.0,
        "hard": 3.0
    }

    # 各难度的基准时间（分钟）
    BASELINE_TIME = {
        "easy": 15,
        "medium": 30,
        "hard": 50
    }

    # 各难度的基准通过率
    BASELINE_SUCCESS_RATE = {
        "easy": 0.85,
        "medium": 0.65,
        "hard": 0.45
    }

    def __init__(
        self,
        comfort_zone_ratio: float = 0.7,
        challenge_zone_ratio: float = 0.3,
        min_samples_for_confidence: int = 5,
        recency_weight: float = 0.3
    ):
        """
        初始化难度匹配器

        Args:
            comfort_zone_ratio: 舒适区题目比例
            challenge_zone_ratio: 挑战区题目比例
            min_samples_for_confidence: 达到置信度所需的最小样本数
            recency_weight: 近期表现权重
        """
        self.comfort_zone_ratio = comfort_zone_ratio
        self.challenge_zone_ratio = challenge_zone_ratio
        self.min_samples_for_confidence = min_samples_for_confidence
        self.recency_weight = recency_weight

    def analyze_user_profile(
        self,
        attempt_records: List[AttemptRecord]
    ) -> Dict[str, DifficultyProfile]:
        """
        分析用户在各难度的表现

        Args:
            attempt_records: 历史尝试记录

        Returns:
            各难度的表现概况
        """
        profiles = {}

        # 按难度分组
        records_by_difficulty = defaultdict(list)
        for record in attempt_records:
            records_by_difficulty[record.difficulty].append(record)

        for difficulty in ["easy", "medium", "hard"]:
            records = records_by_difficulty[difficulty]

            if not records:
                # 没有数据，使用基准值
                profiles[difficulty] = DifficultyProfile(
                    difficulty=difficulty,
                    total_attempts=0,
                    success_count=0,
                    success_rate=self.BASELINE_SUCCESS_RATE[difficulty],
                    avg_time=self.BASELINE_TIME[difficulty],
                    avg_attempts=1.5,
                    recent_performance=0.5,
                    confidence_level=0.0
                )
                continue

            # 计算统计数据
            total_attempts = len(records)
            success_count = sum(1 for r in records if r.success)
            success_rate = success_count / total_attempts
            avg_time = sum(r.time_spent for r in records) / total_attempts
            avg_attempts = sum(r.attempts for r in records) / total_attempts

            # 计算近期表现（最近5次）
            recent_records = sorted(records, key=lambda x: x.timestamp, reverse=True)[:5]
            recent_success = sum(1 for r in recent_records if r.success) / len(recent_records)

            # 计算置信度
            confidence = min(1.0, total_attempts / self.min_samples_for_confidence)

            profiles[difficulty] = DifficultyProfile(
                difficulty=difficulty,
                total_attempts=total_attempts,
                success_count=success_count,
                success_rate=success_rate,
                avg_time=avg_time,
                avg_attempts=avg_attempts,
                recent_performance=recent_success,
                confidence_level=confidence
            )

        return profiles

    def recommend_difficulty(
        self,
        user_skill_level: str,
        attempt_records: List[AttemptRecord],
        target_growth_rate: float = 0.2
    ) -> DifficultyRecommendation:
        """
        推荐难度

        Args:
            user_skill_level: 用户声明的技能水平
            attempt_records: 历史尝试记录
            target_growth_rate: 目标进步率

        Returns:
            难度推荐结果
        """
        # 分析用户表现
        profiles = self.analyze_user_profile(attempt_records)

        # 确定当前水平
        current_level = self._determine_current_level(profiles, user_skill_level)

        # 计算推荐的难度分布
        difficulty_distribution = self._calculate_difficulty_distribution(
            profiles, current_level, target_growth_rate
        )

        # 判断是否应该挑战
        should_challenge = self._should_challenge(profiles, current_level)

        # 确定主推荐难度
        recommended_difficulty = max(
            difficulty_distribution.keys(),
            key=lambda d: difficulty_distribution[d]
        )

        # 生成推理说明
        reasoning = self._generate_reasoning(profiles, current_level, should_challenge)

        # 确定下一个里程碑
        next_milestone = self._determine_next_milestone(profiles, current_level)

        return DifficultyRecommendation(
            recommended_difficulty=recommended_difficulty,
            difficulty_distribution=difficulty_distribution,
            reasoning=reasoning,
            next_milestone=next_milestone,
            should_challenge=should_challenge
        )

    def _determine_current_level(
        self,
        profiles: Dict[str, DifficultyProfile],
        declared_level: str
    ) -> str:
        """
        确定用户当前的实际水平

        结合声明水平和实际表现
        """
        # 如果没有足够数据，使用声明水平
        total_confidence = sum(p.confidence_level for p in profiles.values())
        if total_confidence < 1.0:
            return declared_level

        # 基于表现确定水平
        # 如果在某个难度的通过率 > 70%，认为已掌握
        mastered_levels = []
        for difficulty in ["easy", "medium", "hard"]:
            profile = profiles[difficulty]
            if (profile.confidence_level > 0.5 and
                profile.success_rate > 0.7):
                mastered_levels.append(difficulty)

        if "hard" in mastered_levels:
            return "advanced"
        elif "medium" in mastered_levels:
            return "intermediate"
        else:
            return "beginner"

    def _calculate_difficulty_distribution(
        self,
        profiles: Dict[str, DifficultyProfile],
        current_level: str,
        target_growth_rate: float
    ) -> Dict[str, float]:
        """
        计算推荐的难度分布

        使用 ZPD 理论：大部分在舒适区，小部分在挑战区
        """
        # 基于当前水平的默认分布
        base_distributions = {
            "beginner": {"easy": 0.6, "medium": 0.35, "hard": 0.05},
            "intermediate": {"easy": 0.2, "medium": 0.6, "hard": 0.2},
            "advanced": {"easy": 0.1, "medium": 0.4, "hard": 0.5}
        }

        distribution = base_distributions.get(
            current_level,
            {"easy": 0.33, "medium": 0.34, "hard": 0.33}
        ).copy()

        # 根据实际表现调整
        for difficulty in ["easy", "medium", "hard"]:
            profile = profiles[difficulty]

            if profile.confidence_level > 0.5:
                # 如果通过率过高，减少该难度的比例
                if profile.success_rate > 0.85:
                    adjustment = -0.1 * profile.confidence_level
                    distribution[difficulty] = max(0.05, distribution[difficulty] + adjustment)

                    # 增加更高难度的比例
                    next_difficulty = self._next_difficulty(difficulty)
                    if next_difficulty:
                        distribution[next_difficulty] = min(0.7, distribution[next_difficulty] - adjustment)

                # 如果通过率过低，减少该难度的比例
                elif profile.success_rate < 0.4:
                    adjustment = -0.1 * profile.confidence_level
                    distribution[difficulty] = max(0.05, distribution[difficulty] + adjustment)

                    # 增加更低难度的比例
                    prev_difficulty = self._prev_difficulty(difficulty)
                    if prev_difficulty:
                        distribution[prev_difficulty] = min(0.7, distribution[prev_difficulty] - adjustment)

        # 归一化
        total = sum(distribution.values())
        if total > 0:
            distribution = {k: v / total for k, v in distribution.items()}

        return distribution

    def _should_challenge(
        self,
        profiles: Dict[str, DifficultyProfile],
        current_level: str
    ) -> bool:
        """
        判断是否应该尝试更高难度

        条件：
        1. 当前主力难度通过率 > 80%
        2. 近期表现持续上升
        3. 平均尝试次数 < 1.5
        """
        main_difficulty = {
            "beginner": "easy",
            "intermediate": "medium",
            "advanced": "hard"
        }.get(current_level, "medium")

        profile = profiles[main_difficulty]

        # 检查各项条件
        high_success_rate = profile.success_rate > 0.8
        improving = profile.recent_performance > profile.success_rate
        efficient = profile.avg_attempts < 1.5

        return high_success_rate and (improving or efficient)

    def _generate_reasoning(
        self,
        profiles: Dict[str, DifficultyProfile],
        current_level: str,
        should_challenge: bool
    ) -> str:
        """
        生成推理说明
        """
        parts = []

        # 添加当前水平描述
        level_descriptions = {
            "beginner": "初学者阶段",
            "intermediate": "进阶阶段",
            "advanced": "高手阶段"
        }
        parts.append(f"当前处于{level_descriptions.get(current_level, '学习阶段')}")

        # 添加表现分析
        main_difficulty = {
            "beginner": "easy",
            "intermediate": "medium",
            "advanced": "hard"
        }.get(current_level, "medium")

        profile = profiles[main_difficulty]
        if profile.confidence_level > 0.5:
            parts.append(f"在 {main_difficulty} 难度的通过率为 {profile.success_rate:.0%}")

        # 添加建议
        if should_challenge:
            parts.append("建议尝试更高难度的题目以加快进步")
        else:
            parts.append("建议巩固当前难度，打好基础")

        return "。".join(parts) + "。"

    def _determine_next_milestone(
        self,
        profiles: Dict[str, DifficultyProfile],
        current_level: str
    ) -> str:
        """
        确定下一个里程碑
        """
        milestones = {
            "beginner": {
                "easy": "完成 10 道 Easy 题目，通过率 > 80%",
                "medium": "尝试第一道 Medium 题目"
            },
            "intermediate": {
                "medium": "完成 20 道 Medium 题目，通过率 > 70%",
                "hard": "尝试第一道 Hard 题目"
            },
            "advanced": {
                "hard": "完成 10 道 Hard 题目，通过率 > 60%",
                "medium": "Medium 题目一次通过率 > 85%"
            }
        }

        level_milestones = milestones.get(current_level, {})

        # 根据当前表现选择合适的里程碑
        for difficulty, milestone in level_milestones.items():
            profile = profiles.get(difficulty)
            if profile and profile.confidence_level < 1.0:
                return milestone

        return "继续保持，挑战更多题目！"

    def _next_difficulty(self, difficulty: str) -> Optional[str]:
        """获取下一个难度等级"""
        mapping = {"easy": "medium", "medium": "hard"}
        return mapping.get(difficulty)

    def _prev_difficulty(self, difficulty: str) -> Optional[str]:
        """获取上一个难度等级"""
        mapping = {"medium": "easy", "hard": "medium"}
        return mapping.get(difficulty)

    def match_problems(
        self,
        problems: List[Dict],
        difficulty_recommendation: DifficultyRecommendation,
        target_count: int = 10
    ) -> List[Dict]:
        """
        根据难度推荐匹配题目

        Args:
            problems: 候选题目列表
            difficulty_recommendation: 难度推荐结果
            target_count: 目标题目数量

        Returns:
            匹配的题目列表
        """
        # 按难度分组
        problems_by_difficulty = defaultdict(list)
        for problem in problems:
            problems_by_difficulty[problem["difficulty"]].append(problem)

        # 按分布选择题目
        selected = []
        for difficulty, ratio in difficulty_recommendation.difficulty_distribution.items():
            count = int(target_count * ratio)
            available = problems_by_difficulty[difficulty]

            # 按 frequency 排序选择
            sorted_problems = sorted(
                available,
                key=lambda p: p.get("frequency", 0.5),
                reverse=True
            )

            selected.extend(sorted_problems[:count])

        # 如果数量不够，从主推荐难度补充
        if len(selected) < target_count:
            main_difficulty = difficulty_recommendation.recommended_difficulty
            remaining_count = target_count - len(selected)
            selected_ids = {p["id"] for p in selected}

            for problem in problems_by_difficulty[main_difficulty]:
                if problem["id"] not in selected_ids and len(selected) < target_count:
                    selected.append(problem)

        return selected


def create_attempt_record(
    problem_id: str,
    difficulty: str,
    success: bool,
    time_spent: int,
    attempts: int = 1,
    hints_used: int = 0,
    timestamp: float = None
) -> AttemptRecord:
    """
    创建尝试记录

    Args:
        problem_id: 题目ID
        difficulty: 难度
        success: 是否成功
        time_spent: 花费时间
        attempts: 尝试次数
        hints_used: 使用提示次数
        timestamp: 时间戳

    Returns:
        AttemptRecord 对象
    """
    import time
    return AttemptRecord(
        problem_id=problem_id,
        difficulty=difficulty,
        success=success,
        time_spent=time_spent,
        attempts=attempts,
        hints_used=hints_used,
        timestamp=timestamp or time.time()
    )


# 便捷函数
def get_difficulty_recommendation(
    user_skill_level: str,
    attempt_history: List[Dict]
) -> Dict:
    """
    获取难度推荐的便捷函数

    Args:
        user_skill_level: 用户技能水平
        attempt_history: 尝试历史（字典列表）

    Returns:
        推荐结果字典
    """
    # 转换历史记录
    records = [
        AttemptRecord(
            problem_id=h["problem_id"],
            difficulty=h["difficulty"],
            success=h["success"],
            time_spent=h.get("time_spent", 30),
            attempts=h.get("attempts", 1),
            hints_used=h.get("hints_used", 0),
            timestamp=h.get("timestamp", 0)
        )
        for h in attempt_history
    ]

    # 获取推荐
    matcher = DifficultyMatcher()
    recommendation = matcher.recommend_difficulty(user_skill_level, records)

    return {
        "recommended_difficulty": recommendation.recommended_difficulty,
        "difficulty_distribution": recommendation.difficulty_distribution,
        "reasoning": recommendation.reasoning,
        "next_milestone": recommendation.next_milestone,
        "should_challenge": recommendation.should_challenge
    }

