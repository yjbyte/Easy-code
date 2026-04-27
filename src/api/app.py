"""
FastAPI 应用创建
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Agentic GraphRAG",
        description="智能体驱动的图增强检索生成系统",
        version="0.1.0",
    )

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    _register_routes(app)

    # 注册事件处理器
    _register_events(app)

    return app


def _register_routes(app: FastAPI) -> None:
    """注册路由"""
    from src.api.v1.health import router as health_router
    from src.api.v1.chat import router as chat_router
    from src.api.v1.tools import router as tools_router
    # MCP 路由暂时禁用，需要实现 src/mcp/servers 模块
    # from src.api.v1.mcp import router as mcp_router

    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    app.include_router(chat_router, prefix="/api/v1", tags=["chat"])
    app.include_router(tools_router, prefix="/api/v1", tags=["tools"])
    # app.include_router(mcp_router, prefix="/api/v1", tags=["mcp"])


def _register_events(app: FastAPI) -> None:
    """注册事件处理器"""

    @app.on_event("startup")
    async def startup_event():
        """启动事件"""
        print("[STARTUP] Agentic GraphRAG API starting...")
        print(f"   Version: 0.1.0")
        print(f"   Address: http://{settings.api_host}:{settings.api_port}")
        print(f"   Docs: http://{settings.api_host}:{settings.api_port}/docs")

    @app.on_event("shutdown")
    async def shutdown_event():
        """关闭事件"""
        print("[SHUTDOWN] Agentic GraphRAG API closed")
