"use client";

import { useEffect, useState } from "react";
import { Circle } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { createApiClient } from "@/lib/api";
import { useSettings } from "@/lib/api";

export function Header({ title, description }: { title: string; description?: string }) {
  const { settings, loaded } = useSettings();
  const [online, setOnline] = useState<boolean | null>(null);
  const [version, setVersion] = useState<string | null>(null);

  useEffect(() => {
    if (!loaded) return;

    const client = createApiClient(settings);
    client
      .health()
      .then((h) => {
        setOnline(true);
        setVersion(h.version);
      })
      .catch(() => {
        setOnline(false);
        setVersion(null);
      });
  }, [loaded, settings.baseUrl, settings.apiKey]);

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
      <div className="min-w-0">
        <h1 className="truncate text-sm font-semibold tracking-tight">{title}</h1>
        {description && (
          <p className="truncate text-xs text-muted-foreground">{description}</p>
        )}
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden items-center gap-2 sm:flex">
          {online === null ? (
            <Badge variant="outline">Checking…</Badge>
          ) : online ? (
            <>
              <Badge variant="success" className="gap-1.5 normal-case">
                <Circle className="h-2 w-2 fill-current" />
                API online
              </Badge>
              {version && (
                <span className="text-[11px] text-muted-foreground">v{version}</span>
              )}
            </>
          ) : (
            <Badge variant="destructive" className="gap-1.5 normal-case">
              <Circle className="h-2 w-2 fill-current" />
              API offline
            </Badge>
          )}
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
