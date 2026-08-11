export interface HealthResponse {
  status: string;
  version: string;
}

export interface LintIssue {
  code: string;
  message: string;
  severity: string;
  recommendation?: string | null;
}

export interface LintResponse {
  score: number;
  issues: LintIssue[];
  categories: Record<string, number>;
}

export interface OptimizeResponse {
  prompt: string;
  original_score: number;
  optimized_score: number;
  score_delta: number;
  original_tokens: number;
  optimized_tokens: number;
  token_delta_pct: number;
  original_cost_usd: number;
  optimized_cost_usd: number;
  cost_delta_pct: number;
  strategy: string;
  report_lines: string[];
  warnings: string[];
}

export interface EvaluateResult {
  name: string;
  passed: boolean;
  score: number;
  message: string;
}

export interface EvaluateResponse {
  accuracy: number;
  pass_rate: number;
  prompt_tokens: number;
  total_cost_usd: number;
  total_latency_ms: number;
  judge_score: number | null;
  warnings: string[];
  results: EvaluateResult[];
}

export interface BenchmarkResponse {
  generated_at: string;
  entries: Record<string, unknown>[];
  markdown: string;
}

export interface MultiModelResponse {
  markdown_table: string;
  rows: Record<string, unknown>[];
  best_quality_model: string | null;
  lowest_cost_model: string | null;
}

export interface CostRecommendResponse {
  recommended: Record<string, unknown>;
  pareto_frontier: Record<string, unknown>[];
  reason: string;
  quality_per_dollar: number;
}

export interface DatasetSampleInfo {
  name: string;
  media_path: string | null;
  has_expected: boolean;
}

export interface DatasetEvalResponse {
  accuracy: number;
  pass_rate: number;
  prompt_tokens: number;
  total_cost_usd: number;
  total_latency_ms: number;
  judge_score: number | null;
  warnings: string[];
  results: EvaluateResult[];
  dataset_name: string;
  sample_count: number;
  samples: DatasetSampleInfo[];
}

export interface DatasetOptimizeResponse extends OptimizeResponse {
  dataset_name: string;
  sample_count: number;
  vision_enabled: boolean;
}

export interface ApiSettings {
  baseUrl: string;
  apiKey: string;
  provider: string;
  model: string;
}

export const STRATEGIES = [
  "hybrid",
  "rewrite",
  "iterative",
  "evolutionary",
  "compress",
  "rag",
  "agent",
  "grpo",
  "few_shot",
  "extraction",
] as const;

export { PROVIDERS, providerById } from "./models";
export type { ProviderDef } from "./models";

export const DEFAULT_PROMPT = `Summarize this article.`;

export const DEFAULT_EXTRACTION_PROMPT = `Extract structured fields from the document as JSON.
Return only valid JSON matching the schema.`;

export const DEFAULT_EXTRACTION_SCHEMA = `{
  "type": "object",
  "required": ["vendor", "date", "total"],
  "properties": {
    "vendor": { "type": "string" },
    "date": { "type": "string" },
    "total": { "type": "number" }
  }
}`;

export const ACCEPTED_MEDIA_TYPES = [
  ".pdf",
  ".png",
  ".jpg",
  ".jpeg",
  ".webp",
  ".tiff",
  ".gif",
  ".txt",
].join(",");

export const DEFAULT_TESTS = `tests:
  - name: summary_has_bullets
    input: |
      Artificial intelligence is reshaping healthcare through faster diagnosis,
      personalized treatment plans, and operational automation.
    metric: contains
    expected: "-"

  - name: summary_covers_topic
    input: "Remote work increased productivity for knowledge workers in 2024."
    metric: contains
    expected: "remote"

  - name: non_empty_response
    input: "The market grew 12% year over year."
    metric: regex
    pattern: ".{10,}"`;

export const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: "LayoutDashboard" },
  { href: "/lint", label: "Lint", icon: "ScanSearch" },
  { href: "/evaluate", label: "Evaluate", icon: "FlaskConical" },
  { href: "/dataset", label: "Dataset", icon: "FileStack" },
  { href: "/optimize", label: "Optimize", icon: "Sparkles" },
  { href: "/compress", label: "Compress", icon: "Minimize2" },
  { href: "/benchmark", label: "Benchmark", icon: "BarChart3" },
  { href: "/multi-model", label: "Multi-Model", icon: "Layers" },
  { href: "/cost", label: "Cost", icon: "DollarSign" },
  { href: "/settings", label: "Settings", icon: "Settings" },
] as const;
