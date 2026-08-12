"use client";

import { useState } from "react";
import { Copy, Check, Trophy, ChevronDown, ChevronUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { BenchmarkEntry, BenchmarkResponse } from "@/lib/types";
import { cn, formatScore, formatUsd } from "@/lib/utils";

function ScoreBar({
  label,
  value,
  scale = "unit",
}: {
  label: string;
  value: number;
  scale?: "unit" | "percent";
}) {
  const pct = scale === "unit" ? value * 100 : value;
  const display = scale === "unit" ? formatScore(value) : `${Math.round(value)}/100`;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums text-foreground">{display}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
        <div
          className={cn(
            "h-full rounded-full transition-all",
            pct >= 85 ? "bg-success" : pct >= 60 ? "bg-warning" : "bg-destructive/70",
          )}
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
    </div>
  );
}

function BenchmarkEntryCard({
  entry,
  rank,
  isWinner,
}: {
  entry: BenchmarkEntry;
  rank: number;
  isWinner: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border p-4 transition-colors",
        isWinner ? "border-success/30 bg-success/5" : "border-border bg-muted/10",
      )}
    >
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full border border-border bg-background text-xs font-semibold tabular-nums">
            {rank}
          </span>
          <div>
            <p className="text-sm font-medium text-foreground">{entry.name}</p>
            <p className="text-[11px] text-muted-foreground">{entry.tokens} tokens</p>
          </div>
        </div>
        {isWinner && (
          <Badge variant="success" className="normal-case gap-1">
            <Trophy className="h-3 w-3" />
            Top score
          </Badge>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <ScoreBar label="Lint" value={entry.lint_score} scale="percent" />
        <ScoreBar label="Eval accuracy" value={entry.eval_score} />
        <ScoreBar label="Pass rate" value={entry.pass_rate} />
        {entry.judge_score != null && (
          <ScoreBar label="Judge score" value={entry.judge_score} />
        )}
      </div>

      <div className="mt-3 flex flex-wrap gap-3 border-t border-border pt-3 text-[11px] text-muted-foreground">
        <span>Latency: {Math.round(entry.latency_ms)} ms</span>
        <span>Cost: {formatUsd(entry.cost_usd)}</span>
      </div>
    </div>
  );
}

export function BenchmarkResults({ result }: { result: BenchmarkResponse }) {
  const [showMarkdown, setShowMarkdown] = useState(false);
  const [copied, setCopied] = useState(false);

  const entries = [...result.entries].sort((a, b) => b.eval_score - a.eval_score);
  const topScore = entries[0]?.eval_score ?? 0;

  const copyReport = async () => {
    await navigator.clipboard.writeText(result.markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground">
          Generated {new Date(result.generated_at).toLocaleString()} · {entries.length} variant
          {entries.length !== 1 ? "s" : ""}
        </p>
        <Button type="button" variant="outline" size="sm" onClick={copyReport}>
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied" : "Copy markdown"}
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <p className="metric-label">Best eval score</p>
            <p className="metric-value mt-1">{formatScore(topScore)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="metric-label">Best lint score</p>
            <p className="metric-value mt-1">
              {Math.max(...entries.map((e) => e.lint_score), 0)}/100
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="metric-label">Variants tested</p>
            <p className="metric-value mt-1">{entries.length}</p>
          </CardContent>
        </Card>
      </div>

      <div className="space-y-3">
        {entries.map((entry, index) => (
          <BenchmarkEntryCard
            key={`${entry.name}-${index}`}
            entry={entry}
            rank={index + 1}
            isWinner={index === 0 && entry.eval_score > 0}
          />
        ))}
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between py-3">
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground">
            Markdown report
          </CardTitle>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => setShowMarkdown((v) => !v)}
          >
            {showMarkdown ? (
              <>
                Hide <ChevronUp className="h-3.5 w-3.5" />
              </>
            ) : (
              <>
                Show <ChevronDown className="h-3.5 w-3.5" />
              </>
            )}
          </Button>
        </CardHeader>
        {showMarkdown && (
          <CardContent className="pt-0">
            <pre className="overflow-x-auto rounded-md bg-muted/20 p-4 font-mono text-xs leading-relaxed">
              {result.markdown}
            </pre>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
