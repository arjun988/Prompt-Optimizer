# PRD — OpenPrompt

**Working name:** OpenPrompt  
**Category:** Open-source Prompt Optimization / LLM Developer Tool  
**License:** Apache-2.0  
**Status:** Draft v0.1  
**Last updated:** 2026-08-10

---

## Executive Summary

OpenPrompt is an open-source **prompt compiler and optimizer** — not another “paste prompt, get nicer prompt” wrapper. Users bring their prompt, their model, and (optionally) their test cases. OpenPrompt parses prompts into a structured AST, diagnoses weaknesses, generates candidate variants, **evaluates them against measurable criteria**, and returns the winner with an explanation.

**Core differentiator:** Prove improvement, don’t just assert it.

```text
prompt → parse → diagnose → generate candidates → evaluate → select winner → explain
```

**Recommended optimization strategy (see §6):** A **hybrid evaluation-driven optimizer** combining **OPRO-style iterative refinement**, **evolutionary search over the Prompt AST**, and **contextual bandits** for mutation-operator selection — not classical end-to-end RL training.

---

## 1. Vision & Positioning

### 1.1 Vision

OpenPrompt should become the **compiler/toolchain for prompts** — the LLVM of LLM instructions.

| User provides | OpenPrompt produces |
|---|---|
| Raw intent: *“Analyze this code and tell me what’s wrong.”* | Structured, high-quality prompt with role, constraints, output schema, verification steps |
| Test cases + eval metrics | Measured before/after scores, token delta, cost delta |
| `prompts/v3.yaml` in git | CI regression gates, benchmark reports |

### 1.2 What we are NOT building (initially)

- SaaS dashboard, auth, billing, team management
- Mandatory cloud/database/account
- Proprietary model or vector DB requirement
- Browser extension, huge frontend, 20 providers on day one

**Adoption loop:**

```bash
pip install openprompt
openprompt optimize prompt.txt
```

### 1.3 Success Criteria (12-month)

| Metric | Target |
|---|---|
| Time to first optimization | < 2 minutes after `pip install` |
| Measurable eval improvement on bundled examples | ≥ 15% avg on 5 reference tasks |
| Offline-capable lint + AST parse | 100% of lint/inspect without API |
| CI integration | GitHub Action published, used in ≥ 3 example repos |
| PyPI installs | Community traction (track post-launch) |

---

## 2. Problem Statement

Existing prompt tools mostly implement:

```text
prompt → LLM → nicer-looking prompt
```

This fails because:

1. **No proof** — beauty ≠ performance on the user’s actual task/model
2. **No structure** — prompts stay opaque strings, hard to diff/version/test
3. **No feedback loop** — failures don’t drive targeted fixes
4. **No multi-objective tradeoffs** — quality vs tokens vs cost ignored

OpenPrompt treats prompts like **code**: parse, lint, optimize, test, benchmark, version, CI.

---

## 3. Users & Use Cases

### 3.1 Primary Personas

| Persona | Need |
|---|---|
| **LLM application developer** | Ship prompts that pass regression tests in CI |
| **Prompt engineer / AI team** | Systematic optimization with eval datasets |
| **Open-source contributor** | Local-first tool, pluggable strategies |
| **Agent/MCP builder** | Optimize system prompts, tool descriptions, RAG instructions |

### 3.2 Core Use Cases

1. **Quick optimize** — `openprompt optimize prompt.txt` with no test suite (heuristic + optional LLM judge)
2. **Eval-driven optimize** — User provides `tests/`; optimizer maximizes measured score
3. **Lint-only** — Offline analysis, security scan, contradiction detection
4. **CI regression** — PR fails if prompt score drops or token cost spikes
5. **Multi-model compare** — Same prompt optimized per provider

---

## 4. Product Architecture

### 4.1 Five-Layer Pipeline

```text
                 ┌─────────────────────┐
                 │      User Prompt    │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │  Intent Extraction  │
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │  Prompt Diagnosis   │  ← linter, security, contradictions
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Prompt Optimization │  ← strategies + mutations
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │ Evaluation Engine   │  ← metrics, judge, custom evaluators
                 └──────────┬──────────┘
                            ↓
                 ┌─────────────────────┐
                 │  Optimized Prompt   │  + report (why it won)
                 └─────────────────────┘
```

