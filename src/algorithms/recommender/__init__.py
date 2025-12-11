"""推荐系统模块

提供智能题目推荐功能：
- 基于内容的推荐（标签、难度、公司匹配）
- 难度智能匹配（ZPD理论）
- 历史数据分析（学习曲线、薄弱领域）
"""

from .content_recommender import (
    ContentRecommender,
    UserPreference,
    RecommendationResult,
    create_problem_from_dict,
    recommend_problems
)

from .difficulty_matcher import (
    DifficultyMatcher,
    AttemptRecord,
    DifficultyProfile,
    DifficultyRecommendation,
    create_attempt_record,
    get_difficulty_recommendation
)

from .history_analyzer import (
    HistoryAnalyzer,
    LearningCurve,
    WeakAreaAnalysis,
    StudyPatternAnalysis,
    HistoryAnalysisResult,
    analyze_user_history
)

__all__ = [
    # 内容推荐
    "ContentRecommender",
    "UserPreference",
    "RecommendationResult",
    "create_problem_from_dict",
    "recommend_problems",
    # 难度匹配
    "DifficultyMatcher",
    "AttemptRecord",
    "DifficultyProfile",
    "DifficultyRecommendation",
    "create_attempt_record",
    "get_difficulty_recommendation",
    # 历史分析
    "HistoryAnalyzer",
    "LearningCurve",
    "WeakAreaAnalysis",
    "StudyPatternAnalysis",
    "HistoryAnalysisResult",
    "analyze_user_history",
]
