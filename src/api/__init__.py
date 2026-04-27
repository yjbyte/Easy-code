"""
API 服务模块

提供：
- FastAPI 应用
- 路由定义
- 中间件
"""

from .app import create_app

__all__ = [
    "create_app",
]
