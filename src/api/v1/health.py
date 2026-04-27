"""
健康检查接口
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    message: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        message="Agentic GraphRAG API is running"
    )


@router.get("/")
async def root():
    """根路径"""
    return {
        "message": "Welcome to Agentic GraphRAG API",
        "version": "0.1.0",
        "docs": "/docs"
    }
