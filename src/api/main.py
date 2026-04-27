"""
Agentic GraphRAG 主入口

启动 API 服务:
    python -m src.api.main
"""

import uvicorn
from src.config.settings import settings


def main():
    """启动应用"""
    uvicorn.run(
        "src.api.app:create_app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        factory=True,
    )


if __name__ == "__main__":
    main()
