"""推荐系统 API 端点"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from models.database import get_db
from models.user import User
from services.problem_service import get_problem_service, ProblemService
from services.progress_service import get_progress_service, ProgressService

# 导入推荐系统模块
from algorithms.recommender.content_recommender import (
    ContentRecommender, UserPreference, create_problem_from_dict,
    recommend_problems
)
from algorithms.recommender.difficulty_matcher import (
    DifficultyMatcher, get_difficulty_recommendation
)
from algorithms.recommender.history_analyzer import (
    HistoryAnalyzer, analyze_user_history
)


router = APIRouter()


# ========== Pydantic 模型 ==========

class RecommendationRequest(BaseModel):
    """推荐请求"""
    user_id: int
    count: int = Field(default=10, ge=1, le=50, description="推荐数量")
    focus_tags: Optional[List[str]] = Field(default=None, description="关注的标签")
    target_companies: Optional[List[str]] = Field(default=None, description="目标公司")
    exclude_completed: bool = Field(default=True, description="是否排除已完成的题目")
    diversity_factor: float = Field(default=0.2, ge=0, le=1, description="多样性因子")


class RecommendedProblem(BaseModel):
    """推荐的题目"""
    problem_id: str
    title: str
    difficulty: str
    tags: List[str]
    estimated_time: int
    frequency: float
    score: float = Field(..., description="推荐分数")
    reasons: List[str] = Field(..., description="推荐理由")


class RecommendationResponse(BaseModel):
    """推荐响应"""
    recommendations: List[RecommendedProblem]
    total: int
    metadata: dict


class DifficultyRecommendationResponse(BaseModel):
    """难度推荐响应"""
    recommended_difficulty: str
    difficulty_distribution: dict
    reasoning: str
    next_milestone: str
    should_challenge: bool


class HistoryAnalysisResponse(BaseModel):
    """历史分析响应"""
    total_problems: int
    total_time: int
    success_rate: float
    learning_curve: dict
    weak_areas: dict
    study_patterns: dict
    recommendations: List[str]


class FeedbackRequest(BaseModel):
    """推荐反馈请求"""
    user_id: int
    problem_id: str
    feedback_type: str = Field(..., description="反馈类型: helpful, not_helpful, too_easy, too_hard")
    comment: Optional[str] = None


# ========== 依赖注入 ==========

def get_problem_svc() -> ProblemService:
    """获取题目服务"""
    return get_problem_service()


def get_progress_svc() -> ProgressService:
    """获取进度服务"""
    return get_progress_service()


# ========== API 端点 ==========

@router.post("/", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
    problem_service: ProblemService = Depends(get_problem_svc)
):
    """
    获取个性化题目推荐

    基于用户画像、历史数据和学习目标，智能推荐最适合的题目。

    **推荐算法**：
    1. 基于内容的推荐（标签、难度、公司匹配）
    2. 薄弱领域优先
    3. 难度渐进策略
    4. 多样性保证（MMR算法）

    **请求示例**：
    ```json
    {
      "user_id": 1,
      "count": 10,
      "focus_tags": ["array", "dynamic-programming"],
      "target_companies": ["google", "amazon"],
      "diversity_factor": 0.2
    }
    ```

    Args:
        request: 推荐请求
        db: 数据库会话
        problem_service: 题目服务
    """
    # 获取用户信息
    result = await db.execute(select(User).where(User.id == request.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {request.user_id}")

    # 获取所有题目
    all_problems = problem_service.get_all_problems(limit=500)

    if not all_problems:
        raise HTTPException(status_code=404, detail="没有可用的题目")

    # 获取用户已完成的题目
    completed_problems = set()
    if request.exclude_completed:
        # TODO: 从进度表获取
        pass

    # 构建推荐参数
    weak_tags = user.weak_tags or []
    preferred_tags = request.focus_tags or user.strong_tags or []

    # 调用推荐服务
    recommendations = recommend_problems(
        problems=all_problems,
        user_skill_level=user.skill_level,
        completed_problems=completed_problems,
        weak_tags=weak_tags,
        preferred_tags=preferred_tags,
        target_companies=request.target_companies,
        top_k=request.count
    )

    # 构建响应
    recommended_problems = [
        RecommendedProblem(
            problem_id=r["problem"]["id"],
            title=r["problem"]["title"],
            difficulty=r["problem"]["difficulty"],
            tags=r["problem"]["tags"],
            estimated_time=r["problem"]["estimated_time"],
            frequency=r["problem"]["frequency"],
            score=r["score"],
            reasons=r["reasons"]
        )
        for r in recommendations
    ]

    return RecommendationResponse(
        recommendations=recommended_problems,
        total=len(recommended_problems),
        metadata={
            "user_skill_level": user.skill_level,
            "weak_tags": weak_tags,
            "focus_tags": preferred_tags,
            "exclude_completed": request.exclude_completed,
            "diversity_factor": request.diversity_factor
        }
    )


@router.get("/quick", response_model=RecommendationResponse)
async def get_quick_recommendations(
    user_id: int,
    count: int = Query(5, ge=1, le=20, description="推荐数量"),
    difficulty: Optional[str] = Query(None, description="难度过滤"),
    tags: Optional[List[str]] = Query(None, description="标签过滤"),
    db: AsyncSession = Depends(get_db),
    problem_service: ProblemService = Depends(get_problem_svc)
):
    """
    快速推荐（简化版）

    适合快速获取推荐结果，参数更简单。

    Args:
        user_id: 用户ID
        count: 推荐数量
        difficulty: 难度过滤
        tags: 标签过滤
        db: 数据库会话
        problem_service: 题目服务
    """
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    # 获取题目
    all_problems = problem_service.get_all_problems(limit=200)

    # 简单过滤
    if difficulty:
        all_problems = [p for p in all_problems if p["difficulty"] == difficulty]

    if tags:
        all_problems = [
            p for p in all_problems
            if any(t in p.get("tags", []) for t in tags)
        ]

    # 推荐
    recommendations = recommend_problems(
        problems=all_problems,
        user_skill_level=user.skill_level,
        completed_problems=set(),
        weak_tags=user.weak_tags or [],
        preferred_tags=tags or [],
        top_k=count
    )

    recommended_problems = [
        RecommendedProblem(
            problem_id=r["problem"]["id"],
            title=r["problem"]["title"],
            difficulty=r["problem"]["difficulty"],
            tags=r["problem"]["tags"],
            estimated_time=r["problem"]["estimated_time"],
            frequency=r["problem"]["frequency"],
            score=r["score"],
            reasons=r["reasons"]
        )
        for r in recommendations
    ]

    return RecommendationResponse(
        recommendations=recommended_problems,
        total=len(recommended_problems),
        metadata={
            "mode": "quick",
            "filters": {"difficulty": difficulty, "tags": tags}
        }
    )


@router.get("/difficulty/{user_id}", response_model=DifficultyRecommendationResponse)
async def get_difficulty_recommendation_api(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取难度推荐

    分析用户历史表现，推荐最适合的难度分布。

    基于 ZPD（最近发展区）理论：
    - 80% 舒适区题目巩固基础
    - 20% 挑战区题目促进成长

    Args:
        user_id: 用户ID
        db: 数据库会话
    """
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    # 获取用户历史（简化：使用空历史）
    # TODO: 从数据库获取真实历史数据
    attempt_history = []

    # 获取难度推荐
    recommendation = get_difficulty_recommendation(
        user_skill_level=user.skill_level,
        attempt_history=attempt_history
    )

    return DifficultyRecommendationResponse(
        recommended_difficulty=recommendation["recommended_difficulty"],
        difficulty_distribution=recommendation["difficulty_distribution"],
        reasoning=recommendation["reasoning"],
        next_milestone=recommendation["next_milestone"],
        should_challenge=recommendation["should_challenge"]
    )


