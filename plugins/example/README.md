# OpenPrompt Plugin Example

Copy this folder into your own repository or install locally:

```bash
cd plugins/example
pip install -e .
```

Then verify the operator is discovered:

```python
from openprompt.plugins.discovery import discover_mutation_operators
assert any(op.name == "uppercase_headers" for op in discover_mutation_operators())
```

Register operators, evaluators, or strategies via `pyproject.toml`:

```toml
[project.entry-points."openprompt.operators"]
my_op = "my_package.operators:MyOperator"

[project.entry-points."openprompt.evaluators"]
my_eval = "my_package.evaluators:evaluate"

[project.entry-points."openprompt.strategies"]
my_strategy = "my_package.strategies:MyStrategy"
```