### 4.2 Prompt AST (Core Technical Bet)

Prompts are **not** optimized as raw strings. They flow through an intermediate representation:

```text
Prompt (text/YAML) → Parser → Prompt AST → Optimizer → Prompt AST → Renderer → Provider-specific prompt
```

**Example AST (conceptual):**

```yaml
prompt:
  role:
    description: senior software engineer
  objective:
    task: code_review
  context:
    - source_code
  constraints:
    - dont_invent_issues
    - prioritize_correctness
  output:
    format: structured_markdown
    schema: null
  examples: []
  verification:
    enabled: true
  security:
    untrusted_input_isolation: true
```

**Render targets:** OpenAI, Anthropic, Gemini, Ollama, generic chat templates.

### 4.3 Repository Layout

```text
openprompt/
├── core/
│   ├── parser/          # text/YAML → AST
│   ├── ast/             # Pydantic models
│   ├── optimizer/       # orchestration, bandits, scheduling
│   ├── evaluator/       # metrics, judges, custom hooks
│   ├── benchmark/       # compare versions, reports
│   ├── compiler/        # AST → provider prompts
│   └── security/        # injection, secrets, isolation
├── strategies/
│   ├── rewrite/
│   ├── iterative/       # OPRO-style
│   ├── evolutionary/
│   ├── compression/
│   └── ...
├── providers/
│   ├── openai/
│   ├── anthropic/
│   ├── ollama/
│   └── openrouter/
├── cli/
├── sdk/
├── server/              # optional FastAPI
├── plugins/
├── templates/
├── evaluators/
├── tests/
├── benchmarks/
└── docs/
```

### 4.4 Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| CLI | Typer + Rich |
| Validation / AST | Pydantic v2 |
| API (optional) | FastAPI |
| Storage | SQLite + YAML/JSON project files |
| Testing | pytest |
| Packaging | pyproject.toml → PyPI |
| CI | GitHub Actions |
| License | MIT |

### 4.5 Provider Architecture

```python
class ModelProvider(Protocol):
    def generate(self, messages: list[Message], **kwargs) -> ModelResponse: ...
```

Never hardcode a single vendor. MVP: **OpenAI, Anthropic, Ollama**.

---

## 5. Feature Specification

### 5.1 Optimization Dimensions

| Dimension | Behavior |
|---|---|
| **Instruction** | Resolve vague verbs; add measurable criteria |
| **Role** | Add role **only when** diagnosis predicts benefit |
| **Context** | Surface missing fields (language, env, error, expected vs actual) |
| **Constraints** | Explicit requirements, complexity, immutability, types |
| **Output** | Schemas, sections, format compliance |
| **Reasoning strategy** | Decomposition / verification — not blind “think step by step” |
| **Few-shot** | Count, diversity, ordering, formatting, edge-case coverage |
| **Example selection** | From N examples → best K via similarity + diversity + difficulty |
| **Compression** | Shorter prompt, same or better eval score |
| **Contradiction detection** | Conflicting rules with merge recommendation |
| **Ambiguity detection** | Subjective → measurable requirements |
| **Security** | Injection, untrusted context isolation, secret exposure |

### 5.2 Prompt Linter (Standalone Value)

```bash
openprompt lint prompt.txt
```

```text
Prompt Analysis
────────────────────────
❌ Ambiguous objective
⚠ Missing output schema
⚠ No failure conditions
⚠ Conflicting instructions
✓ Context provided

Score: 61/100  (heuristic — label clearly as non-predictive without eval)
```

### 5.3 Evaluation Engine

**Input:** `tests/` with `input`, optional `expected`, optional custom evaluator.

**Built-in metrics:**

| Metric | Use case |
|---|---|
| Exact match | Classification, labels |
| Regex / JSON schema | Structured output |
| Semantic similarity | Paraphrase-tolerant QA |
| LLM-as-judge | Correctness, relevance, hallucination, format |
| Custom Python | `def evaluate(output, expected) -> float` |

