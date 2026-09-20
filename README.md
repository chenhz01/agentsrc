# agentsrc — your prompts are source code. You just haven't been compiling them.

Somewhere in your repo there's a 4,000-character prompt that three people edited this month.
Nobody knows what changed. Nobody knows if it still works. Your agent is running on vibes.

`agentsrc` is a zero-dependency Python toolkit (511 lines, stdlib only) that gives prompts what
code already has: a schema, semantic versioning, a linker, and a ledger.

**26 tests in 0.09s. No dependencies. No API keys. Copy the folder, you're running.**

Hitting prompt drift in production? → [Jump to Collaboration](#collaboration--the-10-that-isnt-code)

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

## Collaboration — the 10% that isn't code

Here's the honest split. This repo is the 90% that is engineering: read it, run it, fork it, and we
will never chase you about it. The other 10% is judgment — presets and thresholds we only found by
pushing prompts into production and watching them break quietly.

That 10% stays out of the repo. Not to tease you: it is the part that took the longest, and the part
that fails the most silently when it is wrong.

| Tier | What you get | Where it lives |
|---|---|---|
| 🌱 Open | All five modules, 26 tests, the hermes-agent gap analysis | This repo. MIT. Take it. |
| 🔑 Partner | The presets and adapters below | One conversation away |
| 💎 Never shipped | Production traces, client work, pricing | Our desk |

**Behind the lock:**

- **Embedding similarity preset** — what actually closes the paraphrase loophole. The shipped
  `difflib` baseline gets fooled by a rewrite; this is the threshold pair we use instead.
- **RAG-indexed anchor weighting** — `truncate.py` scores `必须/禁止` at +3. That number is an opening
  guess. This is the version that survived contact with real 4,000-character prompts.
- **Industry prompt recipes** — e-commerce support, brand voice, compliance. Working manifests, not
  blank templates.
- **A2A adapter** — manifest beyond MCP.

**How to ask.** Two lines get you a real reply:

1. What you are building, and what the prompt does inside it.
2. Which item above you need, and what you already tried.

A one-line "can I get the files" message gets a one-line answer. The two-line version usually gets the
preset.

→ **hcac4735@agent.qq.com** — replies inside 48h. 中文直接写，不用翻译成英文。
→ Outside China, or mail bouncing? **shanlun2029@outlook.com** reaches us too.

**Not a fit:** star swaps, "let's collaborate" with no project, anyone rebuilding this as a competing
toolkit. **A fit:** you ship agents to real users, prompt governance has already bitten you once, and
you would rather it stopped.

Prefer to work in the open? Open an issue describing the failure mode your prompt has. We fold the
sharpest ones into v0.3 and credit you in the commit.

## License

MIT © 2026 Shanlun

## Tests

```bash
python -m unittest discover -s tests -v   # 26 tests, all green on 3.12/3.13
```
