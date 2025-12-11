"""数据库初始化脚本"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.database import init_db, engine, Base
from models.user import User
from models.plan import Plan, PlanItem
from models.progress import UserProgress, ProblemSubmission


async def create_tables():
    """创建所有数据表"""
    print("=" * 60)
    print("📦 数据库初始化脚本")
    print("=" * 60)

    print("\n1. 创建数据表...")
    async with engine.begin() as conn:
        # 删除所有现有表（慎用！）
        await conn.run_sync(Base.metadata.drop_all)
        print("   ✓ 清理现有表")

        # 创建所有表
        await conn.run_sync(Base.metadata.create_all)
        print("   ✓ 创建新表")

    print("\n✅ 数据库初始化完成！")
    print("\n创建的表:")
    print("  - users: 用户信息表")
    print("  - plans: 计划表")
    print("  - plan_items: 计划详情表")
    print("  - user_progress: 用户进度表")
    print("  - problem_submissions: 提交记录表")
    print("=" * 60)


async def seed_sample_data():
    """插入示例数据（可选）"""
    from sqlalchemy import select
    from models.database import AsyncSessionLocal

    print("\n2. 插入示例数据...")

    async with AsyncSessionLocal() as session:
        # 创建示例用户
        sample_user = User(
            username="demo_user",
            email="demo@example.com",
            skill_level="intermediate",
            daily_time_budget=90,
            preferred_difficulty=["medium", "easy"],
            weak_tags=["dynamic-programming", "tree"],
            strong_tags=["array", "string"]
        )
        session.add(sample_user)
        await session.commit()
        print(f"   ✓ 创建示例用户: {sample_user.username}")

    print("\n✅ 示例数据插入完成！")


async def main():
    """主函数"""
    try:
        # 创建数据表
        await create_tables()

        # 询问是否插入示例数据
        response = input("\n是否插入示例数据？(y/n): ").lower()
        if response == 'y':
            await seed_sample_data()

    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
