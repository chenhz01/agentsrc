"""bridge.py — 意图双向桥接（第4轮：意图双向桥接、MCP/A2A 适配）

单向 = 人写 Prompt、机器猜；双向 = 人写「意图清单」，机器生成/回写协议描述。
v0.1 落地 MCP tool descriptor 双向转换：
  to_mcp_tool(manifest)   意图清单 → MCP 工具描述（可粘进任何 MCP server 配置）
  from_mcp_tool(tool)     MCP 工具描述 → 意图清单（反向回流，改完再正向生成，形成闭环）
A2A 适配器留 v0.2（接口位已预留： descriptor_kind 参数）。
"""

from __future__ import annotations

from typing import Any

_PARAM_TYPES = {"string", "int", "number", "bool", "list"}
_JSON_TYPE = {"int": "integer", "number": "number", "bool": "boolean",
              "list": "array", "string": "string"}


def to_mcp_tool(manifest: dict, descriptor_kind: str = "mcp") -> dict:
    """意图清单 → 协议工具描述。descriptor_kind: "mcp"（v0.1 仅实现 mcp）。"""
    if descriptor_kind != "mcp":
        raise NotImplementedError(f"descriptor_kind={descriptor_kind!r} 将在 v0.2 提供（A2A 适配）")
    if not isinstance(manifest, dict) or "name" not in manifest:
        raise ValueError("manifest 必须是含 name 的 dict（先用 schema.parse 生成）")

    properties: dict[str, dict] = {}
    required: list[str] = []
    for key, spec in (manifest.get("params") or {}).items():
        ptype, req = "string", False
        if isinstance(spec, str):
            parts = [p.strip().lower() for p in spec.split(",") if p.strip()]
            if parts and parts[0] in _PARAM_TYPES:
                ptype = parts[0]
            if "required" in parts[1:]:
                req = True
        properties[key] = {"type": _JSON_TYPE.get(ptype, "string")}
        if req:
            required.append(key)

    return {
        "name": str(manifest["name"]),
        "description": str(manifest.get("intent", "")),
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }


def from_mcp_tool(tool: dict) -> dict:
    """MCP 工具描述 → 意图清单（反向桥接，形成「改清单→再生成」闭环）。"""
    if not isinstance(tool, dict) or "name" not in tool:
        raise ValueError("tool 必须是含 name 的 MCP 工具描述")
    schema = tool.get("inputSchema") or {}
    params: dict[str, str] = {}
    required = set(schema.get("required") or [])
    for key, spec in (schema.get("properties") or {}).items():
        t = str((spec or {}).get("type", "string"))
        rev = {v: k for k, v in _JSON_TYPE.items()}
        ptype = rev.get(t, "string")
        params[key] = f"{ptype}, required" if key in required else ptype
    return {
        "name": str(tool["name"]),
        "version": "0.0.0",          # 反向桥接不猜版本，由 semver.bump 晋升
        "intent": str(tool.get("description", "")),
        "params": params,
    }