**Output:**

```text
Original Prompt    Accuracy: 72%
Optimized Prompt   Accuracy: 89%
Improvement        +17%
Tokens             -12%
Est. cost          -18%
```

### 5.4 Automatic Failure Analysis

On eval failure:

```text
Test #17 failed
Category:     Missing constraint
Observed:     Model returned explanation
Expected:     JSON object
Recommendation: Add strict JSON schema (OutputMutation)
→ Auto-queue Prompt v2 candidate
```

### 5.5 Multi-Objective Optimization

Objective function (configurable):

```text
score = w_quality * eval_score
      - w_tokens * normalized_token_count
      - w_cost   * estimated_usd
      - w_latency * normalized_latency
```

Pareto frontier reporting when weights not fixed.

### 5.6 CLI Commands (Full Target)

| Command | Phase |
|---|---|
| `openprompt init` | 1 |
| `openprompt optimize` | 1 |
| `openprompt lint` | 1 |
| `openprompt eval` | 1 |
| `openprompt inspect` | 1 |
| `openprompt compress` | 2 |
| `openprompt benchmark` | 2 |
| `openprompt compare` | 2 |
| `openprompt diff` | 3 |
| `openprompt security` | 2 |
| `openprompt serve` | 4 |
| `openprompt template <name>` | 2 |

### 5.7 SDK & API

```python
from openprompt import Optimizer

optimizer = Optimizer(provider="openai", model="gpt-4o")
result = optimizer.optimize(
    "Analyze this customer feedback.",
    objective="maximize_accuracy",
    constraints={"max_tokens": 1000, "format": "json"},
)
print(result.prompt, result.score_delta, result.report)
```

REST (optional, local): `POST /optimize`, `/evaluate`, `/benchmark`, `/lint`.

### 5.8 Configuration (`openprompt.yaml`)

```yaml
project: my-project

model:
  provider: ollama
  name: qwen3

optimizer:
  strategy: hybrid          # see §6
  max_iterations: 5
  candidates_per_gen: 8
  eval_budget: 100        # max model calls for optimization

evaluation:
  metrics: [correctness, format]
  judge:
    provider: ollama
    model: qwen3

objectives:
  quality_weight: 1.0
  token_weight: 0.3
  cost_weight: 0.2

privacy:
  telemetry: false
  storage: local
```

---

## 6. Optimization Strategy — Recommendation

### 6.1 Strategy Selection Summary

| Approach | Fit for OpenPrompt | Verdict |
|---|---|---|
| **End-to-end RL (PPO/GRPO)** | Requires training infra, reward model, GPU budget; poor fit for BYOM | ❌ Not primary |
| **Supervised fine-tune meta-optimizer** | Heavy; Phase 5 research only | ⏳ Later |
| **OPRO / iterative LLM refinement** | Uses eval feedback; no training; fast convergence | ✅ Primary |
| **Evolutionary (GA) on AST** | Discrete mutations; multi-objective; parallel eval | ✅ Secondary |
| **Bayesian optimization** | Expensive evals; good for hyperparams & operator weights | ✅ Tuning layer |
| **Contextual bandits (轻量 RL)** | Learn which mutations help per task type | ✅ Operator selection |
| **TextGrad / failure gradients** | Rich failure → targeted AST edits | ✅ Integrated in iterative |
| **Pure rewrite (single-shot LLM)** | Baseline / fast mode | ✅ MVP fallback |

### 6.2 Recommended Primary Strategy: **Hybrid Eval-Driven Optimizer (HEDO)**

OpenPrompt’s default strategy should be **`hybrid`**, composed of three cooperating layers:

