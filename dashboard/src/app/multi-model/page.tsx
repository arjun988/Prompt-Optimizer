"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { RunBar, StrategySelect } from "@/components/shared/run-bar";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/status";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label, Textarea } from "@/components/ui/input";
import { ApiError, createApiClient, parseTestsYaml, useSettings } from "@/lib/api";
import type { MultiModelResponse } from "@/lib/types";
import { DEFAULT_PROMPT, DEFAULT_TESTS } from "@/lib/types";

const DEFAULT_MODELS = `mock:mock-model
openai:gpt-5.6-terra
anthropic:claude-sonnet-5
google/gemini-3.6-flash
x-ai/grok-4.3`;

function parseModels(raw: string) {
  return raw
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      if (line.includes(":")) {
        const [provider, model] = line.split(":", 2);
        return { provider: provider.trim(), model: model.trim() };
      }
      return line;
    });
}

export default function MultiModelPage() {
  const { settings, loaded } = useSettings();
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [testsYaml, setTestsYaml] = useState(DEFAULT_TESTS);
  const [modelsText, setModelsText] = useState(DEFAULT_MODELS);
  const [strategy, setStrategy] = useState("rewrite");
  const [result, setResult] = useState<MultiModelResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    setLoading(true);
    setError(null);
    try {
      const tests = parseTestsYaml(testsYaml);
      const models = parseModels(modelsText);
      const data = (await createApiClient(settings).multiModel({
        prompt,
        models,
        strategy,
        tests,
      })) as MultiModelResponse;
      setResult(data);
    } catch (e) {
      setResult(null);
      setError(e instanceof ApiError ? e.message : "Multi-model optimize failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header title="Multi-Model" description="Compare optimization across providers" />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-2">
          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto border-b border-border p-5 xl:border-b-0 xl:border-r">
            <PromptEditor label="Prompt" value={prompt} onChange={setPrompt} rows={6} />
            <div className="space-y-1.5">
              <Label>Models (one per line: provider:model)</Label>
              <Textarea
                value={modelsText}
                onChange={(e) => setModelsText(e.target.value)}
                rows={5}
                className="font-mono text-sm"
              />
            </div>
            <PromptEditor
              label="Tests (YAML)"
              value={testsYaml}
              onChange={setTestsYaml}
              rows={10}
            />
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && <LoadingState label="Running across models…" />}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !result && (
              <EmptyState
                title="No comparison yet"
                description="Add models and run to see quality vs cost tradeoffs."
              />
            )}
            {result && !loading && (
              <div className="space-y-5 animate-fade-in">
                <div className="flex flex-wrap gap-2">
                  {result.best_quality_model && (
                    <Badge variant="success" className="normal-case">
                      Best quality: {result.best_quality_model}
                    </Badge>
                  )}
                  {result.lowest_cost_model && (
                    <Badge variant="outline" className="normal-case">
                      Lowest cost: {result.lowest_cost_model}
                    </Badge>
                  )}
                </div>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Results table
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="overflow-x-auto pt-0">
                    <pre className="font-mono text-xs leading-relaxed whitespace-pre">
                      {result.markdown_table}
                    </pre>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
                      Raw rows
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2 pt-0">
                    {result.rows.map((row, i) => (
                      <pre
                        key={i}
                        className="rounded-md border border-border bg-muted/20 p-3 font-mono text-xs"
                      >
                        {JSON.stringify(row, null, 2)}
                      </pre>
                    ))}
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </div>

        <RunBar onRun={run} loading={loading} label="Run comparison">
          <StrategySelect value={strategy} onChange={setStrategy} />
        </RunBar>
      </main>
    </AppShell>
  );
}
