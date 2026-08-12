"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import {
  BenchmarkPromptList,
  DEFAULT_BENCHMARK_PROMPTS,
  type BenchmarkPrompt,
} from "@/components/shared/benchmark-prompt-list";
import { BenchmarkResults } from "@/components/shared/benchmark-results";
import { ProviderSelect } from "@/components/shared/provider-select";
import { RunBar } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/status";
import { ApiError, createApiClient, useSettings } from "@/lib/api";
import type { BenchmarkResponse } from "@/lib/types";

export default function BenchmarkPage() {
  const { settings, loaded } = useSettings();
  const [prompts, setPrompts] = useState<BenchmarkPrompt[]>(DEFAULT_BENCHMARK_PROMPTS);
  const [result, setResult] = useState<BenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;

    const filled = prompts
      .map((p) => ({ ...p, content: p.content.trim() }))
      .filter((p) => p.content.length > 0);

    if (filled.length === 0) {
      setError("Add at least one prompt variant with content.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const data = (await createApiClient(settings).benchmark({
        prompts: filled.map((p) => p.content),
        provider: settings.provider,
        model: settings.model,
      })) as BenchmarkResponse;

      const namedEntries = data.entries.map((entry, index) => ({
        ...entry,
        name: filled[index]?.name ?? entry.name,
      }));

      setResult({ ...data, entries: namedEntries });
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Benchmark failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header
        title="Benchmark"
        description="Compare prompt variants side-by-side with lint and eval scores"
      />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
          <div className="flex min-h-0 flex-col border-b border-border p-5 lg:border-b-0 lg:border-r">
            <BenchmarkPromptList prompts={prompts} onChange={setPrompts} className="h-full" />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Running benchmark…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No benchmark report yet"
                description="Add prompt variants on the left, then run to see ranked scores and export a report."
              />
            )}
            {result && !loading && <BenchmarkResults result={result} />}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Run benchmark">
          <ProviderSelect className="min-w-[280px]" />
        </RunBar>
      </main>
    </AppShell>
  );
}
