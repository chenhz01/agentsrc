# agentsrc — your prompts are source code. You just haven't been compiling them.

Somewhere in your repo there's a 4,000-character prompt that three people edited this month.
Nobody knows what changed. Nobody knows if it still works. Your agent is running on vibes.

`agentsrc` is a zero-dependency Python toolkit (511 lines, stdlib only) that gives prompts what
code already has: a schema, semantic versioning, a linker, and a ledger.

**26 tests in 0.12s. No dependencies. No API keys. Copy the folder, you're running.**

## The problem in one table

| Prompts as text | Prompts as source (agentsrc) |
|---|---|
| Breaks silently at runtime | Fails at "compile time" (schema validation) |
| Version = `v2_final_really` | Version bumped by semantic similarity |
| Truncation chops the tail — kills your 必须/禁止 constraints | Truncation keeps intent anchors alive |
| Intent flows one way | Bidirectional bridge: manifest ⇄ MCP tool descriptor |

## Quickstart

```bash
pip install agentsrc   # or just copy agentsrc/ into your project
```

```python
from agentsrc import parse, validate, bump, semantic_truncate, to_mcp_tool

manifest = parse(open("examples/kefu-reply.agentsrc", encoding="utf-8").read())
errors = validate(manifest)            # [] => build passes

new_version, level, ratio = bump("1.2.0", old_prompt, new_prompt)

safe_prompt, stats = semantic_truncate(long_prompt, budget_chars=4000)

tool = to_mcp_tool(manifest)           # your intent, exposed as an MCP tool
```

## v0.2 — hermes-agent grows skills. Who keeps the books?

[NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) (246k★) sells itself
as *"the agent that grows with you"* — skills that create and improve themselves at runtime.
We read the code and asked one question: **who audits the growth?**

Nobody. So `agentsrc.registry` does it for any `agentskills.io`-standard `SKILL.md`:

```python
from agentsrc import SkillRegistry

reg = SkillRegistry("ledger.jsonl")
reg.audit("skills/kefu/SKILL.md")
# {"status": "drift", "recommended_version": "2.0.0",
#  "action": "内容变了版本没升——治理违规！"}

reg.record("skills/kefu/SKILL.md", note="语义升级")  # auto-bump + write-back + JSONL ledger
reg.audit_dir("skills/")                             # batch audit
reg.rollback("kefu-tone", "skills/kefu/SKILL.md", to_version="1.0.0")
```

Four states per skill: `new / ok / drift / noise`. Content changed without a version bump =
**drift = governance violation**, flagged immediately. Growth keeps accounts.

## Why we built this (honestly)

We run production agents. Someone (usually us) edits a prompt, and the only version control is
memory. DSPy compiles prompts but has no version governance; promptfoo tests them but has no
schema or semver; MCP moves them but doesn't govern them. The seam between all of them was
empty — so we filled it. agentsrc isn't a competitor to these tools; it's the missing upstream.

## Honest limits (read before you trust us)

- v0.2 similarity is a **character-level baseline** (`difflib`). A paraphrase rewrite can fool it.
  That's exactly why `similarity()` accepts an injected embedding function — see Collaboration.
- Chinese intent anchors (必须/禁止) are hardcoded defaults; custom anchors work, CJK tokenization
  is heuristic, not linguistic.
- Zero-dependency means zero-dependency: no pydantic sugar. The YAML subset is deliberately tiny
  (that's the feature — small subset, earlier errors).

## Modules

| Module | Since | What it does |
|---|---|---|
| `schema.py` | v0.1 | Deliberately small YAML subset + strict validation |
| `semver.py` | v0.1 | `<0.70 → MAJOR`, `<0.95 → MINOR`, else `PATCH`; pluggable similarity |
| `truncate.py` | v0.1 | Intent-anchor scoring (必须/禁止 +3, numbered +2), order-preserving truncation |
| `bridge.py` | v0.1 | Bidirectional manifest ⇄ MCP tool descriptor |
| `registry.py` | v0.2 | Growth ledger: audit / record / rollback / batch, for agentskills.io SKILL.md |

## Roadmap

- **v0.3** — embedding-based similarity default, RAG-indexed anchor weighting
- **v0.4** — Pydantic-style compile-time contracts, A2A adapter, OpenTelemetry span export

## Collaboration (what's behind the lock)

Some parts of this problem are 90% engineering, 10% judgment calls earned in production.
The judgment calls aren't in the repo — they're available by working with us:

- **Embedding similarity preset** (kill the paraphrase loophole for real)
- **RAG-indexed anchor weighting** (stop guessing which sentences matter)
- **Industry prompt recipe templates** (e-commerce support, brand voice, compliance)
- **A2A full adapter** (manifest beyond MCP)

Building something serious? → **hcac4735@agent.qq.com** (replies within 48h)

## License

MIT © 2026 Shanlun

## Tests

```bash
python -m unittest discover -s tests -v   # 26 tests, all green on 3.12/3.13
```
