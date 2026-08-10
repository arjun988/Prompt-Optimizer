# Extraction dataset example (Phase 5)

Place PDF or PNG/JPEG samples in `samples/` and optional expected JSON in `labels/<name>.json`.

```bash
# Scaffold a new dataset
openprompt dataset init --name invoice-extraction --path datasets/invoice

# Add files:
#   datasets/invoice/samples/invoice1.pdf
#   datasets/invoice/labels/invoice1.json

# Evaluate prompt against dataset
openprompt dataset eval datasets/invoice/dataset.yaml --prompt prompts/invoice-extraction/prompt.yaml

# Optimize for extraction (few-shot + GRPO + eval validation)
openprompt dataset optimize datasets/invoice/dataset.yaml --prompt prompts/invoice-extraction/prompt.yaml --vision
```

## Vision models

Use `--vision` to attach sample images/PDFs to the prompt for multimodal providers (OpenAI `gpt-4o`, Gemini `gemini-2.0-flash`).

Install media extras:

```bash
pip install 'openprompt[media]'
```

## Strategies

| Strategy | Use case |
|---|---|
| `extraction` | Dataset-linked JSON field extraction |
| `few_shot` | Auto-select diverse examples from pool |
| `rag` | Context budget + citation rules |
| `agent` | System + planning + tool descriptions |
| `grpo` | Meta-model proposes eval-validated patches |

Tune hyperparameters:

```bash
openprompt tune prompts/invoice-extraction/prompt.yaml --trials 30
```
