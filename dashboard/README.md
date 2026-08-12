# OpenPrompt Dashboard

Web UI for OpenPrompt — a Cursor-inspired black/white/gray workspace with dark and light mode.

## Features

- **Overview** — quick navigation and setup guide
- **Lint** — heuristic prompt quality (offline, no API key)
- **Evaluate** — run test suites (YAML, JSON, or CSV)
- **Dataset** — upload PDFs/images + labels, eval & optimize extraction prompts
- **Optimize** — reinforcement & other strategies; YAML/JSON/CSV tests; eval budget for hybrid/evolutionary
- **Benchmark** — compare named prompt variants with ranked score cards
- **Multi-Model** — cross-provider optimization
- **Settings** — API URL, key, connection test

## Setup

```bash
# From repo root — start the API
pip install -e ".[server]"
openprompt serve

# Dashboard (separate terminal)
cd dashboard
npm install
cp .env.example .env.local   # optional
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### API keys

In **Settings → Provider API keys**, add OpenAI, Anthropic (Claude), Gemini, Grok, and/or OpenRouter keys. They are stored in your browser (localStorage) and sent to the OpenPrompt server with each evaluate/optimize request. You can then pick any provider/model on Lint, Evaluate, Optimize, Dataset, etc.

The **OpenPrompt API key** field is separate — only needed if you set `OPENPROMPT_API_KEY` on the server.

For CORS from the browser:

```bash
set OPENPROMPT_CORS_ORIGINS=http://localhost:3000
openprompt serve
```

## Stack

- Next.js 15 (App Router)
- TypeScript
- Tailwind CSS
- next-themes (dark/light)
- Lucide icons

No install was run when scaffolding — run `npm install` locally before `npm run dev`.
