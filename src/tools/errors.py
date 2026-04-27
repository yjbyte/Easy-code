"""
Function Calling 错误定义
"""
from typing import Any, Dict, Optional


class FunctionCallError(Exception):
    """Function Calling 基础错误"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ToolNotFoundError(FunctionCallError):
    """工具不存在"""
    pass


class ToolAlreadyRegisteredError(FunctionCallError):
    """工具已被注册"""
    pass


class ParameterValidationError(FunctionCallError):
    """参数验证失败"""
    def __init__(self, message: str, parameter: str = None, corrected: Dict[str, Any] = None):
        super().__init__(message)
        self.parameter = parameter
        self.corrected = corrected or {}


class ExecutionTimeoutError(FunctionCallError):
    """执行超时"""
    def __init__(self, message: str, timeout: int):
        super().__init__(message)
        self.timeout = timeout


class ExecutionFailedError(FunctionCallError):
    """执行失败"""
    pass


class PermissionDeniedError(FunctionCallError):
    """权限不足"""
    pass
