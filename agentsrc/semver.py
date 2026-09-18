"""semver.py — 提示词语义版本治理（第4轮：提示词语义版本，相似度 <0.7 判 Major）

规则：
  similarity < 0.70  → MAJOR（语义大改，下游必须重验）
  similarity < 0.95  → MINOR（措辞微调/新增约束）
  otherwise          → PATCH（错字修正等）
v0.1 用字符级 difflib 作降级实现（零依赖）；similarity() 预留 fn 参数，
可换 embedding 余弦相似度（红队补丁 P1：字符级会被"同义改写"骗过，v0.2 接入语义向量）。
"""

from __future__ import annotations

import difflib
import re

MAJOR, MINOR, PATCH = "major", "minor", "patch"
MAJOR_THRESHOLD = 0.70
MINOR_THRESHOLD = 0.95


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def similarity(old: str, new: str, fn=None) -> float:
    """相似度 [0,1]。fn 可注入 embedding 相似度函数（签名 fn(old,new)->float）。"""
    if fn is not None:
        return float(fn(old, new))
    return difflib.SequenceMatcher(None, _normalize(old), _normalize(new)).ratio()


def judge(old: str, new: str, fn=None) -> tuple[str, float]:
    """返回 (级别, 相似度)。级别 ∈ {major, minor, patch}。"""
    r = similarity(old, new, fn)
    if r < MAJOR_THRESHOLD:
        return MAJOR, r
    if r < MINOR_THRESHOLD:
        return MINOR, r
    return PATCH, r


def bump(version: str, old: str, new: str, fn=None) -> tuple[str, str, float]:
    """按语义相似度晋升版本，返回 (新版本号, 级别, 相似度)。"""
    m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", str(version).strip())
    if not m:
        raise ValueError(f"version 必须是 X.Y.Z，当前为「{version}」")
    level, ratio = judge(old, new, fn)
    x, y, z = (int(g) for g in m.groups())
    if level == MAJOR:
        x, y, z = x + 1, 0, 0
    elif level == MINOR:
        y, z = y + 1, 0
    else:
        z += 1
    return f"{x}.{y}.{z}", level, ratio
