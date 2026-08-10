# OpenPrompt Plugin Example

This directory demonstrates how to publish OpenPrompt plugins as a **standalone package**.

## Install locally

```bash
pip install -e ./plugins/example
pip install -e ..  # OpenPrompt core
```

## Entry points

The example registers:

- `openprompt.operators` — custom mutation operator
- `openprompt.evaluators` — custom evaluator (`contains`)
- `openprompt.strategies` — custom strategy (`passthrough_rewrite`)

Verify discovery:

```bash
python -c "from openprompt.plugins.discovery import discover_strategies; print(discover_strategies().keys())"
```

## Publish

Copy this folder to its own repository, add `pyproject.toml` with `[project.entry-points]`, and publish to PyPI.
