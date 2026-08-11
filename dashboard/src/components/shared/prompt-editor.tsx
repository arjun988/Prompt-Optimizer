"use client";

import { Label, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";

interface PromptEditorProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  rows?: number;
  hint?: string;
  readOnly?: boolean;
  className?: string;
}

export function PromptEditor({
  label,
  value,
  onChange,
  placeholder,
  rows = 12,
  hint,
  readOnly,
  className,
}: PromptEditorProps) {
  return (
    <div className={cn("flex h-full flex-col gap-1.5", className)}>
      <div className="flex items-center justify-between">
        <Label>{label}</Label>
        {hint && <span className="text-[10px] text-muted-foreground">{hint}</span>}
      </div>
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        readOnly={readOnly}
        className={cn(
          "min-h-0 flex-1 resize-none editor-surface",
          readOnly && "bg-muted/30 text-muted-foreground",
        )}
      />
    </div>
  );
}
