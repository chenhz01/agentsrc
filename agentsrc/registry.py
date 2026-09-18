"""registry.py — 成长治理层（v0.2 突破，源自 hermes-agent 差距分析）

hermes-agent（246.7k★）的卖点是 "The agent that grows with you"：
技能自创建、自改进、记忆闭环——但它的成长是**运行时**的，长出来/改掉的 Prompt
**没有账本**：改了什么、语义变了多少、要不要重验下游，没人管。

registry 把这道缝补上：对 agentskills.io 标准（hermes 兼容）的 SKILL.md 做
「** governed growth（有账本的成长）**」——

    audit   : 技能文件体检 → new / ok / drift / noise / bumped
    record  : 合规登记（自动按语义相似度晋升版本，写入 JSONL 账本）
    rollback: 按版本回滚技能正文（账本存快照，可回写）

治理四态：
    new     未登记（账本里没有底账）
    ok      内容与账本一致，版本一致
    drift   内容变了、版本没升 —— 治理违规（最危险：悄悄变化）
    noise   版本升了、内容没变 —— 版本噪音
    bumped  内容与版本都变了但未登记 —— 合规升级，待 record 入账
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from .semver import bump as semver_bump

_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.S)
_KEYVAL = re.compile(r"^([A-Za-z_][\w-]*):\s*(.*)$")


def parse_skill_md(text: str) -> tuple[dict, str]:
    """解析 SKILL.md：frontmatter（--- 包裹的 key: value）+ 正文。无 frontmatter 抛 ValueError。"""
    m = _FRONT.match(text)
    if not m:
        raise ValueError("无 frontmatter（需以 --- 开头的 key: value 块）")
    meta: dict = {}
    for line in m.group(1).splitlines():
        kv = _KEYVAL.match(line.strip())
        if kv:
            meta[kv.group(1)] = kv.group(2).strip()
    return meta, text[m.end():]


class SkillRegistry:
    """技能成长账本（JSONL 存储，零依赖）。"""

    def __init__(self, store_path):
        self.store_path = Path(store_path)
        self._index: dict[str, list[dict]] = {}
        if self.store_path.exists():
            for line in self.store_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    e = json.loads(line)
                    self._index.setdefault(e["name"], []).append(e)

    # ── 内部 ────────────────────────────────────────────
    @staticmethod
    def _body_hash(body: str) -> str:
        return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]

    def _append(self, entry: dict) -> None:
        with self.store_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._index.setdefault(entry["name"], []).append(entry)

    def _last(self, name: str) -> dict | None:
        hist = self._index.get(name)
        return hist[-1] if hist else None

    # ── 体检 ────────────────────────────────────────────
    def audit(self, skill_md_path) -> dict:
        """体检单个 SKILL.md，返回治理四态之一 + 建议动作。"""
        path = Path(skill_md_path)
        text = path.read_text(encoding="utf-8")
        meta, body = parse_skill_md(text)
        name = meta.get("name") or path.stem
        version = str(meta.get("version", ""))
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            return {"status": "invalid", "name": name, "file": str(path),
                    "reason": f"frontmatter version 非法：{version!r}（需 X.Y.Z）"}

        last = self._last(name)
        if last is None:
            return {"status": "new", "name": name, "file": str(path),
                    "cur_version": version, "action": "record() 建立底账"}

        if last["body_hash"] == self._body_hash(body):
            if last["version"] == version:
                return {"status": "ok", "name": name, "file": str(path), "version": version}
            return {"status": "noise", "name": name, "file": str(path),
                    "cur_version": version, "last_version": last["version"],
                    "action": f"内容未变，版本 {last['version']}→{version} 属噪音；回滚版本号或 record() 追认"}

        new_v, level, ratio = semver_bump(last["version"], last["body"], body)
        if last["version"] == version:
            return {"status": "drift", "name": name, "file": str(path),
                    "cur_version": version, "similarity": round(ratio, 4),
                    "recommended_version": new_v, "level": level,
                    "action": f"内容变了版本没升（{level}）——治理违规！应升 {new_v} 并 record()"}
        return {"status": "bumped", "name": name, "file": str(path),
                "cur_version": version, "last_version": last["version"],
                "similarity": round(ratio, 4), "level": level,
                "action": "合规升级，待 record() 入账"}

    def audit_dir(self, dir_path) -> list[dict]:
        """递归体检目录下全部 SKILL.md（agentskills.io 标准）。"""
        return [self.audit(p) for p in sorted(Path(dir_path).rglob("SKILL.md"))]

    # ── 登记 ────────────────────────────────────────────
    def record(self, skill_md_path, note: str = "") -> dict:
        """登记/入账：首次建底账；已有底账则按语义相似度自动晋升版本并写回文件。"""
        path = Path(skill_md_path)
        text = path.read_text(encoding="utf-8")
        meta, body = parse_skill_md(text)
        name = meta.get("name") or path.stem
        last = self._last(name)

        if last is None:
            version = str(meta.get("version", "0.1.0"))
            level, ratio = "baseline", 1.0
        else:
            if last["body_hash"] == self._body_hash(body) and last["version"] == str(meta.get("version", "")):
                return {"name": name, "version": last["version"], "note": "无变化，未入账"}
            version, level, ratio = semver_bump(last["version"], last["body"], body)

        entry = {"name": name, "version": version, "level": level,
                 "similarity": round(ratio, 4), "body_hash": self._body_hash(body),
                 "body": body, "note": note,
                 "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        self._append(entry)

        if last is not None:  # 版本晋升写回文件 frontmatter
            path.write_text(_rewrite_front(text, version), encoding="utf-8")
        return {"name": name, "version": version, "level": level,
                "similarity": round(ratio, 4), "recorded": True}

    # ── 回滚 ────────────────────────────────────────────
    def rollback(self, name: str, skill_md_path, to_version: str | None = None) -> dict:
        """把技能正文回滚到账本中某版本（默认上一个）。当前快照先自动入账，保证回滚本身可再回滚。"""
        hist = self._index.get(name)
        if not hist:
            raise KeyError(f"账本中无 {name!r}")
        target = None
        if to_version is None:
            target = hist[-1]
        else:
            target = next((e for e in reversed(hist) if e["version"] == to_version), None)
            if target is None:
                raise KeyError(f"{name!r} 无版本 {to_version!r}（已有：{[e['version'] for e in hist]}）")

        path = Path(skill_md_path)
        text = path.read_text(encoding="utf-8")
        meta, body = parse_skill_md(text)
        if self._body_hash(body) != target["body_hash"]:
            self.record(path, note="rollback 前自动快照")  # 回滚本身上账
            text = path.read_text(encoding="utf-8")
        path.write_text(_rewrite_front(text, target["version"]) + target["body"], encoding="utf-8")
        return {"name": name, "rolled_back_to": target["version"]}


def _rewrite_front(text: str, new_version: str) -> str:
    """替换 frontmatter 中的 version 行，其余保持原样（只替换匹配段，不动正文）。"""
    def repl(m: re.Match) -> str:
        block = re.sub(r"(?m)^version:.*$", f"version: {new_version}", m.group(1))
        return f"---\n{block}\n---\n"
    return _FRONT.sub(repl, text, count=1)
