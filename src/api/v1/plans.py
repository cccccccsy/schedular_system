"""计划管理 API 端点"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from models.database import get_db
from schemas.plan import (
    PlanCreate, PlanResponse, PlanListResponse,
    PlanProgressUpdate, PlanProgressResponse, QuickPlanRequest
)
from services.plan_service import get_plan_service, PlanService


router = APIRouter()


def get_service() -> PlanService:
    """依赖注入：获取计划服务"""
    return get_plan_service()


@router.post("/", response_model=PlanResponse, status_code=201)
async def create_plan(
    plan_data: PlanCreate,
    db: AsyncSession = Depends(get_db),
    service: PlanService = Depends(get_service)
):
    """
    生成刷题计划

    这是系统的核心功能，将调用所有算法模块生成个性化刷题计划。

    **算法流程**：
    1. 加载用户信息和偏好
    2. 选择/推荐题目（如果未指定）
    3. 计算每道题的优先级（贪心算法）
    4. 优化题目选择（DP优化器）
    5. 优化题目顺序（拓扑排序+聚类）
    6. 生成多天计划（任务调度算法）
    7. 难度平衡和时间分配

    **请求示例**：
    ```json
    {
      "user_id": 1,
      "title": "30天算法突击",
      "start_date": "2025-01-01",
      "daily_time_budget": 90,
      "total_days": 30,
      "preferences": {
        "difficulty_distribution": {"easy": 0.3, "medium": 0.5, "hard": 0.2},
        "focus_tags": ["array", "dynamic-programming"],
        "target_companies": ["google", "amazon"],
        "algorithm_mode": "balanced"
      }
    }
    ```

    Args:
        plan_data: 计划创建请求
        db: 数据库会话
        service: 计划服务
    """
    try:
        plan = await service.create_plan(plan_data, db)
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建计划失败: {str(e)}")


@router.post("/quick", response_model=PlanResponse, status_code=201)
async def create_quick_plan(
    request: QuickPlanRequest,
    db: AsyncSession = Depends(get_db),
    service: PlanService = Depends(get_service)
):
    """
    快速生成计划（简化版）

    使用默认配置快速生成计划，适合快速体验。

    **请求示例**：
    ```json
    {
      "user_id": 1,
      "daily_time_budget": 60,
      "total_days": 30,
      "focus_tags": ["array", "tree"]
    }
    ```

    Args:
        request: 快速计划请求
        db: 数据库会话
        service: 计划服务
    """
    from datetime import date
    from schemas.plan import PlanCreate, PlanPreferences

    # 转换为完整的PlanCreate
    plan_data = PlanCreate(
        user_id=request.user_id,
        title=f"{request.total_days}天刷题计划",
        start_date=date.today(),
        daily_time_budget=request.daily_time_budget,
        total_days=request.total_days,
        preferences=PlanPreferences(
            focus_tags=request.focus_tags,
            target_companies=request.target_companies,
            algorithm_mode="balanced"
        )
    )

    try:
        plan = await service.create_plan(plan_data, db)
        return plan
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建计划失败: {str(e)}")


@router.get("/{plan_id}", response_model=dict)
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    service: PlanService = Depends(get_service)
):
    """
    获取计划详情

    返回完整的计划信息，包括每日安排和进度。

    Args:
        plan_id: 计划ID
        db: 数据库会话
        service: 计划服务
    """
    plan = await service.get_plan_by_id(plan_id, db)

    if not plan:
        raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")

    # TODO: 构建完整响应（包括进度信息）
    return {
        "plan_id": plan.id,
        "title": plan.title,
        "user_id": plan.user_id,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat(),
        "total_problems": plan.total_problems,
        "total_time": plan.total_time,
        "status": plan.status,
        "created_at": plan.created_at.isoformat() if plan.created_at else None
    }


@router.get("/user/{user_id}", response_model=PlanListResponse)
async def list_user_plans(
    user_id: int,
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    service: PlanService = Depends(get_service)
):
    """
    获取用户的所有计划

    Args:
        user_id: 用户ID
        status: 状态过滤（active, completed, abandoned）
        limit: 返回数量
        offset: 偏移量
        db: 数据库会话
        service: 计划服务
    """
    plans = await service.get_user_plans(user_id, db, status)

    # 简化响应（避免循环导入）
    plan_responses = [
        {
            "plan_id": p.id,
            "title": p.title,
            "start_date": p.start_date.isoformat(),
            "end_date": p.end_date.isoformat(),
            "total_problems": p.total_problems,
            "status": p.status
        }
        for p in plans[offset:offset+limit]
    ]

    return {
        "plans": plan_responses,
        "total": len(plans),
        "page": (offset // limit) + 1 if limit > 0 else 1,
        "page_size": limit
    }


@router.patch("/{plan_id}/progress", response_model=dict)
async def update_plan_progress(
    plan_id: int,
    progress_update: PlanProgressUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新计划进度

    记录用户完成某道题的情况。

    **请求示例**：
    ```json
    {
      "problem_id": "1",
      "status": "completed",
      "time_spent": 25,
      "difficulty_rating": 3,
      "notes": "第一次没想到用 hash table"
    }
    ```

    Args:
        plan_id: 计划ID
        progress_update: 进度更新数据
        db: 数据库会话
    """
    # TODO: 实现进度更新逻辑
    return {
        "updated": True,
        "message": "进度更新成功",
        "problem_id": progress_update.problem_id,
        "status": progress_update.status
    }


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除计划

    Args:
        plan_id: 计划ID
        db: 数据库会话
    """
    # TODO: 实现删除逻辑
    from sqlalchemy import select, delete as sql_delete
    from models.plan import Plan, PlanItem

    # 删除计划项
    await db.execute(sql_delete(PlanItem).where(PlanItem.plan_id == plan_id))

    # 删除计划
    result = await db.execute(sql_delete(Plan).where(Plan.id == plan_id))

    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"计划不存在: {plan_id}")

    return None
