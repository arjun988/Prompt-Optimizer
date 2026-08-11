"use client";

import { useState } from "react";
import { CheckCircle2, XCircle } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import {
  buildDatasetFormData,
  FileUploadZone,
  type SampleFile,
} from "@/components/shared/file-upload";
import { ProviderSelect } from "@/components/shared/provider-select";
import { PromptEditor } from "@/components/shared/prompt-editor";
import { EmptyState, ErrorState, LoadingState, MetricGrid } from "@/components/shared/status";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Textarea } from "@/components/ui/input";
import { ApiError, createApiClient, useSettings } from "@/lib/api";
import type { DatasetEvalResponse, DatasetOptimizeResponse } from "@/lib/types";
import {
  DEFAULT_EXTRACTION_PROMPT,
  DEFAULT_EXTRACTION_SCHEMA,
} from "@/lib/types";
import { cn, formatPercent, formatScore, formatUsd } from "@/lib/utils";

type Mode = "eval" | "optimize";

export default function DatasetPage() {
  const { settings, loaded } = useSettings();
  const [mode, setMode] = useState<Mode>("eval");
  const [prompt, setPrompt] = useState(DEFAULT_EXTRACTION_PROMPT);
  const [schema, setSchema] = useState(DEFAULT_EXTRACTION_SCHEMA);
  const [datasetName, setDatasetName] = useState("extraction-upload");
  const [samples, setSamples] = useState<SampleFile[]>([]);
  const [vision, setVision] = useState(false);
  const [evalResult, setEvalResult] = useState<DatasetEvalResponse | null>(null);
  const [optResult, setOptResult] = useState<DatasetOptimizeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    if (!loaded) return;
    if (samples.length === 0) {
      setError("Upload at least one PDF or image sample.");
      return;
    }

    setLoading(true);
    setError(null);
    setEvalResult(null);
    setOptResult(null);

    try {
      const form = buildDatasetFormData({
        prompt,
        provider: settings.provider,
        model: settings.model,
        schema,
        datasetName,
        samples,
        strategy: "extraction",
        vision: mode === "optimize" ? vision : undefined,
      });

      const client = createApiClient(settings);
      if (mode === "eval") {
        setEvalResult((await client.datasetEval(form)) as DatasetEvalResponse);
      } else {
        setOptResult((await client.datasetOptimize(form)) as DatasetOptimizeResponse);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppShell>
      <Header
        title="Dataset"
        description="Upload PDFs/images, label expected JSON, eval & optimize extraction prompts"
      />
      <main className="flex flex-1 flex-col overflow-hidden">
        <div className="grid min-h-0 flex-1 grid-cols-1 xl:grid-cols-2">
          <div className="flex min-h-0 flex-col gap-4 overflow-y-auto border-b border-border p-5 xl:border-b-0 xl:border-r">
            <div className="flex gap-1 rounded-md border border-border bg-muted/20 p-1">
              {(["eval", "optimize"] as Mode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => setMode(m)}
                  className={cn(
                    "flex-1 rounded-sm px-3 py-1.5 text-xs font-medium capitalize transition-colors",
                    mode === m
                      ? "bg-background text-foreground shadow-subtle"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {m === "eval" ? "Evaluate" : "Optimize"}
                </button>
              ))}
            </div>

            <PromptEditor label="Extraction prompt" value={prompt} onChange={setPrompt} rows={6} />

            <div className="space-y-1.5">
              <Label>JSON schema (optional)</Label>
              <Textarea
                value={schema}
                onChange={(e) => setSchema(e.target.value)}
                rows={8}
                className="font-mono text-xs"
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="datasetName">Dataset name</Label>
              <Input
                id="datasetName"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
              />
            </div>

            <FileUploadZone samples={samples} onChange={setSamples} />

            {mode === "optimize" && (
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={vision}
                  onChange={(e) => setVision(e.target.checked)}
                  className="rounded border-border"
                />
                <span>Vision mode — attach first sample for multimodal models</span>
              </label>
            )}
          </div>

          <div className="flex min-h-0 flex-col overflow-y-auto p-5">
            {loading && (
              <LoadingState
                label={mode === "eval" ? "Evaluating on uploaded dataset…" : "Optimizing extraction prompt…"}
              />
            )}
            {error && !loading && <ErrorState message={error} />}
            {!loading && !error && !evalResult && !optResult && (
              <EmptyState
                title="No dataset results"
                description="Upload labeled PDFs or images, then evaluate or optimize your extraction prompt."
              />
            )}

            {evalResult && !loading && (
              <div className="space-y-5 animate-fade-in">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="normal-case">
                    {evalResult.dataset_name} · {evalResult.sample_count} samples
                  </Badge>
                </div>
                <MetricGrid
                  items={[
                    { label: "Pass rate", value: formatScore(evalResult.pass_rate) },
                    { label: "Accuracy", value: formatScore(evalResult.accuracy) },
                    { label: "Cost", value: formatUsd(evalResult.total_cost_usd) },
                    { label: "Latency", value: `${evalResult.total_latency_ms.toFixed(0)} ms` },
                  ]}
                />
                <ResultsList results={evalResult.results} />
              </div>
            )}

            {optResult && !loading && (
              <div className="space-y-5 animate-fade-in">
                <div className="flex flex-wrap gap-2">
                  <Badge variant="outline" className="normal-case">
                    {optResult.dataset_name} · {optResult.sample_count} samples
                  </Badge>
                  {optResult.vision_enabled && (
                    <Badge variant="outline" className="normal-case">
                      Vision enabled
                    </Badge>
                  )}
                </div>
                <MetricGrid
                  items={[
                    {
                      label: "Score",
                      value: formatScore(optResult.optimized_score),
                      delta: `${optResult.score_delta >= 0 ? "+" : ""}${(optResult.score_delta * 100).toFixed(1)} pts`,
                      positive: optResult.score_delta >= 0,
                    },
                    {
                      label: "Tokens",
                      value: String(optResult.optimized_tokens),
                      delta: formatPercent(optResult.token_delta_pct),
                      positive: optResult.token_delta_pct <= 0,
                    },
                    {
                      label: "Strategy",
                      value: optResult.strategy,
                    },
                    {
                      label: "Original",
                      value: formatScore(optResult.original_score),
                    },
                  ]}
                />
                <PromptEditor
                  label="Optimized prompt"
                  value={optResult.prompt}
                  onChange={() => {}}
                  rows={12}
                  readOnly
                />
                {optResult.report_lines.length > 0 && (
                  <pre className="overflow-x-auto rounded-md border border-border bg-muted/20 p-4 font-mono text-xs leading-relaxed text-muted-foreground">
                    {optResult.report_lines.join("\n")}
                  </pre>
                )}
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-end justify-between gap-4 border-t border-border bg-muted/10 px-5 py-4">
          <ProviderSelect className="min-w-[280px]" />
          <Button
            onClick={run}
            disabled={loading || samples.length === 0}
            className="min-w-[160px]"
          >
            {loading
              ? "Running…"
              : mode === "eval"
                ? "Run dataset eval"
                : "Run dataset optimize"}
          </Button>
        </div>
      </main>
    </AppShell>
  );
}

function ResultsList({
  results,
}: {
  results: { name: string; passed: boolean; score: number; message: string }[];
}) {
  return (
    <Card>
      <CardHeader className="py-3">
        <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
          Per-sample results
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 pt-0">
        {results.map((r) => (
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
  );
}
