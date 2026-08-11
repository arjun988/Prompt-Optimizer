/** Curated provider + model IDs (Aug 2026). Synced with openprompt/config/model_catalog.py */

export interface ProviderDef {
  id: string;
  label: string;
  defaultModel: string;
  models: readonly string[];
}

export const PROVIDERS: readonly ProviderDef[] = [
  {
    id: "mock",
    label: "Mock (offline)",
    defaultModel: "mock-model",
    models: ["mock-model"],
  },
  {
    id: "openai",
    label: "OpenAI",
    defaultModel: "gpt-5.6-terra",
    models: [
      "gpt-5.6",
      "gpt-5.6-sol",
      "gpt-5.6-terra",
      "gpt-5.6-luna",
      "gpt-5.5",
      "gpt-5.4",
      "gpt-5.4-mini",
      "gpt-5.4-nano",
      "gpt-5.1",
      "gpt-5-mini",
      "gpt-5-nano",
      "gpt-4.1",
      "gpt-4.1-mini",
      "gpt-4.1-nano",
      "gpt-4o",
      "gpt-4o-mini",
      "o3-mini",
    ],
  },
  {
    id: "anthropic",
    label: "Anthropic",
    defaultModel: "claude-sonnet-5",
    models: [
      "claude-opus-5",
      "claude-sonnet-5",
      "claude-fable-5",
      "claude-opus-4-8",
      "claude-opus-4-7",
      "claude-opus-4-6",
      "claude-opus-4-5",
      "claude-sonnet-4-6",
      "claude-sonnet-4-5",
      "claude-haiku-4-5",
    ],
  },
  {
    id: "gemini",
    label: "Gemini",
    defaultModel: "gemini-3.6-flash",
    models: [
      "gemini-3.6-flash",
      "gemini-3.5-flash",
      "gemini-3.5-flash-lite",
      "gemini-3.1-pro-preview",
      "gemini-3-flash-preview",
      "gemini-2.5-pro",
      "gemini-2.5-flash",
      "gemini-2.5-flash-lite",
      "gemini-2.0-flash",
      "gemini-2.0-flash-lite",
      "gemini-flash-latest",
      "gemini-pro-latest",
    ],
  },
  {
    id: "grok",
    label: "Grok (xAI)",
    defaultModel: "grok-4.3",
    models: [
      "grok-4.5",
      "grok-4.3",
      "grok-4.20-0309-reasoning",
      "grok-4.20-0309-non-reasoning",
    ],
  },
  {
    id: "ollama",
    label: "Ollama (local)",
    defaultModel: "llama3.3",
    models: [
      "llama3.3",
      "llama3.2",
      "llama3.1",
      "qwen3",
      "qwen2.5",
      "mistral",
      "gemma3",
      "deepseek-r1",
      "phi4",
    ],
  },
  {
    id: "openrouter",
    label: "OpenRouter",
    defaultModel: "openai/gpt-5.6-terra",
    models: [
      "openai/gpt-5.6-sol",
      "openai/gpt-5.6-terra",
      "openai/gpt-5.6-luna",
      "openai/gpt-4.1-mini",
      "anthropic/claude-opus-5",
      "anthropic/claude-sonnet-5",
      "google/gemini-3.6-flash",
      "google/gemini-2.5-pro",
      "google/gemini-2.5-flash",
      "x-ai/grok-4.3",
    ],
  },
] as const;

export function providerById(id: string): ProviderDef {
  return PROVIDERS.find((p) => p.id === id) ?? PROVIDERS[0];
}