```text
┌─────────────────────────────────────────────────────────────┐
│                    HYBRID OPTIMIZER (HEDO)                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Diagnosis-Guided Seed Generation (OPRO-inspired)  │
│    • Parse → AST → linter issues → structured critique      │
│    • LLM generates 3–5 targeted candidates (not random)     │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Evolutionary AST Search (NSGA-II style)           │
│    • Mutate via plugin operators on AST nodes               │
│    • Multi-objective: quality ↑ tokens ↓ cost ↓             │
│    • Tournament selection + elitism                         │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Contextual Bandit Operator Selection              │
│    • State = task embedding + failure categories            │
│    • Actions = mutation operators                           │
│    • Reward = Δeval_score − λ·Δtokens                       │
│    • LinUCB or Thompson sampling (no GPU training)          │
└─────────────────────────────────────────────────────────────┘
```

### 6.3 Why NOT classical RL as the core?

1. **Users bring their own models** — you cannot train a universal prompt policy offline.
2. **Eval is the ground truth** — bandits and evolutionary methods use it directly without backprop through the LLM.
3. **AST mutations are discrete** — evolutionary + bandit fits naturally; RL shines when you control model weights.
4. **Local-first / privacy** — no requirement to ship trajectories to a training cluster.

**Where RL *does* belong in OpenPrompt:**

- **Contextual bandits** for choosing `RoleMutation` vs `OutputMutation` vs `CompressionMutation` given diagnosis features (lightweight online RL).
- **Phase 5 research:** optional small **meta-model** fine-tuned with GRPO on public prompt-opt benchmarks to propose better initial mutations (still validated by user eval).

### 6.4 Algorithm Detail — Default `hybrid` Loop

```text
Input:  prompt P0, test suite T, budget B (max eval calls)
Output: best prompt P*, report R

1. PARSE & DIAGNOSE
   AST₀ ← parse(P0)
   issues ← linter(AST₀) + security_scan(AST₀)

2. SEED (OPRO-style, ~20% of budget)
   critique ← LLM("Given issues + AST, propose improvements")
   seeds ← LLM_generate_candidates(AST₀, critique, k=5)
   scores ← evaluate_each(seeds, T)
   pool ← seeds

3. EVOLUTIONARY LOOP (remaining budget)
   while eval_calls < B:
     parents ← select_pareto(pool, objectives=[quality, tokens, cost])
     for each parent:
       op ← bandit.select(state=embed(AST, failures))
       child ← op.mutate(parent)      # plugin operator
       if passes_linter(child):
         score ← evaluate(child, T)
         pool.append(child)
         bandit.update(op, reward=Δscore)
     pool ← elitism(pool, top_k)

4. FAILURE-DRIVEN REFINEMENT (TextGrad-style)
   failures ← worst_failing_tests(best)
   if failures:
     patches ← diagnose_failures(failures)  # category → mutation
     pool.extend(apply_mutations(best, patches))

5. SELECT WINNER
   P* ← argmax_pareto(pool)
   R ← diff_report(P0, P*, issues, failure_analysis)
```

### 6.5 Mutation Operator Framework (Plugins)

```python
class MutationOperator(Protocol):
    name: str
    def mutate(self, ast: PromptAST, context: OptimizeContext) -> PromptAST: ...

# Built-in operators
RoleMutation | ConstraintMutation | ContextMutation | OutputMutation
ExampleMutation | StructureMutation | CompressionMutation
SecurityMutation | ReasoningMutation
```

Users register custom operators; bandit learns when they help.

### 6.6 Strategy Presets (User-Facing)

| Strategy | When to use | Budget |
|---|---|---|
| `rewrite` | No test suite; fast single-shot | Low |
| `iterative` | Small suite; OPRO-style only | Medium |
| `evolutionary` | Broad search; many candidates | High |
| `hybrid` **(default)** | Production; eval suite available | Medium–High |
| `compress` | Token budget hard constraint | Medium |

### 6.7 Reference Literature & Lineage

- **OPRO** (Yang et al., 2023) — LLM as optimizer from scored history  
- **DSPy MIPRO/GEPA** — metric-driven prompt compilation (conceptual alignment)  
- **TextGrad** (2024) — textual gradients from failures  
- **NSGA-II** — multi-objective evolutionary selection  
- **LinUCB / Thompson Sampling** — contextual bandits for operator selection  

---

## 7. Implementation Plan

### Phase 0 — Foundation (Week 1–2)

