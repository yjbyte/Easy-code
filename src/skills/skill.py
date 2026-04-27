"""
Skill 技能基类和数据模型
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SkillCategory(str, Enum):
    """技能分类"""
    ANALYSIS = "analysis"           # 分析类
    RETRIEVAL = "retrieval"         # 检索类
    REASONING = "reasoning"         # 推理类
    SYNTHESIS = "synthesis"         # 综合类
    VALIDATION = "validation"       # 验证类
    GENERATION = "generation"       # 生成类
    UTILITY = "utility"             # 工具类


class SkillStatus(str, Enum):
    """技能状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SkillContext(BaseModel):
    """技能执行上下文"""

    # 输入数据
    inputs: Dict[str, Any] = Field(default_factory=dict)

    # 共享状态
    shared_memory: Dict[str, Any] = Field(default_factory=dict)

    # 执行历史
    execution_history: List["SkillExecution"] = Field(default_factory=list)

    # 配置
    config: Dict[str, Any] = Field(default_factory=dict)

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def get_input(self, key: str, default=None):
        """获取输入参数"""
        return self.inputs.get(key, default)

    def set_output(self, key: str, value: Any):
        """设置输出结果"""
        if "outputs" not in self.shared_memory:
            self.shared_memory["outputs"] = {}
        self.shared_memory["outputs"][key] = value

    def get_shared(self, key: str, default=None):
        """获取共享状态"""
        return self.shared_memory.get(key, default)

    def set_shared(self, key: str, value: Any):
        """设置共享状态"""
        self.shared_memory[key] = value

    def get_all_outputs(self) -> Dict[str, Any]:
        """获取所有输出"""
        return self.shared_memory.get("outputs", {})


class SkillExecution(BaseModel):
    """技能执行记录"""
    skill_name: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: SkillStatus = SkillStatus.PENDING
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    error: Optional[str] = None
    duration: float = 0.0


class SkillResult(BaseModel):
    """技能执行结果"""

    # 执行状态
    success: bool = Field(..., description="是否成功")
    status: SkillStatus = Field(default=SkillStatus.SUCCESS)

    # 输出数据
    outputs: Dict[str, Any] = Field(default_factory=dict, description="输出数据")

    # 执行信息
    duration: float = Field(default=0.0, description="执行时长（秒）")

    # 错误信息
    error: Optional[str] = Field(default=None, description="错误信息")
    error_code: Optional[str] = Field(default=None, description="错误代码")

    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")

    def get_output(self, key: str, default=None):
        """获取输出值"""
        return self.outputs.get(key, default)


class Skill(ABC):
    """技能基类"""

    # 元数据（子类覆盖）
    name: str
    description: str
    category: SkillCategory
    version: str = "1.0.0"
    author: str = "Agentic GraphRAG"

    # 配置
    timeout: int = 30
    retry_count: int = 0
    dependencies: List[str] = []

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """执行技能

        Args:
            context: 技能上下文

        Returns:
            SkillResult: 执行结果
        """
        pass

    async def validate_inputs(self, context: SkillContext) -> bool:
        """验证输入参数"""
        return True

    def get_input_schema(self) -> type:
        """获取输入 Schema（可选）"""
        return None

    def get_output_schema(self) -> type:
        """获取输出 Schema（可选）"""
        return None

    async def execute_dependency(
        self,
        dependency_name: str,
        context: SkillContext
    ) -> SkillResult:
        """执行依赖技能

        Args:
            dependency_name: 依赖技能名称
            context: 技能上下文

        Returns:
            SkillResult: 依赖技能的执行结果
        """
        from src.skills import get_skill_registry

        registry = get_skill_registry()
        skill = registry.get(dependency_name)

        if not skill:
            raise ValueError(f"依赖技能 '{dependency_name}' 未找到")

        return await skill.execute(context)

    def create_context(self, **inputs) -> SkillContext:
        """创建技能上下文"""
        return SkillContext(inputs=inputs)


class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[SkillCategory, List[str]] = {}

    def register(self, skill: Skill) -> None:
        """注册技能"""
        self._skills[skill.name] = skill
        self._categories.setdefault(skill.category, []).append(skill.name)

    def unregister(self, name: str) -> bool:
        """注销技能"""
        if name not in self._skills:
            return False

        skill = self._skills[name]
        self._categories[skill.category].remove(name)

        del self._skills[name]
        return True

    def get(self, name: str) -> Optional[Skill]:
        """获取技能"""
        return self._skills.get(name)

    def list_all(self) -> List[Skill]:
        """列出所有技能"""
        return list(self._skills.values())

    def list_by_category(self, category: SkillCategory) -> List[Skill]:
        """按分类列出技能"""
        names = self._categories.get(category, [])
        return [self._skills[name] for name in names]

    def find_by_capability(self, capability: str) -> List[Skill]:
        """按能力查找技能"""
        results = []
        for skill in self._skills.values():
            # 检查技能描述或名称
            if capability.lower() in skill.description.lower() or capability.lower() in skill.name.lower():
                results.append(skill)
        return results

    def count(self) -> int:
        """返回技能总数"""
        return len(self._skills)

    def clear(self) -> None:
        """清空所有技能"""
        self._skills.clear()
        self._categories.clear()


# 全局实例
_global_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """获取全局技能注册表"""
    global _global_registry
    if _global_registry is None:
        _global_registry = SkillRegistry()
    return _global_registry
