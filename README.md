# agentsrc — Prompt-as-Source Toolkit

> **Core thesis**: Prompt engineering is evolving from unstructured text toward **Agent source code**.
> Prompts deserve what code already has: a schema, a compiler, semantic versioning, and governance.

`agentsrc` is a zero-dependency Python toolkit that treats an agent's prompt as a *compiled artifact* with build-time guarantees, not a blob of prose.

## Why

| Treating prompts as text | Treating prompts as source |
|---|---|
| Broken silently at runtime | **Fails at "compile time"** (schema validation) |
| Version = `v2_final_really` | **Semantic versioning driven by similarity** |
| Truncation = chop the tail (kills your hard constraints) | **Semantic truncation** keeps intent anchors |
| Intent flows one way (human writes, machine guesses) | **Bidirectional intent bridge** (manifest ⇄ MCP tool descriptor) |

## Install & Quickstart

```bash
# zero dependencies, Python 3.10+
pip install agentsrc   # or: copy the agentsrc/ folder into your project
```

```python
from agentsrc import parse, validate, bump, semantic_truncate, to_mcp_tool

manifest = parse(open("examples/kefu-reply.agentsrc", encoding="utf-8").read())
errors = validate(manifest)            # [] => build passes

# prompt changed? get a governed version bump, not a guess
new_version, level, ratio = bump("1.2.0", old_prompt, new_prompt)

# context window tight? truncate WITHOUT losing your 必须/禁止 constraints
safe_prompt, stats = semantic_truncate(long_prompt, budget_chars=4000)

# expose the agent's intent as an MCP tool descriptor
tool = to_mcp_tool(manifest)
```

## Modules (v0.1.0)

| Module | Rounds | What it does |
|---|---|---|
| `schema.py` | r2 | A **deliberately small YAML subset** + strict validation. Small subset = harder errors, earlier. |
| `semver.py` | r4 | Similarity-driven versioning: `<0.70 → MAJOR`, `<0.95 → MINOR`, else `PATCH`. Pluggable similarity fn (bring your own embeddings). |
| `truncate.py` | r3 | **Semantic truncation**: scores sentences by intent anchors (必须/禁止/must/never…), keeps high-scoring ones within budget, preserves order. |
| `bridge.py` | r4 | **Bidirectional bridge**: manifest → MCP tool descriptor, and back. Round-trip closes the governance loop. |
| `ParserRegistry` | r3 | Pluggable parsers land in v0.2 (registry seam already isolated in `schema.parse`). |

## Positioning

| Project | Overlap | Difference |
|---|---|---|
| DSPy | prompt compilation | No version governance / no truncation semantics |
| promptfoo | prompt testing | No schema or semver layer |
| MCP | transport protocol | agentsrc feeds *into* MCP, doesn't replace it |
| LangChain | runtime glue | No build-time contract for the prompt itself |

## Roadmap

- **v0.2** — `ParserRegistry` (pluggable parsers), embedding-based similarity default, A2A adapter
- **v0.3** — Pydantic-style compile-time contracts, RAG-indexed anchor weighting
- **v0.4** — WASM sandbox runner, OpenTelemetry span export (`agentsrc.build`, `agentsrc.truncate`)

> Honesty note: v0.1 similarity is a character-level baseline (`difflib`). It can be fooled by
> paraphrase rewrites — that is exactly why `similarity()` accepts an injected embedding function.

## License

MIT © 2026 Shanlun — contact: hcac4735@agent.qq.com

## Tests

```bash
python -m unittest discover -s tests -v   # 19 tests, all green on 3.12/3.13
```
