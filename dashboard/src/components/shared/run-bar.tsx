"use client";

import { Button } from "@/components/ui/button";
import { Label, Select } from "@/components/ui/input";
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