@router.get("/analysis/{user_id}", response_model=HistoryAnalysisResponse)
async def get_history_analysis(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    progress_service: ProgressService = Depends(get_progress_svc)
):
    """
    获取学习历史分析

    深入分析用户的刷题历史，提供：
    - 学习曲线（进步趋势）
    - 薄弱领域识别
    - 学习模式分析
    - 个性化改进建议

    Args:
        user_id: 用户ID
        db: 数据库会话
        progress_service: 进度服务
    """
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    # 获取历史分析
    analysis = await progress_service.get_user_history_analysis(user_id, db)

    return HistoryAnalysisResponse(
        total_problems=analysis.get("total_problems", 0),
        total_time=analysis.get("total_time", 0),
        success_rate=analysis.get("success_rate", 0.0),
        learning_curve=analysis.get("learning_curve", {}),
        weak_areas=analysis.get("weak_areas", {}),
        study_patterns=analysis.get("study_patterns", {}),
        recommendations=analysis.get("recommendations", [])
    )


@router.get("/similar/{problem_id}", response_model=RecommendationResponse)
async def get_similar_problems(
    problem_id: str,
    count: int = Query(5, ge=1, le=20, description="推荐数量"),
    problem_service: ProblemService = Depends(get_problem_svc)
):
    """
    获取相似题目推荐

    基于指定题目，找出相似的题目用于强化练习。

    相似度计算考虑：
    - 标签重叠（Jaccard相似度）
    - 难度相近
    - 公司重叠

    Args:
        problem_id: 题目ID
        count: 推荐数量
        problem_service: 题目服务
    """
    # 获取目标题目
    target_problem = problem_service.get_problem_by_id(problem_id)
    if not target_problem:
        raise HTTPException(status_code=404, detail=f"题目不存在: {problem_id}")

    # 获取所有题目
    all_problems = problem_service.get_all_problems(limit=500)

    # 创建推荐器
    recommender = ContentRecommender()
    problem_objects = [create_problem_from_dict(p) for p in all_problems]
    target_obj = create_problem_from_dict(target_problem)

    # 获取相似题目
    similar = recommender.recommend_similar(target_obj, problem_objects, top_k=count)

    recommended_problems = [
        RecommendedProblem(
            problem_id=p.id,
            title=p.title,
            difficulty=p.difficulty,
            tags=p.tags,
            estimated_time=p.estimated_time,
            frequency=p.frequency,
            score=sim,
            reasons=[f"与 {target_problem['title']} 相似"]
        )
        for p, sim in similar
    ]

    return RecommendationResponse(
        recommendations=recommended_problems,
        total=len(recommended_problems),
        metadata={
            "target_problem": problem_id,
            "target_title": target_problem["title"],
            "similarity_method": "content_based"
        }
    )


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    提交推荐反馈

    收集用户对推荐的反馈，用于改进推荐算法。

    **反馈类型**：
    - `helpful`: 推荐有帮助
    - `not_helpful`: 推荐不相关
    - `too_easy`: 难度太低
    - `too_hard`: 难度太高

    Args:
        feedback: 反馈请求
        db: 数据库会话
    """
    # 验证用户
    result = await db.execute(select(User).where(User.id == feedback.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {feedback.user_id}")

    # TODO: 保存反馈到数据库
    # 这里可以创建一个反馈表来存储

    return {
        "success": True,
        "message": "感谢您的反馈！",
        "feedback_type": feedback.feedback_type,
        "problem_id": feedback.problem_id
    }


@router.get("/tags/weak/{user_id}", response_model=List[dict])
async def get_weak_tags(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    progress_service: ProgressService = Depends(get_progress_svc)
):
    """
    获取用户的薄弱标签

    分析用户历史，识别需要加强的知识领域。

    Args:
        user_id: 用户ID
        db: 数据库会话
        progress_service: 进度服务
    """
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    # 获取历史分析
    analysis = await progress_service.get_user_history_analysis(user_id, db)

    weak_areas = analysis.get("weak_areas", {})
    weak_tags = weak_areas.get("weak_tags", [])

    # 格式化返回
    return [
        {
            "tag": tag,
            "weakness_score": score,
            "recommendation": f"建议多练习 {tag} 类型的题目"
        }
        for tag, score in weak_tags[:10]
    ]

