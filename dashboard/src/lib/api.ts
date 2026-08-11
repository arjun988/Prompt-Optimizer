"use client";

import { useCallback, useEffect, useState } from "react";
import type { ApiSettings, ProviderKeys } from "./types";

const STORAGE_KEY = "openprompt-settings";

export const DEFAULT_PROVIDER_KEYS: ProviderKeys = {
  openai: "",
  anthropic: "",
  gemini: "",
  grok: "",
  openrouter: "",
};

export const DEFAULT_SETTINGS: ApiSettings = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
  apiKey: process.env.NEXT_PUBLIC_API_KEY ?? "",
  provider: "mock",
  model: "mock-model",
  providerKeys: DEFAULT_PROVIDER_KEYS,
};

function normalizeSettings(raw: Partial<ApiSettings>): ApiSettings {
  return {
    ...DEFAULT_SETTINGS,
    ...raw,
    providerKeys: {
      ...DEFAULT_PROVIDER_KEYS,
      ...(raw.providerKeys ?? {}),
    },
  };
}

/** Map provider id to stored API key (empty string if unset). */
export function providerApiKey(settings: ApiSettings, provider: string): string | undefined {
  const map: Record<string, keyof ProviderKeys> = {
    openai: "openai",
    anthropic: "anthropic",
    gemini: "gemini",
    grok: "grok",
    openrouter: "openrouter",
  };
  const field = map[provider];
  if (!field) return undefined;
  const value = settings.providerKeys[field]?.trim();
  return value || undefined;
}

/** Non-empty provider keys for multi-model requests. */
export function activeProviderKeys(settings: ApiSettings): Record<string, string> | undefined {
  const entries = Object.entries(settings.providerKeys).filter(([, v]) => v.trim());
  return entries.length ? Object.fromEntries(entries.map(([k, v]) => [k, v.trim()])) : undefined;
}

export function withProviderKey(
  settings: ApiSettings,
  provider: string,
  payload: Record<string, unknown>,
): Record<string, unknown> {
  const api_key = providerApiKey(settings, provider);
  return api_key ? { ...payload, api_key } : payload;
}

export function useSettings() {
  const [settings, setSettingsState] = useState<ApiSettings>(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setSettingsState(normalizeSettings(JSON.parse(raw)));
      }
    } catch {
      /* ignore */
    }
    setLoaded(true);
  }, []);

  const setSettings = useCallback((next: Partial<ApiSettings>) => {
    setSettingsState((prev) => {
      const merged = normalizeSettings({ ...prev, ...next });
      localStorage.setItem(STORAGE_KEY, JSON.stringify(merged));
      return merged;
    });
  }, []);

  return { settings, setSettings, loaded };
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  settings: ApiSettings,
  path: string,
  body?: unknown,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (settings.apiKey) {
    headers["X-API-Key"] = settings.apiKey;
  }

  const res = await fetch(`${settings.baseUrl.replace(/\/$/, "")}${path}`, {
    method: body !== undefined ? "POST" : "GET",
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? data.message ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(String(detail), res.status);
  }

  return res.json() as Promise<T>;
}

async function multipartRequest<T>(
  settings: ApiSettings,
  path: string,
  form: FormData,
): Promise<T> {
  const headers: Record<string, string> = {};
  if (settings.apiKey) {
    headers["X-API-Key"] = settings.apiKey;
  }

  const res = await fetch(`${settings.baseUrl.replace(/\/$/, "")}${path}`, {
    method: "POST",
    headers,
    body: form,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail ?? data.message ?? detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(String(detail), res.status);
  }

  return res.json() as Promise<T>;
}

export function createApiClient(settings: ApiSettings) {
  const providerPayload = (
    provider: string,
    payload: Record<string, unknown>,
  ) => withProviderKey(settings, provider, payload);

  return {
    health: () => request<{ status: string; version: string }>(settings, "/health"),
    lint: (prompt: string) => request(settings, "/lint", { prompt }),
    optimize: (payload: Record<string, unknown>) =>
      request(
        settings,
        "/optimize",
        providerPayload(String(payload.provider ?? settings.provider), payload),
      ),
    evaluate: (payload: Record<string, unknown>) =>
      request(
        settings,
        "/evaluate",
        providerPayload(String(payload.provider ?? settings.provider), payload),
      ),
    compress: (payload: Record<string, unknown>) =>
      request(
        settings,
        "/compress",
        providerPayload(String(payload.provider ?? settings.provider), payload),
      ),
    benchmark: (payload: Record<string, unknown>) =>
      request(
        settings,
        "/benchmark",
        providerPayload(String(payload.provider ?? settings.provider), payload),
      ),
    multiModel: (payload: Record<string, unknown>) =>
      request(settings, "/multi-model/optimize", {
        ...payload,
        provider_keys: activeProviderKeys(settings),
      }),
    costRecommend: (payload: Record<string, unknown>) =>
      request(
        settings,
        "/cost/recommend",
        providerPayload(String(payload.provider ?? settings.provider), payload),
      ),
    datasetEval: (form: FormData, provider: string) => {
      const key = providerApiKey(settings, provider);
      if (key) form.append("api_key", key);
      return multipartRequest(settings, "/dataset/eval", form);
    },
    datasetOptimize: (form: FormData, provider: string) => {
      const key = providerApiKey(settings, provider);
      if (key) form.append("api_key", key);
      return multipartRequest(settings, "/dataset/optimize", form);
    },
  };
}
