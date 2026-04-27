"""
Skills 技能系统模块

提供：
- Skill: 技能基类
- SkillCategory: 技能分类
- SkillContext: 技能上下文
- SkillResult: 技能结果
- SkillRegistry: 技能注册表
- 预置技能
"""

from .skill import (
    Skill,
    SkillCategory,
    SkillContext,
    SkillResult,
    SkillStatus,
    SkillExecution,
    SkillRegistry,
    get_skill_registry
)

__all__ = [
    "Skill",
    "SkillCategory",
    "SkillContext",
    "SkillResult",
    "SkillStatus",
    "SkillExecution",
    "SkillRegistry",
    "get_skill_registry",
]
