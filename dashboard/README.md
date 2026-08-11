# OpenPrompt Dashboard

Web UI for OpenPrompt — a Cursor-inspired black/white/gray workspace with dark and light mode.

## Features

- **Overview** — quick navigation and setup guide
- **Lint** — heuristic prompt quality (offline, no API key)
- **Evaluate** — run YAML test suites
- **Dataset** — upload PDFs/images + labels, eval & optimize extraction prompts
- **Optimize** — all strategies (hybrid, evolutionary, RAG, agent, GRPO, …)
- **Compress** — token reduction
- **Benchmark** — multi-prompt comparison
- **Multi-Model** — cross-provider optimization
- **Cost** — Pareto quality/cost recommendations
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

If the API uses auth, set `OPENPROMPT_API_KEY` on the server and the same value in **Settings** (or `NEXT_PUBLIC_API_KEY` in `.env.local`).

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