**Goal:** Repo skeleton, dev ergonomics, empty CLI.

| Task | Deliverable |
|---|---|
| pyproject.toml, ruff, pytest, pre-commit | Dev environment |
| `openprompt --help` | Typer CLI stub |
| Pydantic AST models (v0 schema) | `core/ast/models.py` |
| Provider protocol + mock provider | Tests without API keys |

**Exit criteria:** `pip install -e .` works; CI runs pytest on push.

---

### Phase 1 — MVP Core (Week 3–8)

**Goal:** Parse, lint, basic optimize, eval — the “compiler skeleton.”

| Module | Scope |
|---|---|
| **Parser** | Plain text + YAML → AST; heuristic section detection |
| **Linter** | Ambiguity, missing output, contradictions (rule-based) |
| **Compiler** | AST → OpenAI / Anthropic / Ollama message lists |
| **Evaluator** | Exact match, JSON schema, regex; test runner |
| **Optimizer v0** | `rewrite` strategy only (single LLM pass guided by linter) |
| **Providers** | OpenAI, Anthropic, Ollama |
| **CLI** | `init`, `optimize`, `lint`, `eval`, `inspect` |
| **Examples** | 3 reference prompts + test suites |

**Exit criteria:**

```bash
openprompt optimize examples/summarize.txt
# → shows before/after, linter issues, token count

openprompt eval examples/summarize/
# → runs tests, prints score
```

---

### Phase 2 — Real Optimizer (Week 9–14)

**Goal:** Prove measurable improvement via candidate search.

| Module | Scope |
|---|---|
| **Mutation framework** | 8 built-in operators as plugins |
| **`iterative` strategy** | OPRO-style with scored history |
| **`evolutionary` strategy** | Population, crossover (AST merge), NSGA-II selection |
| **`hybrid` strategy** | Full HEDO loop (§6.4) |
| **Contextual bandit** | LinUCB operator selector |
| **Compression** | `CompressionMutation` + token-aware objective |
| **Security scanner** | Injection patterns, untrusted context warnings |
| **Failure analysis** | Category → recommended mutation |
| **CLI** | `compress`, `benchmark`, `compare`, `security` |
| **Templates** | code_review, summarization, classification, extraction |

**Exit criteria:** On bundled benchmarks, optimized prompts beat baseline by ≥ 15% avg eval score OR ≥ 20% token reduction at equal score.

---

### Phase 3 — Evaluation & Versioning (Week 15–20)

**Goal:** Prompts as tested, versioned artifacts.

| Module | Scope |
|---|---|
| **LLM-as-judge** | Configurable judge provider + rubric |
| **Custom evaluators** | Load user Python functions |
| **Benchmark reports** | Markdown + JSON export |
| **Versioning** | `prompts/foo/v1.yaml`, diff command |
| **Regression testing** | Compare vN vs vN-1, fail on threshold |
| **SQLite observability** | Runs, scores, tokens, cost (local default) |
| **GitHub Action** | `openprompt eval` in CI |

**Exit criteria:** Example repo with CI gate; `openprompt diff v1 v2` works.

---

### Phase 4 — Developer Ecosystem (Week 21–28)

**Goal:** Integration surfaces beyond CLI.

| Module | Scope |
|---|---|
| **Python SDK** | Stable public API |
| **REST server** | `openprompt serve` + FastAPI |
| **Plugin discovery** | entry points for strategies/operators/evaluators |
| **Multi-model optimize** | Per-provider render + compare table |
| **Cost optimizer** | Quality/cost Pareto recommendations |
| **Docs site** | mkdocs or similar |

**Exit criteria:** SDK on PyPI; plugin example repo; REST OpenAPI spec.

---

### Phase 5 — Advanced / Research (Week 29+)

**Goal:** Differentiation for agents, RAG, research users.

| Feature | Notes |
|---|---|
| Automatic few-shot selection | Embedding diversity + difficulty scoring |
| RAG prompt optimization | Context budget, citation rules |
| Agent layer optimization | System + tools + planning prompts |
| Tool description optimization | MCP/function-call schemas |
| Bayesian tuning | Operator weights, iteration count |
| Optional meta-model (GRPO) | Small model proposes mutations; always eval-validated |
| VS Code extension | Lint + optimize panel |

