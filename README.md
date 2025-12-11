# 智能刷题计划调度系统

一个智能的刷题计划调度系统，基于 FastAPI 构建，使用调度算法、动态规划、贪心算法和推荐系统生成个性化学习计划。

## 项目特点

- 🚀 **标准 REST API**: 使用 FastAPI 构建，自动生成 API 文档
- 🧮 **纯 Python 算法**: 独立的算法模块，包含调度、DP、贪心、推荐四大类
- 📊 **智能调度**: 根据用户时间和能力自动生成最优学习计划
- 💾 **轻量级存储**: SQLite + JSON 文件，易于部署和维护

## 技术栈

- **Web 框架**: FastAPI 0.109+
- **数据库**: SQLite (异步 aiosqlite)
- **ORM**: SQLAlchemy 2.0+
- **算法库**: NumPy, SciPy
- **开发工具**: Pytest, Black, Ruff

## 核心算法

### 1. 调度算法（核心）
- 任务调度：将题目分配到多天
- 时间分配：估算每道题的完成时间
- 多天规划：确保知识连贯性和难度平衡

### 2. 动态规划
- 最优序列选择
- 价值最大化
- 标签覆盖优化

### 3. 贪心算法
- 优先级计算
- 快速调度
- 实时推荐

### 4. 推荐系统
- 基于内容的推荐
- 难度智能匹配
- 历史数据分析

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python scripts/init_db.py
```

### 3. 启动服务

```bash
# 方式1：直接运行
python src/main.py

# 方式2：使用 uvicorn
uvicorn main:app --reload

# 方式3：使用 fastapi cli（如果已安装）
fastapi dev src/main.py
```

### 4. 访问 API 文档

服务启动后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## API 端点

### 计划管理 `/api/v1/plans`
- `POST /` - 生成刷题计划
- `POST /quick` - 快速生成计划
- `GET /{plan_id}` - 获取计划详情
- `GET /user/{user_id}` - 获取用户所有计划
- `PATCH /{plan_id}/progress` - 更新进度
- `DELETE /{plan_id}` - 删除计划

### 题目管理 `/api/v1/problems`
- `GET /` - 查询题目列表（支持筛选）
- `GET /{problem_id}` - 获取题目详情
- `POST /` - 添加新题目
- `PUT /{problem_id}` - 更新题目
- `DELETE /{problem_id}` - 删除题目
- `GET /stats/overview` - 获取统计信息
- `GET /tags/` - 获取所有标签

### 推荐系统 `/api/v1/recommendations`
- `POST /` - 获取个性化推荐
- `GET /quick` - 快速推荐
- `GET /difficulty/{user_id}` - 获取难度推荐
- `GET /analysis/{user_id}` - 获取学习历史分析
- `GET /similar/{problem_id}` - 获取相似题目
- `POST /feedback` - 提交推荐反馈
- `GET /tags/weak/{user_id}` - 获取薄弱标签

### 用户管理 `/api/v1/users`
- `POST /` - 创建用户
- `GET /{user_id}` - 获取用户信息
- `PUT /{user_id}` - 更新用户信息
- `DELETE /{user_id}` - 删除用户
- `GET /{user_id}/stats` - 获取用户统计

## 项目结构

```
schedular_system/
├── src/
│   ├── api/v1/              # REST API 端点
│   ├── models/              # 数据库模型
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # 业务逻辑层
│   ├── algorithms/          # 核心算法模块
│   │   ├── scheduler/       # 调度算法
│   │   ├── optimizer/       # 动态规划
│   │   ├── greedy/          # 贪心算法
│   │   └── recommender/     # 推荐系统
│   ├── repositories/        # 数据访问层
│   └── utils/               # 工具函数
├── data/
│   ├── problems/            # 题目数据 (JSON)
│   └── database/            # SQLite 数据库
├── tests/                   # 测试用例
└── scripts/                 # 工具脚本
```

## 开发计划

### Phase 1: 基础设施 ✅
- [x] 项目目录结构
- [x] 数据库模型
- [x] FastAPI 基础框架
- [x] 题目数据加载

### Phase 2: 核心算法 ✅
- [x] 贪心算法 - 优先级计算 (`priority_calculator.py`)
- [x] 贪心算法 - 快速调度 (`quick_scheduler.py`)
- [x] 调度算法 - 任务调度核心 (`task_scheduler.py`)
- [x] 调度算法 - 时间分配器 (`time_allocator.py`)
- [x] 调度算法 - 多天规划器 (`multi_day_planner.py`)
- [x] 动态规划 - 序列优化 (`sequence_optimizer.py`)
- [x] 动态规划 - DP优化器 (`dp_optimizer.py`)

### Phase 3: 推荐系统 ✅
- [x] 内容推荐 (`content_recommender.py`)
- [x] 难度匹配 (`difficulty_matcher.py`)
- [x] 历史分析 (`history_analyzer.py`)

### Phase 4: 业务逻辑 ✅
- [x] 计划生成服务 (`plan_service.py`)
- [x] 进度跟踪服务 (`progress_service.py`)
- [x] 题目管理服务 (`problem_service.py`)

### Phase 5: API 完善 ✅
- [x] 计划管理 API (`/api/v1/plans`)
- [x] 题目管理 API (`/api/v1/problems`)
- [x] 用户管理 API (`/api/v1/users`)
- [x] 推荐系统 API (`/api/v1/recommendations`)

### Phase 6: 测试与文档（进行中）
- [ ] 单元测试
- [ ] 集成测试
- [ ] 完整文档

## 示例数据

系统预装了 20 道经典 LeetCode 题目作为示例数据，涵盖：
- **难度分布**: Easy (40%), Medium (50%), Hard (10%)
- **标签覆盖**: Array, String, Tree, DP, DFS/BFS, Backtracking 等
- **公司频率**: Amazon, Google, Microsoft, Facebook 等

## 配置说明

复制 `.env.example` 到 `.env` 并根据需要修改：

```bash
cp .env.example .env
```

主要配置项：
- `DEBUG`: 调试模式
- `DATABASE_URL`: 数据库路径
- `DEFAULT_DAILY_TIME_BUDGET`: 默认每日时间预算（分钟）

## 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_algorithms/

# 查看覆盖率
pytest --cov=src tests/
```

## 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 开启 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 作者

Created for interview demonstration - showcasing backend development and algorithm implementation skills.

---

**Status**: ✅ Phase 1-5 完成，Phase 6 进行中

**Version**: 0.2.0
