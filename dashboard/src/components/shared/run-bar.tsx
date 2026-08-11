"use client";

import { Button } from "@/components/ui/button";
import { Label, Select } from "@/components/ui/input";
import { DEFAULT_EVAL_BUDGET, estimateOptimizeApiCalls, usesEvalBudget } from "@/lib/optimize-budget";
import { STRATEGIES } from "@/lib/types";

interface StrategySelectProps {
  value: string;
  onChange: (value: string) => void;
}

export function StrategySelect({ value, onChange }: StrategySelectProps) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="strategy">Strategy</Label>
      <Select id="strategy" value={value} onChange={(e) => onChange(e.target.value)}>
        {STRATEGIES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </Select>
    </div>
  );
}

interface EvalBudgetSelectProps {
  strategy: string;
  value: number;
  onChange: (value: number) => void;
  testCount: number;
  modelCount?: number;
}

const EVAL_BUDGET_PRESETS = [10, 25, 50, 100, 200];

export function EvalBudgetSelect({
  strategy,
  value,
  onChange,
  testCount,
  modelCount = 1,
}: EvalBudgetSelectProps) {
  if (!usesEvalBudget(strategy)) {
    return null;
  }

  const estimate = estimateOptimizeApiCalls(strategy, value, testCount, modelCount);

  return (
    <div className="space-y-1.5">
      <Label htmlFor="eval-budget">Eval rounds (API budget)</Label>
      <Select
        id="eval-budget"
        value={String(value)}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {EVAL_BUDGET_PRESETS.map((n) => (
          <option key={n} value={n}>
            {n} rounds
          </option>
        ))}
      </Select>
      {estimate.label && (
        <p className="text-[10px] leading-snug text-muted-foreground">{estimate.label}</p>
      )}
    </div>
  );
}

export { DEFAULT_EVAL_BUDGET };

interface RunBarProps {
  onRun: () => void;
  loading?: boolean;
  disabled?: boolean;
  label?: string;
  children?: React.ReactNode;
}

export function RunBar({
  onRun,
  loading,
  disabled,
  label = "Run",
  children,
}: RunBarProps) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4 border-t border-border bg-muted/10 px-5 py-4">
      <div className="flex flex-1 flex-wrap items-end gap-4">{children}</div>
      <Button onClick={onRun} disabled={disabled || loading} className="min-w-[120px]">
        {loading ? "Running…" : label}
      </Button>
    </div>
  );
}
