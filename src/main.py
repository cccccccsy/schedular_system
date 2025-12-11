"""FastAPI 应用主入口"""
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models.database import init_db, close_db


# 全局变量：缓存题目数据
problems_cache = {}
tags_cache = {}


def load_problems_data():
    """加载题目数据到内存"""
    global problems_cache, tags_cache

    # 加载题目
    try:
        with open(settings.problems_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            problems_cache = {p["id"]: p for p in data.get("problems", [])}
            print(f"✓ 加载 {len(problems_cache)} 道题目")
    except FileNotFoundError:
        print(f"⚠ 题目文件未找到: {settings.problems_json_path}")
        problems_cache = {}

    # 加载标签
    try:
        with open(settings.tags_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            tags_cache = {t["id"]: t for t in data.get("tags", [])}
            print(f"✓ 加载 {len(tags_cache)} 个标签")
    except FileNotFoundError:
        print(f"⚠ 标签文件未找到: {settings.tags_json_path}")
        tags_cache = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    print("=" * 60)
    print(f"🚀 {settings.app_name} v{settings.app_version} 启动中...")
    print("=" * 60)

    # 初始化数据库
    print("📦 初始化数据库...")
    await init_db()
    print("✓ 数据库初始化完成")

    # 加载题目数据
    print("📚 加载题目数据...")
    load_problems_data()

    print("=" * 60)
    print(f"✅ 服务启动成功！访问 http://localhost:8000/docs 查看 API 文档")
    print("=" * 60)

    yield

    # 关闭时执行
    print("\n🛑 服务关闭中...")
    await close_db()
    print("✓ 数据库连接已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="一个智能的刷题计划调度系统，使用调度算法、动态规划、贪心算法和推荐系统生成个性化学习计划",
    lifespan=lifespan,
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 根端点
@app.get("/")
async def root():
    """根端点 - 服务信息"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "api": settings.api_v1_prefix,
        "statistics": {
            "total_problems": len(problems_cache),
            "total_tags": len(tags_cache),
        }
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "database": "connected",
        "problems_loaded": len(problems_cache) > 0,
        "tags_loaded": len(tags_cache) > 0,
    }


# 注册 API 路由
from api.v1 import plans, problems, users, recommendations

app.include_router(
    problems.router,
    prefix=f"{settings.api_v1_prefix}/problems",
    tags=["Problems - 题目管理"]
)
app.include_router(
    plans.router,
    prefix=f"{settings.api_v1_prefix}/plans",
    tags=["Plans - 计划管理"]
)
app.include_router(
    users.router,
    prefix=f"{settings.api_v1_prefix}/users",
    tags=["Users - 用户管理"]
)
app.include_router(
    recommendations.router,
    prefix=f"{settings.api_v1_prefix}/recommendations",
    tags=["Recommendations - 推荐系统"]
)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下自动重载
    )
