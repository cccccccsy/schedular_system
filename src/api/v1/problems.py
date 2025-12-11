"""题目管理 API 端点"""
from typing import List
from fastapi import APIRouter, HTTPException, Query, Depends

from schemas.problem import (
    ProblemResponse, ProblemCreate, ProblemUpdate,
    ProblemListResponse, ProblemQueryParams, ProblemStatsResponse
)
from services.problem_service import get_problem_service, ProblemService


router = APIRouter()


def get_service() -> ProblemService:
    """依赖注入：获取题目服务"""
    return get_problem_service()


@router.get("/", response_model=ProblemListResponse)
async def list_problems(
    difficulty: List[str] | None = Query(None, description="难度过滤"),
    tags: List[str] | None = Query(None, description="标签过滤"),
    companies: List[str] | None = Query(None, description="公司过滤"),
    search: str | None = Query(None, description="搜索关键词"),
    min_frequency: float | None = Query(None, ge=0, le=1, description="最小频率"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    offset: int = Query(0, ge=0, description="偏移量"),
    service: ProblemService = Depends(get_service)
):
    """
    获取题目列表

    支持多种过滤条件：
    - 难度：easy, medium, hard
    - 标签：如 array, dynamic-programming
    - 公司：如 amazon, google
    - 搜索：标题关键词
    - 频率：最小出题频率
    """
    query_params = ProblemQueryParams(
        difficulty=difficulty,
        tags=tags,
        companies=companies,
        search=search,
        min_frequency=min_frequency,
        limit=limit,
        offset=offset
    )

    problems, total = service.search_problems(query_params)

    # 转换为响应模型
    problem_responses = [
        ProblemResponse(**problem, priority=None)
        for problem in problems
    ]

    return ProblemListResponse(
        problems=problem_responses,
        total=total,
        page=(offset // limit) + 1 if limit > 0 else 1,
        page_size=limit
    )


@router.get("/{problem_id}", response_model=ProblemResponse)
async def get_problem(
    problem_id: str,
    service: ProblemService = Depends(get_service)
):
    """
    根据ID获取题目详情

    Args:
        problem_id: 题目ID
    """
    problem = service.get_problem_by_id(problem_id)

    if not problem:
        raise HTTPException(status_code=404, detail=f"题目不存在: {problem_id}")

    return ProblemResponse(**problem, priority=None)


@router.post("/", response_model=ProblemResponse, status_code=201)
async def create_problem(
    problem: ProblemCreate,
    service: ProblemService = Depends(get_service)
):
    """
    创建新题目

    Args:
        problem: 题目数据
    """
    created_problem = service.add_problem(problem)
    return ProblemResponse(**created_problem, priority=None)


@router.put("/{problem_id}", response_model=ProblemResponse)
async def update_problem(
    problem_id: str,
    problem_update: ProblemUpdate,
    service: ProblemService = Depends(get_service)
):
    """
    更新题目信息

    Args:
        problem_id: 题目ID
        problem_update: 更新数据
    """
    updated_problem = service.update_problem(problem_id, problem_update)

    if not updated_problem:
        raise HTTPException(status_code=404, detail=f"题目不存在: {problem_id}")

    return ProblemResponse(**updated_problem, priority=None)


@router.delete("/{problem_id}", status_code=204)
async def delete_problem(
    problem_id: str,
    service: ProblemService = Depends(get_service)
):
    """
    删除题目

    Args:
        problem_id: 题目ID
    """
    success = service.delete_problem(problem_id)

    if not success:
        raise HTTPException(status_code=404, detail=f"题目不存在: {problem_id}")

    return None


@router.get("/stats/overview", response_model=ProblemStatsResponse)
async def get_statistics(
    service: ProblemService = Depends(get_service)
):
    """
    获取题目统计信息

    包括：
    - 总题目数
    - 按难度分布
    - 按标签分布
    - 按平台分布
    - 平均预估时间
    """
    return service.get_statistics()


@router.get("/tags/", response_model=List[dict])
async def list_tags(
    service: ProblemService = Depends(get_service)
):
    """
    获取所有可用的标签

    返回标签列表及其详细信息
    """
    return service.get_all_tags()


@router.get("/tags/{tag_id}", response_model=dict)
async def get_tag_info(
    tag_id: str,
    service: ProblemService = Depends(get_service)
):
    """
    获取标签详细信息

    Args:
        tag_id: 标签ID
    """
    tag_info = service.get_tag_info(tag_id)

    if not tag_info:
        raise HTTPException(status_code=404, detail=f"标签不存在: {tag_id}")

    return tag_info
