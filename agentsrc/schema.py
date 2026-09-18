"""schema.py — YAML 子集定义与解析（第2轮：划定"YAML 子集"）

刻意只用一个子集，不做完整 YAML：
  - 嵌套 dict：2 空格缩进
  - 列表："- 条目"
  - 标量：字符串 / int / float / bool
  - 注释：# 开头的行被忽略
理由：Prompt 清单不需要锚点/多行块/流式语法——子集越小，校验越硬，错得越早（编译期错误 > 运行期事故）。
"""

from __future__ import annotations

import re
from typing import Any

# 顶层必备键（编译期契约的最小集）
REQUIRED_KEYS = ("name", "version", "intent")
KNOWN_KEYS = set(REQUIRED_KEYS) | {"params", "rules", "outputs", "metadata"}

_INT_RE = re.compile(r"^-?\d+$")
_FLOAT_RE = re.compile(r"^-?\d+\.\d+$")
_BOOL = {"true": True, "false": False}


def parse_scalar(raw: str) -> Any:
    """把子集标量转成 Python 值。"""
    s = raw.strip()
    if s.lower() in _BOOL:
        return _BOOL[s.lower()]
    if _INT_RE.match(s):
        return int(s)
    if _FLOAT_RE.match(s):
        return float(s)
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def parse(text: str) -> dict:
    """解析 YAML 子集为 dict。语法不合法时抛 SubsetSyntaxError。"""
    lines: list[tuple[int, str]] = []
    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise SubsetSyntaxError(f"第{lineno}行：子集禁止 Tab 缩进（只允许空格）")
        lines.append((len(raw) - len(raw.lstrip(" ")), stripped))
    if not lines:
        raise SubsetSyntaxError("空文件")

    value, idx = _parse_block(lines, 0, lines[0][0])
    if idx != len(lines):
        raise SubsetSyntaxError(f"第{lines[idx][0]}列缩进不可解析（第 {idx+1} 行附近）")
    if not isinstance(value, dict):
        raise SubsetSyntaxError("顶层必须是键值映射")
    return value


def _parse_block(lines, idx, indent):
    """从 idx 开始解析一个同缩进块，返回 (值, 下一个未消费的下标)。"""
    if lines[idx][1].startswith("- "):
        items = []
        while idx < len(lines) and lines[idx][0] == indent and lines[idx][1].startswith("- "):
            items.append(parse_scalar(lines[idx][1][2:]))
            idx += 1
        return items, idx
    node: dict = {}
    while idx < len(lines):
        cur_indent, content = lines[idx]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            raise SubsetSyntaxError(f"缩进跳级（{cur_indent} > {indent}）：内容「{content[:30]}」")
        m = re.match(r"^([^:]+):\s*(.*)$", content)
        if not m:
            raise SubsetSyntaxError(f"行不是「key: value」形式：「{content[:40]}」")
        key, rest = m.group(1).strip(), m.group(2).strip()
        idx += 1
        if rest:  # 叶子
            node[key] = parse_scalar(rest)
        else:     # 有子块
            if idx < len(lines) and lines[idx][0] > cur_indent:
                child, idx = _parse_block(lines, idx, lines[idx][0])
                node[key] = child
            elif idx < len(lines) and lines[idx][0] == cur_indent and lines[idx][1].startswith("- "):
                child, idx = _parse_block(lines, idx, cur_indent)
                node[key] = child
            else:
                node[key] = None
    return node, idx


class SubsetSyntaxError(ValueError):
    """YAML 子集语法错误（编译期失败，优于运行期事故）。"""


def validate(manifest: dict, strict: bool = True) -> list[str]:
    """校验 manifest。返回错误列表（空列表 = 通过）。strict 时未知顶层键也报错。"""
    errors: list[str] = []
    for key in REQUIRED_KEYS:
        if key not in manifest or manifest[key] in (None, ""):
            errors.append(f"缺少必备键「{key}」")
    if "version" in manifest and manifest["version"] is not None:
        if not re.match(r"^\d+\.\d+\.\d+$", str(manifest["version"])):
            errors.append(f"version 必须是 X.Y.Z 三段式，当前为「{manifest['version']}」")
    if strict:
        for key in manifest:
            if key not in KNOWN_KEYS:
                errors.append(f"未知顶层键「{key}」（strict 模式：拼错即报，不等运行）")
    params = manifest.get("params")
    if params is not None and not isinstance(params, dict):
        errors.append("params 必须是键值映射")
    for key in ("rules", "outputs"):
        val = manifest.get(key)
        if val is not None and not isinstance(val, list):
            errors.append(f"{key} 必须是列表（- 条目）")
    return errors
