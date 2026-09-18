"""test_registry.py — 成长治理层测试（v0.2.0）

运行：python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentsrc import SkillRegistry, parse_skill_md  # noqa: E402

SKILL_V1 = """---
name: kefu-tone
version: 1.0.0
description: 客服语气技能
---

你是客服代理。必须引用订单号原句。禁止承诺退款。
"""

SKILL_BODY_V2 = """你是客服代理。必须引用客户订单号原句。禁止承诺退款以外的补偿。语气使用品牌词表。
"""

SKILL_V2 = SKILL_V1.replace("你是客服代理。必须引用订单号原句。禁止承诺退款。\n", SKILL_BODY_V2)


class TestParseSkillMd(unittest.TestCase):
    def test_parse(self):
        meta, body = parse_skill_md(SKILL_V1)
        self.assertEqual(meta["name"], "kefu-tone")
        self.assertEqual(meta["version"], "1.0.0")
        self.assertIn("禁止承诺退款", body)

    def test_no_frontmatter(self):
        with self.assertRaises(ValueError):
            parse_skill_md("没有 frontmatter 的普通文件")


class TestRegistry(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.store = self.dir / "ledger.jsonl"
        self.skill = self.dir / "SKILL.md"
        self.reg = SkillRegistry(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, text):
        self.skill.write_text(text, encoding="utf-8")

    def test_lifecycle(self):
        # ① new
        self._write(SKILL_V1)
        a = self.reg.audit(self.skill)
        self.assertEqual(a["status"], "new")
        # ② record 底账 → ok
        r = self.reg.record(self.skill, note="baseline")
        self.assertEqual(r["version"], "1.0.0")
        self.assertEqual(self.reg.audit(self.skill)["status"], "ok")
        # ③ 内容变、版本没升 → drift（治理违规，给出建议版本）
        self._write(SKILL_V2)
        a = self.reg.audit(self.skill)
        self.assertEqual(a["status"], "drift")
        self.assertIn(a["level"], ("major", "minor"))
        self.assertRegex(a["recommended_version"], r"^\d+\.\d+\.\d+$")
        # ④ record() 合规入账 → 版本自动晋升且写回文件 → ok
        r = self.reg.record(self.skill, note="语义升级")
        self.assertEqual(r["version"], a["recommended_version"])
        self.assertEqual(self.reg.audit(self.skill)["status"], "ok")
        self.assertIn(f"version: {r['version']}", self.skill.read_text(encoding="utf-8"))
        # ⑤ 版本升了内容没变 → noise
        self._write(SKILL_V2.replace("version: 1.0.0", "version: 9.9.9")
                    if "version: 1.0.0" in SKILL_V2 else SKILL_V2)
        # 上面 SKILL_V2 的版本行来自 SKILL_V1 头部，直接手工构造 noise：
        self._write(SKILL_V2.replace("version: 1.1.0", "version: 9.9.9")
                    .replace("version: 2.0.0", "version: 9.9.9"))
        a = self.reg.audit(self.skill)
        self.assertEqual(a["status"], "noise")

    def test_rollback(self):
        self._write(SKILL_V1)
        self.reg.record(self.skill)
        self._write(SKILL_V2)
        r2 = self.reg.record(self.skill)
        v2 = r2["version"]
        # 回滚到 1.0.0（回滚前状态与账本末条一致 → 无需快照，账本 2 条即可完整还原）
        self.reg.rollback("kefu-tone", self.skill, to_version="1.0.0")
        body = parse_skill_md(self.skill.read_text(encoding="utf-8"))[1]
        self.assertIn("禁止承诺退款。", body)  # 回到 v1 内容
        self.assertNotIn("退款以外的补偿", body)  # v2 内容必须消失（防「新旧正文拼接」回归）
        hist = [e for e in self.store.read_text(encoding="utf-8").splitlines() if e.strip()]
        self.assertEqual(len(hist), 2)
        # 可逆性证明：账本只进不退——回滚后再 record，从账本末条 1.1.0 前向晋升 1.2.0（内容=旧版，版本向前）
        r3 = self.reg.record(self.skill)
        self.assertEqual(r3["version"], "1.2.0")
        self.assertEqual(r3["level"], "minor")
        self.assertEqual(self.reg.audit(self.skill)["status"], "ok")

    def test_audit_dir(self):
        sub = self.dir / "skills" / "kefu"
        sub.mkdir(parents=True)
        (sub / "SKILL.md").write_text(SKILL_V1, encoding="utf-8")
        results = self.reg.audit_dir(self.dir)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "new")

    def test_invalid_version(self):
        self._write(SKILL_V1.replace("version: 1.0.0", "version: v1"))
        self.assertEqual(self.reg.audit(self.skill)["status"], "invalid")

    def test_rollback_unknown_version(self):
        self._write(SKILL_V1)
        self.reg.record(self.skill)
        with self.assertRaises(KeyError):
            self.reg.rollback("kefu-tone", self.skill, to_version="8.8.8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
