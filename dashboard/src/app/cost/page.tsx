"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { ProviderSelect } from "@/components/shared/provider-select";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { RunBar, StrategySelect } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/status";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { ApiError, createApiClient, useSettings } from "@/lib/api";
import type { CostRecommendResponse } from "@/lib/types";
import { DEFAULT_PROMPT } from "@/lib/types";

export default function CostPage() {
  const { settings, loaded } = useSettings();
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [strategy, setStrategy] = useState("rewrite");
  const [minQuality, setMinQuality] = useState("0.85");
  const [result, setResult] = useState<CostRecommendResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    setLoading(true);
    setError(null);
    try {
      const data = (await createApiClient(settings).costRecommend({
        prompt,
        strategy,
        provider: settings.provider,
        model: settings.model,
        min_quality: minQuality ? parseFloat(minQuality) : undefined,
      })) as CostRecommendResponse;
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Cost recommendation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header title="Cost" description="Quality vs cost Pareto recommendations" />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
          <div className="flex min-h-0 flex-col border-b border-border p-5 lg:border-b-0 lg:border-r">
            <PromptEditor label="Prompt" value={prompt} onChange={setPrompt} rows={18} />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Computing recommendations…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No recommendation"
                description="Run to get Pareto frontier and quality-per-dollar analysis."
              />
            )}
            {result && !loading && (
              <div className="space-y-5 animate-fade-in">
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-sm">Recommendation</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 pt-0">
                    <p className="text-sm leading-relaxed text-muted-foreground">{result.reason}</p>
                    <p className="text-xs text-muted-foreground">
                      Quality per dollar:{" "}
                      <span className="font-medium text-foreground">
                        {result.quality_per_dollar.toFixed(2)}
                      </span>
                    </p>
                    <pre className="overflow-x-auto rounded-md border border-border bg-muted/20 p-4 font-mono text-xs">
                      {JSON.stringify(result.recommended, null, 2)}
                    </pre>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Pareto frontier ({result.pareto_frontier.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 pt-0">
                    {result.pareto_frontier.map((point, i) => (
                      <pre
                        key={i}
                        className="rounded-md border border-border p-3 font-mono text-xs"
                      >
                        {JSON.stringify(point, null, 2)}
                      </pre>
                    ))}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Get recommendation">
          <StrategySelect value={strategy} onChange={setStrategy} />
          <div className="space-y-1.5">
            <Label htmlFor="minQuality">Min quality (0–1)</Label>
            <Input
              id="minQuality"
              value={minQuality}
              onChange={(e) => setMinQuality(e.target.value)}
              className="w-28"
            />
          </div>
          <ProviderSelect className="min-w-[280px]" />
        </RunBar>
      </main>
    </AppShell>
  );
}
