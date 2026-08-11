/** Helpers for optimize API call budgeting. */

import type { TestFormat } from "./test-formats";

export const DEFAULT_EVAL_BUDGET = 50;

/** Strategies that honor `eval_budget` (evaluation rounds cap). */
export const BUDGETED_STRATEGIES = new Set(["hybrid", "evolutionary", "grpo"]);

export function usesEvalBudget(strategy: string): boolean {
  return BUDGETED_STRATEGIES.has(strategy);
}

export function safeTestCount(
  parse: (format: TestFormat, raw: string) => unknown[],
  format: TestFormat,
  raw: string,
  fallback = 3,
): number {
  try {
    const n = parse(format, raw).length;
    return n > 0 ? n : fallback;
  } catch {
    return fallback;
  }
}

/**
 * Rough model-call estimate for budgeted strategies.
 * Each eval round runs every test once; hybrid also issues LLM rewrite calls (~budget / 5).
 */
export function estimateOptimizeApiCalls(
  strategy: string,
  evalBudget: number,
  testCount: number,
  modelCount = 1,
): { min: number; max: number; label: string } {
  if (!usesEvalBudget(strategy) || testCount <= 0) {
    return { min: 0, max: 0, label: "" };
  }

  const evalCalls = evalBudget * testCount;
  const rewriteCalls = strategy === "hybrid" ? Math.max(3, Math.floor(evalBudget / 5)) : 0;
  const min = evalCalls * modelCount;
  const max = (evalCalls + rewriteCalls) * modelCount;

  const perModel =
    min === max
      ? `~${min} API calls`
      : `~${min}–${max} API calls`;

  const label =
    modelCount > 1
      ? `${perModel} (${modelCount} models × ${evalBudget} eval rounds × ${testCount} tests)`
      : `${perModel} (${evalBudget} eval rounds × ${testCount} tests)`;

  return { min, max, label };
}
