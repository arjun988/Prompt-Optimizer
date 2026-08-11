"use client";

import { PROVIDERS } from "@/lib/types";
import { useSettings } from "@/lib/api";
import { Label, Select } from "@/components/ui/input";

export function ProviderSelect({ className }: { className?: string }) {
  const { settings, setSettings } = useSettings();

  const providerDef = PROVIDERS.find((p) => p.id === settings.provider) ?? PROVIDERS[0];

  return (
    <div className={className}>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="provider">Provider</Label>
          <Select
            id="provider"
            value={settings.provider}
            onChange={(e) => {
              const next = PROVIDERS.find((p) => p.id === e.target.value) ?? PROVIDERS[0];
              setSettings({ provider: next.id, model: next.models[0] });
            }}
          >
            {PROVIDERS.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="model">Model</Label>
          <Select
            id="model"
            value={settings.model}
            onChange={(e) => setSettings({ model: e.target.value })}
          >
            {providerDef.models.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
        </div>
      </div>
    </div>
  );
}
