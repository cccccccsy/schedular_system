"""用户管理 API 端点"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.database import get_db
from models.user import User
from schemas.user import UserCreate, UserUpdate, UserResponse


router = APIRouter()


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新用户

    **请求示例**：
    ```json
    {
      "username": "coder123",
      "email": "coder@example.com",
      "skill_level": "intermediate",
      "daily_time_budget": 90,
      "preferred_difficulty": ["medium", "easy"],
      "weak_tags": ["dynamic-programming", "tree"],
      "strong_tags": ["array", "string"]
    }
    ```

    Args:
        user_data: 用户数据
        db: 数据库会话
    """
    # 检查用户名是否存在
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    # 检查邮箱是否存在
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    # 创建用户
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        skill_level=user_data.skill_level,
        daily_time_budget=user_data.daily_time_budget,
        preferred_difficulty=user_data.preferred_difficulty,
        weak_tags=user_data.weak_tags,
        strong_tags=user_data.strong_tags
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    return db_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户信息

    Args:
        user_id: 用户ID
        db: 数据库会话
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新用户信息

    Args:
        user_id: 用户ID
        user_update: 更新数据
        db: 数据库会话
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    # 更新字段
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return user


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除用户

    Args:
        user_id: 用户ID
        db: 数据库会话
    """
    from sqlalchemy import delete as sql_delete

    result = await db.execute(sql_delete(User).where(User.id == user_id))
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    return None


@router.get("/{user_id}/stats", response_model=dict)
async def get_user_stats(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取用户统计信息

    包括：
    - 完成题目数
    - 按难度分布
    - 学习曲线
    - 薄弱/擅长领域

    Args:
        user_id: 用户ID
        db: 数据库会话
    """
    # TODO: 实现完整的统计逻辑
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail=f"用户不存在: {user_id}")

    return {
        "user_id": user.id,
        "username": user.username,
        "skill_level": user.skill_level,
        "total_problems": 0,  # TODO: 从进度表统计
        "by_difficulty": {"easy": 0, "medium": 0, "hard": 0},
        "weak_areas": user.weak_tags,
        "strong_areas": user.strong_tags
    }
