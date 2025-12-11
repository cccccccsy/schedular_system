"""API v1 端点

提供 REST API 接口：
- /problems - 题目管理
- /plans - 计划管理
- /users - 用户管理
- /recommendations - 推荐系统
"""

from . import plans
from . import problems
from . import users
from . import recommendations

__all__ = ["plans", "problems", "users", "recommendations"]
