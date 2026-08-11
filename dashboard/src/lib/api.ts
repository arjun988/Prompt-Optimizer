"use client";

import { useCallback, useEffect, useState } from "react";
import type { ApiSettings } from "./types";

const STORAGE_KEY = "openprompt-settings";

export const DEFAULT_SETTINGS: ApiSettings = {
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000",
  apiKey: process.env.NEXT_PUBLIC_API_KEY ?? "",
  provider: "mock",
  model: "mock-model",
};

export function useSettings() {
  const [settings, setSettingsState] = useState<ApiSettings>(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        setSettingsState({ ...DEFAULT_SETTINGS, ...JSON.parse(raw) });
      }
    } catch {
      /* ignore */
    }
    setLoaded(true);
  }, []);

  const setSettings = useCallback((next: Partial<ApiSettings>) => {
    setSettingsState((prev) => {
      const merged = { ...prev, ...next };
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
  return {
    health: () => request<{ status: string; version: string }>(settings, "/health"),
    lint: (prompt: string) => request(settings, "/lint", { prompt }),
    optimize: (payload: Record<string, unknown>) => request(settings, "/optimize", payload),
    evaluate: (payload: Record<string, unknown>) => request(settings, "/evaluate", payload),
    compress: (payload: Record<string, unknown>) => request(settings, "/compress", payload),
    benchmark: (payload: Record<string, unknown>) => request(settings, "/benchmark", payload),
    multiModel: (payload: Record<string, unknown>) =>
      request(settings, "/multi-model/optimize", payload),
    costRecommend: (payload: Record<string, unknown>) =>
      request(settings, "/cost/recommend", payload),
    datasetEval: (form: FormData) => multipartRequest(settings, "/dataset/eval", form),
    datasetOptimize: (form: FormData) => multipartRequest(settings, "/dataset/optimize", form),
  };
}

/** Parse YAML-ish tests block into API test objects (minimal parser). */
export function parseTestsYaml(raw: string): Record<string, unknown>[] {
  const lines = raw.split("\n");
  const tests: Record<string, unknown>[] = [];
  let current: Record<string, unknown> | null = null;
  let blockKey: string | null = null;
  let blockLines: string[] = [];

  const flushBlock = () => {
    if (current && blockKey) {
      current[blockKey] = blockLines.join("\n").replace(/\n$/, "");
    }
    blockKey = null;
    blockLines = [];
  };

  const flushTest = () => {
    flushBlock();
    if (current) tests.push(current);
    current = null;
  };

  for (const line of lines) {
    if (/^\s*tests:\s*$/.test(line)) continue;

    const itemMatch = line.match(/^\s*-\s*name:\s*(.+)$/);
    if (itemMatch) {
      flushTest();
      current = { name: itemMatch[1].trim() };
      continue;
    }

    if (!current) continue;

    const blockStart = line.match(/^\s*(input|expected|pattern):\s*\|\s*$/);
    if (blockStart) {
      flushBlock();
      blockKey = blockStart[1];
      continue;
    }

    if (blockKey && /^\s{4,}/.test(line)) {
      blockLines.push(line.replace(/^\s{4}/, ""));
      continue;
    }

    flushBlock();

    const kv = line.match(/^\s*(\w+):\s*(.+)$/);
    if (kv) {
      current[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, "");
    }
  }

  flushTest();
  return tests;
}
