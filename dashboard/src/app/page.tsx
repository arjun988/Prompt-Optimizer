"use client";

import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  FileStack,
  FlaskConical,
  Layers,
  ScanSearch,
  Sparkles,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const QUICK_ACTIONS = [
  {
    href: "/lint",
    title: "Lint prompt",
    description: "Heuristic quality score, ambiguity & format checks — no API key required.",
    icon: ScanSearch,
  },
  {
    href: "/evaluate",
    title: "Evaluate",
    description: "Run test suites against your prompt with exact, regex, or schema metrics.",
    icon: FlaskConical,
  },
  {
    href: "/dataset",
    title: "Extraction dataset",
    description: "Upload PDFs/images with labels — eval and optimize prompts for file parsing.",
    icon: FileStack,
  },
  {
    href: "/optimize",
    title: "Optimize",
    description: "Improve prompts with reinforcement, hybrid, or other eval-driven strategies.",
    icon: Sparkles,
  },
  {
    href: "/multi-model",
    title: "Compare models",
    description: "Run the same optimization across providers and pick quality vs cost.",
    icon: Layers,
  },
  {
    href: "/benchmark",
    title: "Benchmark",
    description: "Compare named prompt variants with ranked scores and exportable reports.",
    icon: BarChart3,
  },
];

export default function OverviewPage() {
  return (
    <AppShell>
      <Header
        title="Overview"
        description="Analyze, optimize, and evaluate prompts through the OpenPrompt API"
      />
      <main className="flex-1 overflow-y-auto p-6">
        <div className="mx-auto max-w-5xl space-y-8 animate-slide-up">
          <section className="space-y-2">
            <Badge variant="outline" className="normal-case">
              Prompt engineering workspace
            </Badge>
            <h2 className="text-2xl font-semibold tracking-tight">
              Treat prompts like code
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
              OpenPrompt parses prompts into a structured AST, lints for issues, optimizes with
              evaluation-driven strategies, and proves improvements with test suites — all from
              a polished UI instead of the terminal.
            </p>
          </section>

          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {QUICK_ACTIONS.map((action) => {
              const Icon = action.icon;
              return (
                <Link key={action.href} href={action.href} className="group block">
                  <Card className="h-full transition-colors hover:border-foreground/20 hover:bg-accent/30">
                    <CardHeader className="border-none pb-0">
                      <div className="mb-2 flex h-9 w-9 items-center justify-center rounded-md border border-border bg-background">
                        <Icon className="h-4 w-4" />
                      </div>
                      <CardTitle>{action.title}</CardTitle>
                      <CardDescription className="leading-relaxed">
                        {action.description}
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="pt-4">
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground group-hover:text-foreground">
                        Open
                        <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                      </span>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Getting started</CardTitle>
              <CardDescription>Three steps to connect the dashboard to your backend</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ol className="space-y-3 text-sm text-muted-foreground">
                <li className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border text-xs font-medium text-foreground">
                    1
                  </span>
                  <span>
                    Install dashboard deps:{" "}
                    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
                      cd dashboard && npm install
                    </code>
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border text-xs font-medium text-foreground">
                    2
                  </span>
                  <span>
                    Start the API:{" "}
                    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
                      openprompt serve
                    </code>
                  </span>
                </li>
                <li className="flex gap-3">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-border text-xs font-medium text-foreground">
                    3
                  </span>
                  <span>
                    Run the UI:{" "}
                    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
                      npm run dev
                    </code>{" "}
                    — configure URL &amp; API key in Settings
                  </span>
                </li>
              </ol>
            </CardContent>
          </Card>
        </div>
      </main>
    </AppShell>
  );
}
