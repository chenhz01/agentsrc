"""agentsrc — Prompt-as-Source Toolkit (v0.2.0)

把 Prompt 当源代码来治理：schema(子集) + semver(语义版本) + truncate(语义截断)
+ bridge(意图双向桥接→MCP) + registry(成长治理层：给自改进 agent 的成长上账本)。
零依赖（仅 Python 标准库）。核心论断：Prompt 工程正从非结构化文本向 Agent 源代码演进。
"""

from .schema import parse, validate
from .semver import similarity, judge, bump
from .truncate import semantic_truncate
from .bridge import to_mcp_tool, from_mcp_tool
from .registry import SkillRegistry, parse_skill_md

__version__ = "0.2.0"
__all__ = [
    "parse", "validate",
    "similarity", "judge", "bump",
    "semantic_truncate",
    "to_mcp_tool", "from_mcp_tool",
    "SkillRegistry", "parse_skill_md",
    "__version__",
]
