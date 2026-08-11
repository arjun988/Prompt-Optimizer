"use client";

import { FileText, ImageIcon, Trash2, Upload } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Label, Textarea } from "@/components/ui/input";
import { ACCEPTED_MEDIA_TYPES } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface SampleFile {
  id: string;
  file: File;
  expected: string;
}

interface FileUploadZoneProps {
  samples: SampleFile[];
  onChange: (samples: SampleFile[]) => void;
}

function fileIcon(name: string) {
  const lower = name.toLowerCase();
  if (lower.endsWith(".pdf")) return FileText;
  if (/\.(png|jpe?g|webp|gif|tiff)$/.test(lower)) return ImageIcon;
  return FileText;
}

export function FileUploadZone({ samples, onChange }: FileUploadZoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const addFiles = useCallback(
    (files: FileList | File[]) => {
      const next = [...samples];
      for (const file of Array.from(files)) {
        next.push({
          id: `${file.name}-${file.size}-${Date.now()}-${Math.random()}`,
          file,
          expected: "",
        });
      }
      onChange(next);
    },
    [samples, onChange],
  );

  const remove = (id: string) => onChange(samples.filter((s) => s.id !== id));

  const updateExpected = (id: string, expected: string) => {
    onChange(samples.map((s) => (s.id === id ? { ...s, expected } : s)));
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Samples (PDF / images)</Label>
        <span className="text-[10px] text-muted-foreground">{samples.length} file(s)</span>
      </div>

      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed px-4 py-10 transition-colors",
          dragging
            ? "border-foreground/40 bg-accent/50"
            : "border-border bg-muted/10 hover:border-foreground/25 hover:bg-accent/30",
        )}
      >
        <Upload className="h-5 w-5 text-muted-foreground" />
        <p className="text-sm font-medium">Drop PDFs or images here</p>
        <p className="text-xs text-muted-foreground">or click to browse</p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_MEDIA_TYPES}
          className="hidden"
          onChange={(e) => {
            if (e.target.files?.length) addFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      {samples.length > 0 && (
        <div className="space-y-2">
          {samples.map((sample) => {
            const Icon = fileIcon(sample.file.name);
            return (
              <div
                key={sample.id}
                className="rounded-md border border-border bg-background p-3"
              >
                <div className="mb-2 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm font-medium">{sample.file.name}</span>
                    <span className="text-[10px] text-muted-foreground">
                      {(sample.file.size / 1024).toFixed(1)} KB
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    onClick={() => remove(sample.id)}
                    aria-label={`Remove ${sample.file.name}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
                <div className="space-y-1">
                  <Label className="text-[10px]">Expected JSON (label)</Label>
                  <Textarea
                    value={sample.expected}
                    onChange={(e) => updateExpected(sample.id, e.target.value)}
                    rows={2}
                    placeholder='{"vendor": "Acme Corp", "total": 120}'
                    className="font-mono text-xs"
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function buildDatasetFormData(options: {
  prompt: string;
  provider: string;
  model: string;
  schema: string;
  datasetName: string;
  samples: SampleFile[];
  strategy?: string;
  vision?: boolean;
}): FormData {
  const labels: Record<string, string> = {};
  for (const sample of options.samples) {
    if (sample.expected.trim()) {
      labels[sample.file.name] = sample.expected.trim();
    }
  }

  const form = new FormData();
  form.append("prompt", options.prompt);
  form.append("provider", options.provider);
  form.append("model", options.model);
  form.append("dataset_name", options.datasetName);
  if (options.schema.trim()) form.append("schema", options.schema.trim());
  if (Object.keys(labels).length) form.append("labels", JSON.stringify(labels));
  if (options.strategy) form.append("strategy", options.strategy);
  if (options.vision !== undefined) form.append("vision", String(options.vision));

  for (const sample of options.samples) {
    form.append("files", sample.file, sample.file.name);
  }

  return form;
}
