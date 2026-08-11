"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label } from "@/components/ui/input";
import {
  ApiError,
  createApiClient,
  DEFAULT_PROVIDER_KEYS,
  DEFAULT_SETTINGS,
  useSettings,
} from "@/lib/api";
import type { ProviderKeys } from "@/lib/types";

const PROVIDER_KEY_FIELDS: { id: keyof ProviderKeys; label: string; placeholder: string }[] = [
  { id: "openai", label: "OpenAI API key", placeholder: "sk-..." },
  { id: "anthropic", label: "Anthropic (Claude) API key", placeholder: "sk-ant-..." },
  { id: "gemini", label: "Gemini API key", placeholder: "AIza..." },
  { id: "grok", label: "Grok (xAI) API key", placeholder: "xai-..." },
  { id: "openrouter", label: "OpenRouter API key", placeholder: "sk-or-..." },
];

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

  const clearProviderKeys = () => {
    setDraft({ ...draft, providerKeys: { ...DEFAULT_PROVIDER_KEYS } });
  };

  const setProviderKey = (id: keyof ProviderKeys, value: string) => {
    setDraft({
      ...draft,
      providerKeys: { ...draft.providerKeys, [id]: value },
    });
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
      <Header title="Settings" description="API connection, provider keys, and defaults" />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-xl space-y-6 animate-slide-up">
          <Card>
            <CardHeader>
              <CardTitle>OpenPrompt server</CardTitle>
              <CardDescription>
                Connection to your local or remote OpenPrompt REST API
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
                <Label htmlFor="apiKey">OpenPrompt API key (optional)</Label>
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
                  Reset all
                </Button>
              </div>
              {healthMsg && (
                <p className="text-sm text-muted-foreground">{healthMsg}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Provider API keys</CardTitle>
              <CardDescription>
                Used when you evaluate or optimize with OpenAI, Claude, Gemini, Grok, or
                OpenRouter. Stored in your browser only — sent to your OpenPrompt server per
                request, not logged by the dashboard.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {PROVIDER_KEY_FIELDS.map((field) => (
                <div key={field.id} className="space-y-1.5">
                  <Label htmlFor={`pk-${field.id}`}>{field.label}</Label>
                  <Input
                    id={`pk-${field.id}`}
                    type="password"
                    autoComplete="off"
                    value={draft.providerKeys[field.id]}
                    onChange={(e) => setProviderKey(field.id, e.target.value)}
                    placeholder={field.placeholder}
                  />
                </div>
              ))}
              <p className="text-xs text-muted-foreground">
                Mock and Ollama do not need keys here. Ollama uses{" "}
                <code className="rounded bg-muted px-1 py-0.5 font-mono">OLLAMA_HOST</code> on
                the server if not localhost.
              </p>
              <p className="text-xs text-muted-foreground">
                On the machine running <code className="font-mono">openprompt serve</code>, install
                provider SDKs once:{" "}
                <code className="rounded bg-muted px-1 py-0.5 font-mono">
                  pip install -e &quot;.[gemini,openai,anthropic,server]&quot;
                </code>
              </p>
              <div className="flex flex-wrap gap-2 pt-1">
                <Button onClick={save}>{saved ? "Saved" : "Save provider keys"}</Button>
                <Button variant="ghost" onClick={clearProviderKeys}>
                  Clear provider keys
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </AppShell>
  );
}
