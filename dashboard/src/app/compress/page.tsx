"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { ProviderSelect } from "@/components/shared/provider-select";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { RunBar } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState, MetricGrid } from "@/components/shared/status";
import { ApiError, createApiClient, useSettings } from "@/lib/api";
import type { OptimizeResponse } from "@/lib/types";
import { DEFAULT_PROMPT } from "@/lib/types";
import { formatPercent, formatUsd } from "@/lib/utils";

export default function CompressPage() {
  const { settings, loaded } = useSettings();
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    setLoading(true);
    setError(null);
    try {
      const data = (await createApiClient(settings).compress({
        prompt,
        provider: settings.provider,
        model: settings.model,
      })) as OptimizeResponse;
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Compression failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header title="Compress" description="Reduce token count while preserving intent" />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
          <div className="flex min-h-0 flex-col border-b border-border p-5 lg:border-b-0 lg:border-r">
            <PromptEditor label="Original prompt" value={prompt} onChange={setPrompt} rows={18} />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Compressing…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No compressed output"
                description="Run compress to see token and cost savings."
              />
            )}
            {result && !loading && (
              <div className="space-y-5 animate-fade-in">
                <MetricGrid
                  items={[
                    {
                      label: "Tokens saved",
                      value: `${result.original_tokens - result.optimized_tokens}`,
                      delta: formatPercent(result.token_delta_pct),
                      positive: result.token_delta_pct < 0,
                    },
                    {
                      label: "New tokens",
                      value: String(result.optimized_tokens),
                    },
                    {
                      label: "Cost delta",
                      value: formatUsd(result.optimized_cost_usd),
                      delta: formatPercent(result.cost_delta_pct),
                      positive: result.cost_delta_pct <= 0,
                    },
                    {
                      label: "Original tokens",
                      value: String(result.original_tokens),
                    },
                  ]}
                />
                <PromptEditor
                  label="Compressed prompt"
                  value={result.prompt}
                  onChange={() => {}}
                  rows={14}
                  readOnly
                />
              </div>
            )}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Run compress">
          <ProviderSelect className="min-w-[280px]" />
        </RunBar>
      </main>
    </AppShell>
  );
}
