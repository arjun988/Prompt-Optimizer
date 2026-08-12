"use client";

import { GripVertical, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label, Textarea } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export interface BenchmarkPrompt {
  id: string;
  name: string;
  content: string;
}

interface BenchmarkPromptListProps {
  prompts: BenchmarkPrompt[];
  onChange: (prompts: BenchmarkPrompt[]) => void;
  className?: string;
}

function newPrompt(index: number): BenchmarkPrompt {
  return {
    id: crypto.randomUUID(),
    name: `Variant ${index}`,
    content: "",
  };
}

export const DEFAULT_BENCHMARK_PROMPTS: BenchmarkPrompt[] = [
  {
    id: "summarize",
    name: "Summarize",
    content: "Summarize this article in 3 bullet points. Use concise language and cover the main ideas.",
  },
  {
    id: "extract",
    name: "Extract entities",
    content: "Extract key entities from the text as JSON with fields: people, organizations, locations.",
  },
  {
    id: "classify",
    name: "Sentiment",
    content: "Classify the sentiment as positive, negative, or neutral. Reply with one word only.",
  },
];

export function BenchmarkPromptList({ prompts, onChange, className }: BenchmarkPromptListProps) {
  const update = (id: string, patch: Partial<BenchmarkPrompt>) => {
    onChange(prompts.map((p) => (p.id === id ? { ...p, ...patch } : p)));
  };

  const remove = (id: string) => {
    if (prompts.length <= 1) return;
    onChange(prompts.filter((p) => p.id !== id));
  };

  const add = () => {
    onChange([...prompts, newPrompt(prompts.length + 1)]);
  };

  return (
    <div className={cn("flex min-h-0 flex-col gap-3", className)}>
      <div className="flex items-center justify-between">
        <Label>Prompt variants</Label>
        <Button type="button" variant="outline" size="sm" onClick={add}>
          <Plus className="h-3.5 w-3.5" />
          Add variant
        </Button>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
        {prompts.map((prompt, index) => (
          <div
            key={prompt.id}
            className="rounded-lg border border-border bg-muted/10 transition-colors focus-within:border-foreground/20"
          >
            <div className="flex items-center gap-2 border-b border-border px-3 py-2">
              <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground/50" aria-hidden />
              <input
                value={prompt.name}
                onChange={(e) => update(prompt.id, { name: e.target.value })}
                placeholder={`Variant ${index + 1}`}
                className="min-w-0 flex-1 bg-transparent text-sm font-medium text-foreground outline-none placeholder:text-muted-foreground"
                aria-label={`Name for variant ${index + 1}`}
              />
              <span className="rounded-md bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                #{index + 1}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
                onClick={() => remove(prompt.id)}
                disabled={prompts.length <= 1}
                aria-label={`Remove ${prompt.name}`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
            <Textarea
              value={prompt.content}
              onChange={(e) => update(prompt.id, { content: e.target.value })}
              placeholder="Write the prompt instructions for this variant…"
              rows={4}
              className="min-h-[96px] resize-none rounded-none border-0 bg-transparent focus-visible:ring-0"
            />
          </div>
        ))}
      </div>

      <p className="text-[11px] leading-relaxed text-muted-foreground">
        Each card is a separate prompt variant. Name them clearly — results appear ranked by eval score.
      </p>
    </div>
  );
}
