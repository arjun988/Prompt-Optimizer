"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { ProviderSelect } from "@/components/shared/provider-select";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { RunBar } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/status";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, createApiClient, useSettings } from "@/lib/api";
import type { BenchmarkResponse } from "@/lib/types";

const DEFAULT_PROMPTS = `Summarize this article in 3 bullet points.

Extract key entities from the text as JSON.

Classify the sentiment as positive, negative, or neutral.`;

export default function BenchmarkPage() {
  const { settings, loaded } = useSettings();
  const [promptsText, setPromptsText] = useState(DEFAULT_PROMPTS);
  const [result, setResult] = useState<BenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    setLoading(true);
    setError(null);
    try {
      const prompts = promptsText
        .split(/\n\s*\n/)
        .map((p) => p.trim())
        .filter(Boolean);
      const data = (await createApiClient(settings).benchmark({
        prompts,
        provider: settings.provider,
        model: settings.model,
      })) as BenchmarkResponse;
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Benchmark failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header title="Benchmark" description="Compare multiple prompts side-by-side" />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
          <div className="flex min-h-0 flex-col border-b border-border p-5 lg:border-b-0 lg:border-r">
            <PromptEditor
              label="Prompts"
              value={promptsText}
              onChange={setPromptsText}
              rows={20}
              hint="Separate prompts with a blank line"
            />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Running benchmark…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No benchmark report"
                description="Add prompts and run to generate scores and markdown export."
              />
            )}
            {result && !loading && (
              <div className="space-y-5 animate-fade-in">
                <p className="text-xs text-muted-foreground">
                  Generated {new Date(result.generated_at).toLocaleString()}
                </p>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Entries
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 pt-0">
                    {result.entries.map((entry, i) => (
                      <div
                        key={i}
                        className="rounded-md border border-border p-3 font-mono text-xs"
                      >
                        <pre className="whitespace-pre-wrap break-words">
                          {JSON.stringify(entry, null, 2)}
                        </pre>
                      </div>
                    ))}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Markdown report
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <pre className="overflow-x-auto rounded-md bg-muted/20 p-4 font-mono text-xs leading-relaxed">
                      {result.markdown}
                    </pre>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Run benchmark">
          <ProviderSelect className="min-w-[280px]" />
        </RunBar>
      </main>
    </AppShell>
  );
}
