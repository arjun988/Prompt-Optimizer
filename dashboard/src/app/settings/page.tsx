"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import { ApiError, createApiClient, DEFAULT_SETTINGS, useSettings } from "@/lib/api";

export default function SettingsPage() {
  const { settings, setSettings, loaded } = useSettings();
  const [draft, setDraft] = useState(settings);
  const [saved, setSaved] = useState(false);
  const [healthMsg, setHealthMsg] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    if (loaded) setDraft(settings);
  }, [loaded, settings]);

  const save = () => {
    setSettings(draft);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const reset = () => {
    setDraft(DEFAULT_SETTINGS);
    setSettings(DEFAULT_SETTINGS);
  };

  const testConnection = async () => {
    setTesting(true);
    setHealthMsg(null);
    try {
      const h = await createApiClient(draft).health();
      setHealthMsg(`Connected — OpenPrompt v${h.version}`);
    } catch (e) {
      setHealthMsg(e instanceof ApiError ? e.message : "Connection failed");
    } finally {
      setTesting(false);
    }
  };

  return (
    <AppShell>
      <Header title="Settings" description="API connection and defaults" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-xl space-y-6 animate-slide-up">
          <Card>
            <CardHeader>
              <CardTitle>API connection</CardTitle>
              <CardDescription>
                Point the dashboard at your OpenPrompt REST server
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="baseUrl">Base URL</Label>
                <Input
                  id="baseUrl"
                  value={draft.baseUrl}
                  onChange={(e) => setDraft({ ...draft, baseUrl: e.target.value })}
                  placeholder="http://127.0.0.1:8000"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="apiKey">API key (optional)</Label>
                <Input
                  id="apiKey"
                  type="password"
                  value={draft.apiKey}
                  onChange={(e) => setDraft({ ...draft, apiKey: e.target.value })}
                  placeholder="Matches OPENPROMPT_API_KEY on server"
                />
              </div>
              <div className="flex flex-wrap gap-2 pt-2">
                <Button onClick={save}>{saved ? "Saved" : "Save settings"}</Button>
                <Button variant="outline" onClick={testConnection} disabled={testing}>
                  {testing ? "Testing…" : "Test connection"}
                </Button>
                <Button variant="ghost" onClick={reset}>
                  Reset defaults
                </Button>
              </div>
              {healthMsg && (
                <p className="text-sm text-muted-foreground">{healthMsg}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Environment variables</CardTitle>
              <CardDescription>Set on the server process, not in this UI</CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 font-mono text-xs text-muted-foreground">
                <li>
                  <span className="text-foreground">OPENPROMPT_API_KEY</span> — REST auth
                </li>
                <li>
                  <span className="text-foreground">OPENPROMPT_CORS_ORIGINS</span> — e.g.{" "}
                  http://localhost:3000
                </li>
                <li>
                  <span className="text-foreground">OPENAI_API_KEY</span>,{" "}
                  <span className="text-foreground">ANTHROPIC_API_KEY</span>, etc.
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </main>
    </AppShell>
  );
}
