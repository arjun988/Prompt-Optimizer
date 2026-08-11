"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { ProviderSelect } from "@/components/shared/provider-select";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { RunBar } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState, MetricGrid } from "@/components/shared/status";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, createApiClient, parseTestsYaml, useSettings } from "@/lib/api";
import type { EvaluateResponse } from "@/lib/types";
import { DEFAULT_PROMPT, DEFAULT_TESTS } from "@/lib/types";
import { cn, formatScore, formatUsd } from "@/lib/utils";
import { CheckCircle2, XCircle } from "lucide-react";

export default function EvaluatePage() {
  const { settings, loaded } = useSettings();
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [testsYaml, setTestsYaml] = useState(DEFAULT_TESTS);
  const [result, setResult] = useState<EvaluateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    setLoading(true);
    setError(null);
    try {
      const tests = parseTestsYaml(testsYaml);
      const data = (await createApiClient(settings).evaluate({
        prompt,
        provider: settings.provider,
        model: settings.model,
        tests,
      })) as EvaluateResponse;
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header title="Evaluate" description="Run test suites against your prompt" />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-2">
          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto border-b border-border p-5 xl:border-b-0 xl:border-r">
            <PromptEditor label="Prompt" value={prompt} onChange={setPrompt} rows={8} />
            <PromptEditor
              label="Tests (YAML)"
              value={testsYaml}
              onChange={setTestsYaml}
              rows={14}
              hint="Same format as tests.yaml"
            />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Running evaluation…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No results yet"
                description="Configure provider & tests, then run evaluation."
              />
            )}
            {result && !loading && (
              <div className="space-y-5 animate-fade-in">
                <MetricGrid
                  items={[
                    { label: "Pass rate", value: formatScore(result.pass_rate) },
                    { label: "Accuracy", value: formatScore(result.accuracy) },
                    { label: "Tokens", value: String(result.prompt_tokens) },
                    { label: "Cost", value: formatUsd(result.total_cost_usd) },
                  ]}
                />

                {result.warnings.length > 0 && (
                  <div className="space-y-1">
                    {result.warnings.map((w, i) => (
                      <Badge key={i} variant="warning" className="mr-2 normal-case">
                        {w}
                      </Badge>
                    ))}
                  </div>
                )}

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Test results
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 pt-0">
                    {result.results.map((r) => (
                      <div
                        key={r.name}
                        className={cn(
                          "flex items-start gap-3 rounded-md border border-border p-3",
                          r.passed ? "bg-success/5" : "bg-destructive/5",
                        )}
                      >
                        {r.passed ? (
                          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                        ) : (
                          <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
                        )}
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-medium">{r.name}</p>
                            <span className="text-xs text-muted-foreground">
                              {(r.score * 100).toFixed(0)}%
                            </span>
                          </div>
                          {r.message && (
                            <p className="mt-1 text-xs text-muted-foreground">{r.message}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Run evaluation">
          <ProviderSelect className="min-w-[280px]" />
        </RunBar>
      </main>
    </AppShell>
  );
}
