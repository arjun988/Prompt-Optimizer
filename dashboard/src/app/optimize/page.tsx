"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { ProviderSelect } from "@/components/shared/provider-select";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { RunBar, StrategySelect } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState, MetricGrid } from "@/components/shared/status";
import { Badge } from "@/components/ui/badge";
import { ApiError, createApiClient, parseTestsYaml, useSettings } from "@/lib/api";
import type { OptimizeResponse } from "@/lib/types";
import { DEFAULT_PROMPT, DEFAULT_TESTS } from "@/lib/types";
import { formatPercent, formatScore, formatUsd } from "@/lib/utils";

export default function OptimizePage() {
  const { settings, loaded } = useSettings();
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [testsYaml, setTestsYaml] = useState(DEFAULT_TESTS);
  const [strategy, setStrategy] = useState("hybrid");
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    setLoading(true);
    setError(null);
    try {
      const tests = parseTestsYaml(testsYaml);
      const data = (await createApiClient(settings).optimize({
        prompt,
        strategy,
        provider: settings.provider,
        model: settings.model,
        tests,
      })) as OptimizeResponse;
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Optimization failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header title="Optimize" description="Evaluation-driven prompt improvement" />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-2">
          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto border-b border-border p-5 xl:border-b-0 xl:border-r">
            <PromptEditor label="Original prompt" value={prompt} onChange={setPrompt} rows={8} />
            <PromptEditor
              label="Tests (YAML)"
              value={testsYaml}
              onChange={setTestsYaml}
              rows={12}
            />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Optimizing prompt…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No optimization yet"
                description="Pick a strategy and run — results appear here with before/after metrics."
              />
            )}
            {result && !loading && (
              <div className="space-y-5 animate-fade-in">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className="normal-case">
                    Strategy: {result.strategy}
                  </Badge>
                  {result.warnings.map((w, i) => (
                    <Badge key={i} variant="warning" className="normal-case">
                      {w}
                    </Badge>
                  ))}
                </div>

                <MetricGrid
                  items={[
                    {
                      label: "Score",
                      value: formatScore(result.optimized_score),
                      delta: `${result.score_delta >= 0 ? "+" : ""}${(result.score_delta * 100).toFixed(1)} pts`,
                      positive: result.score_delta >= 0,
                    },
                    {
                      label: "Tokens",
                      value: String(result.optimized_tokens),
                      delta: formatPercent(result.token_delta_pct),
                      positive: result.token_delta_pct <= 0,
                    },
                    {
                      label: "Cost",
                      value: formatUsd(result.optimized_cost_usd),
                      delta: formatPercent(result.cost_delta_pct),
                      positive: result.cost_delta_pct <= 0,
                    },
                    {
                      label: "Original score",
                      value: formatScore(result.original_score),
                    },
                  ]}
                />

                <PromptEditor
                  label="Optimized prompt"
                  value={result.prompt}
                  onChange={() => {}}
                  rows={10}
                  readOnly
                />

                {result.report_lines.length > 0 && (
                  <pre className="overflow-x-auto rounded-md border border-border bg-muted/20 p-4 font-mono text-xs leading-relaxed text-muted-foreground">
                    {result.report_lines.join("\n")}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Run optimize">
          <StrategySelect value={strategy} onChange={setStrategy} />
          <ProviderSelect className="min-w-[280px]" />
        </RunBar>
      </main>
    </AppShell>
  );
}
