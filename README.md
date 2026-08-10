# OpenPrompt

**The open-source prompt optimizer.**

Analyze. Optimize. Evaluate. Benchmark.

OpenPrompt is a local-first developer tool that treats prompts like code: parse them into a structured AST, lint for issues, optimize with evaluation-driven strategies, and prove improvements with test suites.

```bash
pip install -e .

openprompt optimize examples/summarize/prompt.txt
openprompt lint examples/summarize/prompt.txt
openprompt eval examples/summarize
openprompt diff v1 v2 --dir prompts/versions
```

## Features

- **Prompt AST** — Parse text/YAML into a structured intermediate representation
- **Linter** — Ambiguity, contradictions, missing output format (works offline)
- **Optimizer** — Strategies: `rewrite`, `iterative`, `evolutionary`, `hybrid`, `compress`
- **Evaluation** — Exact match, regex, JSON schema, semantic similarity, LLM-as-judge, custom Python evaluators
- **Semantic engine** — TF-IDF cosine (default) or sentence-transformers via `[semantic]` extra
- **NSGA-II** — Multi-objective Pareto selection (quality, tokens, cost)
- **AST crossover** — Evolutionary merge of prompt structures
- **Plugin operators** — Entry-point discovery under `openprompt.operators`
- **Cost modeling** — Provider-specific USD estimates in eval, benchmark, and optimize
- **Benchmark & compare** — Score and token-compare multiple prompts
- **Versioning & diff** — Treat prompts like versioned artifacts
- **Local observability** — SQLite run history (opt-in, no telemetry by default)

## Quick Start

```bash
# Initialize a project
openprompt init

# Lint (offline — no API key needed)
openprompt lint prompts/example.txt

# Optimize (uses mock provider by default)
openprompt optimize prompts/example.txt --strategy hybrid

# Evaluate against tests
openprompt eval prompts/example.txt --tests tests/example_tests.yaml

# Use a real model
openprompt optimize prompts/example.txt --provider ollama --model llama3.2
openprompt optimize prompts/example.txt --provider gemini --model gemini-2.0-flash
openprompt optimize prompts/example.txt --provider grok --model grok-2-latest
```

## Configuration

`openprompt.yaml`:

```yaml
project: my-project

model:
  provider: ollama
  name: llama3.2

optimizer:
  strategy: hybrid
  max_iterations: 5
  eval_budget: 100

evaluation:
  metrics: [exact_match, format]
  judge:
    provider: ollama
    model: llama3.2

privacy:
  telemetry: false
  storage: local
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `openprompt init` | Create project scaffold |
| `openprompt lint` | Offline prompt analysis |
| `openprompt inspect` | Show parsed AST |
| `openprompt optimize` | Optimize a prompt |
| `openprompt eval` | Run test suite |
| `openprompt compress` | Reduce tokens |
| `openprompt benchmark` | Compare multiple prompts |
| `openprompt compare` | A/B compare on tests |
| `openprompt security` | Security scan |
| `openprompt diff` | Diff two versions |
| `openprompt template` | Built-in templates |

## Python SDK

```python
from openprompt import Optimizer

optimizer = Optimizer(provider="mock", model="mock-model")
result = optimizer.optimize("Summarize this article.")
print(result.prompt)
print(f"Score delta: {result.score_delta:+.1%}")
```

## Providers

| Provider | Install | Env var |
|----------|---------|---------|
| `mock` | (built-in) | — |
| `ollama` | (built-in) | `OLLAMA_HOST` |
| `openai` | `pip install 'openprompt[openai]'` | `OPENAI_API_KEY` |
| `anthropic` | `pip install 'openprompt[anthropic]'` | `ANTHROPIC_API_KEY` |
| `grok` | `pip install 'openprompt[grok]'` | `XAI_API_KEY` |
| `gemini` | `pip install 'openprompt[gemini]'` | `GOOGLE_API_KEY` or `GEMINI_API_KEY` |

Install all cloud providers at once: `pip install 'openprompt[all-providers]'`

## Project Structure

```
openprompt/
├── core/           # AST, parser, linter, compiler, evaluator, optimizer
├── strategies/     # Mutation operators
├── providers/      # Model adapters
├── cli/            # Typer CLI
└── templates/      # Built-in prompt templates
```

## Development

```bash
pip install -e ".[dev]"
pre-commit install
pytest
ruff check openprompt
```

## License

MIT — see [LICENSE](LICENSE).

## Documentation

See [PRD.md](PRD.md) for the full product requirements and roadmap.
