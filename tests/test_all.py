"""test_all.py — agentsrc v0.1.0 全量测试（零依赖 unittest）

运行：python -m unittest discover -s tests -v
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agentsrc import (  # noqa: E402
    bridge, bump, from_mcp_tool, judge, parse, semantic_truncate,
    similarity, to_mcp_tool, validate,
)
from agentsrc.schema import SubsetSyntaxError  # noqa: E402

MANIFEST = """\
name: kefu-reply-agent
version: 1.2.0
intent: 客服自动回复代理：按品牌语气规则生成回复草稿，禁止承诺退款
params:
  customer_text: string, required
  tone: string
rules:
  - 必须引用客户订单号原句
  - 禁止出现退款以外的补偿承诺
outputs:
  - draft
"""


class TestSchema(unittest.TestCase):
    def test_parse_full(self):
        m = parse(MANIFEST)
        self.assertEqual(m["name"], "kefu-reply-agent")
        self.assertEqual(m["params"]["customer_text"], "string, required")
        self.assertEqual(m["rules"][1], "禁止出现退款以外的补偿承诺")

    def test_validate_ok(self):
        self.assertEqual(validate(parse(MANIFEST)), [])

    def test_validate_missing(self):
        errs = validate({"name": "x", "version": "1.0.0"})
        self.assertTrue(any("intent" in e for e in errs))

    def test_validate_bad_version(self):
        errs = validate({"name": "x", "version": "1.0", "intent": "y"})
        self.assertTrue(any("X.Y.Z" in e for e in errs))

    def test_strict_unknown_key(self):
        errs = validate(dict(parse(MANIFEST), para=None))  # 拼错 params
        self.assertTrue(any("未知顶层键" in e for e in errs))

    def test_tab_rejected(self):
        with self.assertRaises(SubsetSyntaxError):
            parse("name: x\n\tversion: 1.0.0")

    def test_scalar_types(self):
        m = parse("name: x\nversion: 1.0.0\nintent: t\nmetadata:\n  retry: 3\n  on: true\n  ratio: 0.5\n")
        self.assertEqual(m["metadata"], {"retry": 3, "on": True, "ratio": 0.5})


class TestSemver(unittest.TestCase):
    BASE = "你是客服代理。必须引用订单号原句。禁止承诺退款。语气正式。" * 3

    def test_patch(self):
        level, r = judge(self.BASE, self.BASE.replace("正式", "正式。"))
        self.assertEqual(level, "patch")
        self.assertGreaterEqual(r, 0.95)

    def test_minor(self):
        changed = self.BASE.replace("语气正式。", "语气正式并使用品牌词表。") * 1
        level, r = judge(self.BASE, changed)
        self.assertEqual(level, "minor")
        self.assertGreaterEqual(r, 0.70)

    def test_major(self):
        level, _ = judge(self.BASE, "你是一个完全不同的翻译助手，把输入翻译成英文并输出JSON。")
        self.assertEqual(level, "major")

    def test_bump(self):
        v, level, _ = bump("1.2.0", self.BASE, "完全不同的新提示词，做完全另一件事。")
        self.assertEqual((v, level), ("2.0.0", "major"))
        v2, level2, _ = bump("1.2.0", self.BASE, self.BASE.replace("订单号", "工单编号"))
        self.assertEqual(v2.split(".")[0], "1")
        self.assertIn(level2, ("minor", "patch"))

    def test_custom_similarity_fn(self):
        # 预留的 embedding 接口位：注入恒等函数验证走 fn 分支
        level, _ = judge("a", "b", fn=lambda o, n: 0.5)
        self.assertEqual(level, "major")


class TestTruncate(unittest.TestCase):
    TEXT = ("这是一个客服代理。"
            "你必须引用客户订单号原句。"
            "今天天气不错，这段是废话填充内容，没有任何约束信息，可以丢弃。"
            "禁止承诺退款以外的补偿。"
            "再补一段无锚点的闲聊句子用来占预算，让截断器有得选。")

    def test_no_truncation_needed(self):
        out, st = semantic_truncate(self.TEXT, budget_chars=10_000)
        self.assertEqual(out, self.TEXT)
        self.assertEqual(st["dropped"], 0)

    def test_anchors_survive(self):
        out, st = semantic_truncate(self.TEXT, budget_chars=40)
        self.assertIn("必须引用客户订单号原句", out)
        self.assertGreater(st["dropped"], 0)
        self.assertFalse(st["hard_cut"])

    def test_order_preserved(self):
        out, _ = semantic_truncate(self.TEXT, budget_chars=60)
        i1, i2 = out.find("必须"), out.find("禁止")
        self.assertLess(i1, i2)

    def test_hard_cut(self):
        out, st = semantic_truncate("只有一句话且特别长" * 30, budget_chars=10)
        self.assertTrue(st["hard_cut"])
        self.assertEqual(len(out), 10)


class TestBridge(unittest.TestCase):
    def test_roundtrip(self):
        m = parse(MANIFEST)
        tool = to_mcp_tool(m)
        self.assertEqual(tool["name"], "kefu-reply-agent")
        self.assertIn("禁止承诺退款", tool["description"])
        self.assertEqual(tool["inputSchema"]["required"], ["customer_text"])
        self.assertEqual(tool["inputSchema"]["properties"]["tone"]["type"], "string")

        back = from_mcp_tool(tool)
        self.assertEqual(back["name"], "kefu-reply-agent")
        self.assertEqual(back["params"]["customer_text"], "string, required")
        self.assertEqual(back["params"]["tone"], "string")

    def test_to_mcp_tool_requires_name(self):
        with self.assertRaises(ValueError):
            to_mcp_tool({"intent": "x"})

    def test_a2a_reserved(self):
        with self.assertRaises(NotImplementedError):
            to_mcp_tool(parse(MANIFEST), descriptor_kind="a2a")


if __name__ == "__main__":
    unittest.main(verbosity=2)
