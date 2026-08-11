"use client";

import { Upload } from "lucide-react";
import { useRef } from "react";
import { Label, Textarea } from "@/components/ui/input";
import type { TestFormat } from "@/lib/test-formats";
import { cn } from "@/lib/utils";

const FORMAT_LABELS: Record<TestFormat, string> = {
  yaml: "YAML",
  json: "JSON",
  csv: "CSV",
};

const FORMAT_HINTS: Record<TestFormat, string> = {
  yaml: "Same format as tests.yaml",
  json: "Array of { name, input, expected, metric } — or simple { input, expected } pairs",
  csv: "Columns: input, expected (optional: name, metric, pattern)",
};

interface TestSuiteEditorProps {
  format: TestFormat;
  onFormatChange: (format: TestFormat) => void;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  className?: string;
}

export function TestSuiteEditor({
  format,
  onFormatChange,
  value,
  onChange,
  rows = 14,
  className,
}: TestSuiteEditorProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  const onFile = async (file: File) => {
    const text = await file.text();
    onChange(text);
    const lower = file.name.toLowerCase();
    if (lower.endsWith(".json")) onFormatChange("json");
    else if (lower.endsWith(".csv")) onFormatChange("csv");
    else if (lower.endsWith(".yaml") || lower.endsWith(".yml")) onFormatChange("yaml");
  };

  return (
    <div className={cn("flex min-h-0 flex-col gap-2", className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex gap-1 rounded-md border border-border bg-muted/20 p-1">
          {(["yaml", "json", "csv"] as TestFormat[]).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => onFormatChange(f)}
              className={cn(
                "rounded-sm px-2.5 py-1 text-xs font-medium transition-colors",
                format === f
                  ? "bg-background text-foreground shadow-subtle"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              {FORMAT_LABELS[f]}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
          >
            <Upload className="h-3.5 w-3.5" />
            Upload file
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".yaml,.yml,.json,.csv,text/csv,application/json"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) void onFile(file);
              e.target.value = "";
            }}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label>Test suite ({FORMAT_LABELS[format]})</Label>
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={rows}
          className="min-h-0 flex-1 resize-none font-mono text-xs leading-relaxed"
          spellCheck={false}
        />
        <p className="text-[10px] text-muted-foreground">{FORMAT_HINTS[format]}</p>
      </div>
    </div>
  );
}
