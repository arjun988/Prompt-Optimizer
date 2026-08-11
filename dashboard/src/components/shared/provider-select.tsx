"use client";

import { PROVIDERS, providerById } from "@/lib/models";
import { useSettings } from "@/lib/api";
import { Label, Select } from "@/components/ui/input";

export function ProviderSelect({ className }: { className?: string }) {
  const { settings, setSettings } = useSettings();

  const providerDef = providerById(settings.provider);

  return (
    <div className={className}>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="provider">Provider</Label>
          <Select
            id="provider"
            value={settings.provider}
            onChange={(e) => {
              const next = providerById(e.target.value);
              setSettings({ provider: next.id, model: next.defaultModel });
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
