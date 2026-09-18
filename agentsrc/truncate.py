"""truncate.py — 语义截断（第3轮：语义截断替代粗暴压缩）

粗暴压缩 = 砍尾巴，会把「禁止/必须」这类硬约束砍掉。
语义截断 = 先给每个句子打「意图锚点分」，预算内保分高的，输出保持原顺序。
锚点词表可按领域扩充（v0.2 计划：接 RAG 索引，按历史命中率动态加权）。
"""

from __future__ import annotations

import re
from typing import Iterable

DEFAULT_ANCHORS: tuple[str, ...] = (
    "必须", "禁止", "不得", "不能", "只", "仅", "一定",
    "目标", "约束", "输出", "规则", "优先", "重要",
    "注意", "步骤", "格式", "返回", "always", "never", "must",
)

_SENT_SPLIT = re.compile(r"(?<=[。！？!?\n])")


def _split(text: str) -> list[str]:
    return [p for p in _SENT_SPLIT.split(text or "") if p.strip()]


def score_sentence(sentence: str, index: int, anchors: Iterable[str] = DEFAULT_ANCHORS) -> int:
    """意图锚点分：命中锚点词 +3；编号条目 +2；开头两句 +1（上下文地基）。"""
    s = 1
    if any(a in sentence for a in anchors):
        s += 3
    if re.match(r"^\s*(\d+[.、）)]|[-*•])", sentence):
        s += 2
    if index < 2:
        s += 1
    return s


def semantic_truncate(
    text: str,
    budget_chars: int,
    anchors: Iterable[str] = DEFAULT_ANCHORS,
) -> tuple[str, dict]:
    """在 budget_chars 内做语义截断。

    返回 (截断文本, 统计)。统计含 kept/dropped/ratio/saved_chars。
    预算无法容纳任何单句时，硬截首句并标记 hard_cut=True。
    """
    if budget_chars <= 0:
        raise ValueError("budget_chars 必须 > 0")
    parts = _split(text)
    total = sum(len(p) for p in parts)
    if total <= budget_chars:
        return text, {"kept": len(parts), "dropped": 0, "ratio": 1.0, "saved_chars": 0, "hard_cut": False}

    scored = [(score_sentence(p, i, anchors), i, p) for i, p in enumerate(parts)]
    scored_by_score = sorted(scored, key=lambda t: (-t[0], t[1]))

    used, keep_idx = 0, set()
    for _, i, p in scored_by_score:
        if used + len(p) <= budget_chars:
            keep_idx.add(i)
            used += len(p)

    hard_cut = False
    if not keep_idx:  # 单句超预算：硬截
        head = parts[0][:budget_chars]
        hard_cut = True
        stats = {"kept": 1, "dropped": len(parts) - 1,
                 "ratio": len(head) / total, "saved_chars": total - len(head), "hard_cut": True}
        return head, stats

    out = "".join(p for i, p in enumerate(parts) if i in keep_idx)
    return out, {
        "kept": len(keep_idx), "dropped": len(parts) - len(keep_idx),
        "ratio": used / total, "saved_chars": total - used, "hard_cut": False,
    }
