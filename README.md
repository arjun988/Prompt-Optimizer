# OpenPrompt

**The open-source prompt optimizer.**

Analyze. Optimize. Evaluate. Benchmark.

OpenPrompt treats prompts like code: parse into a structured AST, lint for issues, optimize with evaluation-driven strategies, and prove improvements with test suites.

```bash
pip install -e .

# Offline lint (no API key)
openprompt lint examples/summarize/prompt.txt

# Optimize with bundled tests (mock provider — no API key)
openprompt optimize examples/summarize --tests examples/summarize/tests.yaml --strategy hybrid

# Evaluate a task directory (prompt.txt + tests.yaml)
openprompt eval examples/summarize

# Real model (requires provider API key or local Ollama)
openprompt optimize examples/summarize --provider ollama --model llama3.2
```

## Features

- **Prompt AST (v1.1)** — Text/YAML → structured IR (RAG, agent/tools, media attachments)
- **Linter** — Ambiguity, contradictions, missing output format (offline)
- **Optimizer** — `rewrite`, `iterative`, `evolutionary`, `hybrid`, `compress`, `rag`, `agent`, `grpo`, `few_shot`, `extraction`
- **Dataset extraction** — PDF/image samples + labeled JSON; optimize prompts for your data
- **Evaluation** — Exact match, regex, JSON schema, semantic, LLM judge, plugin evaluators
- **Multimodal** — PDF text extraction + vision attachments (OpenAI, Gemini)
- **NSGA-II + bandit** — Multi-objective selection with LinUCB operator choice
- **Plugins** — Entry points for operators, evaluators, strategies
- **REST API** — `openprompt serve` with auth, CORS, rate limits
- **Local observability** — SQLite run history (no telemetry by default)

## Quick Start

```bash
# Install
pip install -e .

# Scaffold a project (task layout: prompts/example/prompt.txt + tests.yaml)
openprompt init

# Examples in this repo
openprompt lint examples/summarize/prompt.txt
openprompt eval examples/summarize
openprompt optimize examples/summarize --tests examples/summarize/tests.yaml

# JSON output for CI
openprompt eval examples/summarize --json
openprompt optimize examples/summarize --tests examples/summarize/tests.yaml --json

# Compress tokens
openprompt compress examples/summarize/prompt.txt

# Security scan
openprompt security examples/summarize/prompt.txt
```

### Providers

| Provider | Install | Env var |
|----------|---------|---------|
| `mock` | built-in | — (heuristic scores only; good for smoke tests) |
| `ollama` | built-in | `OLLAMA_HOST` |
| `openai` | `pip install 'openprompt[openai]'` | `OPENAI_API_KEY` |
| `anthropic` | `pip install 'openprompt[anthropic]'` | `ANTHROPIC_API_KEY` |
| `grok` | `pip install 'openprompt[grok]'` | `XAI_API_KEY` |
| `gemini` | `pip install 'openprompt[gemini]'` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |
| `openrouter` | built-in | `OPENROUTER_API_KEY` |

```bash
openprompt optimize examples/summarize \
  --provider openai --model gpt-4o-mini \
  --tests examples/summarize/tests.yaml
```

## Extraction datasets (PDF / images)

For “optimize a prompt to extract perfectly from my documents”:

```bash
pip install -e ".[media]"   # pypdf for PDF text extraction

openprompt dataset init --name invoice --path datasets/invoice
# Add samples/*.pdf and labels/*.json

openprompt dataset eval datasets/invoice/dataset.yaml \
  --prompt prompts/invoice/prompt.yaml

openprompt dataset optimize datasets/invoice/dataset.yaml \
  --prompt prompts/invoice/prompt.yaml \
  --strategy extraction \
  --vision   # attach images/PDFs for vision models
```

See [examples/extraction-dataset/README.md](examples/extraction-dataset/README.md).

## Configuration

`openprompt.yaml`:

```yaml
project: my-project

model:
  provider: ollama
  name: llama3.2

optimizer:
  strategy: hybrid
  eval_budget: 100
  few_shot_count: 3

meta_model:          # GRPO proposer (optional)
  provider: openai
  model: gpt-4o-mini

evaluation:
  pass_threshold: 0.85
  dataset_path: datasets/invoice/dataset.yaml

privacy:
  telemetry: false
  storage: local
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `openprompt init` | Scaffold project + example task |
| `openprompt lint` | Offline prompt analysis (`--json`) |
| `openprompt inspect` | Show parsed AST |
| `openprompt optimize` | Optimize (`--tests`, `--strategy`, `--json`) |
| `openprompt eval` | Run test suite (`--fail-on-regression`) |
| `openprompt compress` | Reduce tokens |
| `openprompt benchmark` | Compare multiple prompts |
| `openprompt compare` | A/B on tests |
| `openprompt security` | Security scan (`--fail-on-findings`) |
| `openprompt diff` | Diff versions (`--dir`) |
| `openprompt template` | Built-in templates |
| `openprompt multi-model` | Optimize across models (`-m provider:model`) |
| `openprompt cost-recommend` | Quality/cost Pareto pick |
| `openprompt tune` | Bayesian-style hyperparameter tuning |
| `openprompt dataset init` | Scaffold PDF/image extraction dataset |
| `openprompt dataset eval` | Eval prompt on dataset |
| `openprompt dataset optimize` | Optimize for extraction |
| `openprompt serve` | REST API (`--api-key`) |

## Python SDK

```python
from openprompt import OpenPrompt, ModelSpec

client = OpenPrompt(provider="mock")
print(client.lint("Summarize this article.").score)

result = client.optimize(
    "examples/summarize",
    strategy="hybrid",
    tests_path="examples/summarize/tests.yaml",
)
print(result.prompt, f"{result.score_delta:+.1%}")
```

### REST API

```bash
pip install 'openprompt[server]'
export OPENPROMPT_API_KEY=your-secret
openprompt serve --api-key your-secret
# Docs: http://127.0.0.1:8000/docs
```

Send `X-API-Key: your-secret` on all endpoints except `/health`.

## Examples layout

```
examples/
├── summarize/
│   ├── prompt.txt
│   └── tests.yaml
├── classification/
│   ├── prompt.txt
│   └── tests.yaml
├── code-review.yaml
└── extraction-dataset/README.md
```

After `openprompt init`:

```
prompts/example/prompt.txt
prompts/example/tests.yaml
openprompt.yaml
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check openprompt
python scripts/export_openapi.py   # refresh openapi.json
```

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Documentation

See [PRD.md](PRD.md) for the full product requirements and roadmap.
