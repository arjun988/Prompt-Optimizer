"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { RunBar } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/status";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiError, createApiClient, useSettings } from "@/lib/api";
import type { LintResponse } from "@/lib/types";
import { DEFAULT_PROMPT } from "@/lib/types";

export default function LintPage() {
  const { settings, loaded } = useSettings();
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [result, setResult] = useState<LintResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    setLoading(true);
    setError(null);
    try {
      const data = (await createApiClient(settings).lint(prompt)) as LintResponse;
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Lint failed");
    } finally {
      setLoading(false);
    }
  };

  const severityVariant = (s: string) => {
    if (s === "error") return "destructive";
    if (s === "warning") return "warning";
    return "outline";
  };

  return (
    <AppShell>
      <Header title="Lint" description="Offline heuristic quality analysis" />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 lg:grid-cols-2">
          <div className="flex min-h-0 flex-col border-b border-border p-5 lg:border-b-0 lg:border-r">
            <PromptEditor
              label="Prompt"
              value={prompt}
              onChange={setPrompt}
              rows={20}
              hint="Uses mock provider — no API key"
            />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Analyzing prompt…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No lint report yet"
                description="Run lint to see quality score, categories, and actionable issues."
              />
            )}
            {result && !loading && (
              <div className="space-y-5 animate-fade-in">
                <div className="flex items-center gap-4">
                  <div>
                    <p className="metric-label">Quality score</p>
                    <p className="text-4xl font-semibold tracking-tight">{result.score}</p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(result.categories).map(([k, v]) => (
                      <Badge key={k} variant="outline" className="normal-case">
                        {k}: {v}
                      </Badge>
                    ))}
                  </div>
                </div>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Issues ({result.issues.length})
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3 pt-0">
                    {result.issues.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No issues found.</p>
                    ) : (
                      result.issues.map((issue, i) => (
                        <div
                          key={`${issue.code}-${i}`}
                          className="rounded-md border border-border p-3"
                        >
                          <div className="mb-1 flex items-center gap-2">
                            <Badge variant={severityVariant(issue.severity)} className="normal-case">
                              {issue.severity}
                            </Badge>
                            <code className="text-[11px] text-muted-foreground">{issue.code}</code>
                          </div>
                          <p className="text-sm">{issue.message}</p>
                          {issue.recommendation && (
                            <p className="mt-2 text-xs text-muted-foreground">
                              {issue.recommendation}
                            </p>
                          )}
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Run lint" />
      </main>
    </AppShell>
  );
}