---

## 8. MVP Definition (Phase 1 Ship List)

**In scope:**

- [ ] CLI: `init`, `optimize`, `lint`, `eval`, `inspect`
- [ ] Prompt AST (Pydantic) + parser (text/YAML)
- [ ] Rule-based linter + heuristic quality score
- [ ] `rewrite` optimizer (linter-guided single pass)
- [ ] Eval: exact match, JSON, regex
- [ ] Providers: OpenAI, Anthropic, Ollama
- [ ] 3 examples + README quickstart
- [ ] Apache-2.0 license alignment (note: current LICENSE is MIT — reconcile before release)

**Out of scope for MVP:**

- Evolutionary/bandit/hybrid (Phase 2)
- REST API, VS Code, GitHub Action (Phases 3–4)
- RAG/agent optimization (Phase 5)

---

## 9. Non-Functional Requirements

| Requirement | Target |
|---|---|
| **Privacy** | No telemetry by default; local SQLite; offline lint/parse |
| **Portability** | Linux, macOS, Windows (CLI) |
| **Extensibility** | Plugin entry points for operators, strategies, evaluators, providers |
| **Determinism** | Seedable runs where possible; log all candidates + scores |
| **Cost awareness** | Token + USD estimates on every optimize/eval run |
| **Explainability** | Every recommendation ties to linter issue or eval failure |

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Eval suite too small → overfit prompts | Report confidence; holdout tests; diversity warnings |
| LLM judge bias | Support multiple judges; prefer user metrics when available |
| Optimization cost explodes | Hard `eval_budget` cap; strategy presets |
| Provider API drift | Adapter layer; contract tests with mock server |
| “Prompt score” perceived as ground truth | Label as heuristic unless backed by eval |
| License mismatch (MIT vs Apache-2.0) | Align LICENSE before public launch |

---

## 11. Metrics & Telemetry (Opt-In Only)

Local run log (default):

- prompt hash, version, model, strategy
- eval score, token in/out, latency, estimated cost
- mutation operators applied, failure categories

No cloud telemetry unless explicitly enabled.

---

## 12. Open Questions

1. **AST schema versioning** — How do we migrate `v1` AST YAML when schema evolves?
2. **Default judge model** — Ollama local vs none when no API key?
3. **Crossover semantics** — How to merge two AST prompts in evolutionary search?
4. **License** — Switch repo to Apache-2.0 to match PRD?
5. **Project name on PyPI** — `openprompt` availability?

---

## 13. Appendix A — Example End-to-End Workflow

```bash
openprompt init
# creates openprompt.yaml, prompts/, tests/, evaluators/

# Edit prompts/customer-support.yaml
openprompt lint prompts/customer-support.yaml
openprompt optimize prompts/customer-support.yaml --strategy hybrid
openprompt eval prompts/customer-support.yaml

openprompt save prompts/customer-support-v2.yaml
git commit -m "Optimize customer support prompt (+17% eval, -12% tokens)"
# CI runs openprompt eval → PASS
```

---

## 14. Appendix B — Killer CI Workflow (Target State)

```yaml
# .github/workflows/prompt-eval.yml
name: Prompt Evaluation
on: [pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install openprompt
      - run: openprompt eval prompts/ --baseline main
```

```text
Prompt benchmark
Before: 87%  |  After: 91%
Tokens: -18%
✓ No regression
✓ Security checks passed
```

---

## 15. Appendix C — Immediate Next Steps (This Repo)

1. Rename/consolidate repo branding → **OpenPrompt**
2. Align **LICENSE** to Apache-2.0 (if intended)
3. Scaffold `pyproject.toml` + package layout per §4.3
4. Implement Phase 0 + Phase 1 milestones
5. Add `benchmarks/` with 5 tasks to validate Phase 2 optimizer

---

*OpenPrompt: Analyze. Optimize. Evaluate. Benchmark. Prove it.*
