/** Parse evaluation test suites as YAML, JSON, or CSV for the dashboard API. */

export type TestFormat = "yaml" | "json" | "csv";

export interface ParsedTest {
  name: string;
  input: string;
  expected?: string | null;
  metric?: string;
  pattern?: string | null;
  schema?: Record<string, unknown> | null;
  evaluator?: string | null;
  metadata?: Record<string, unknown>;
}

export function parseTestsYaml(raw: string): ParsedTest[] {
  const lines = raw.split("\n");
  const tests: ParsedTest[] = [];
  let current: ParsedTest | null = null;
  let blockKey: string | null = null;
  let blockLines: string[] = [];

  const flushBlock = () => {
    if (current && blockKey) {
      (current as Record<string, string>)[blockKey] = blockLines.join("\n").replace(/\n$/, "");
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
      current = { name: itemMatch[1].trim(), input: "" };
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
      (current as Record<string, string>)[kv[1]] = kv[2].trim().replace(/^["']|["']$/g, "");
    }
  }

  flushTest();
  return normalizeTests(tests);
}

export function parseTestsJson(raw: string): ParsedTest[] {
  const data = JSON.parse(raw) as unknown;
  let items: unknown[];

  if (Array.isArray(data)) {
    items = data;
  } else if (data && typeof data === "object" && "tests" in data) {
    items = (data as { tests: unknown[] }).tests;
  } else {
    throw new Error("JSON must be an array of tests or an object with a 'tests' array.");
  }

  if (!Array.isArray(items)) {
    throw new Error("JSON 'tests' must be an array.");
  }

  return normalizeTests(
    items.map((item, index) => {
      if (!item || typeof item !== "object") {
        throw new Error(`Test at index ${index} must be an object.`);
      }
      const row = item as Record<string, unknown>;
      if (row.input === undefined || row.input === null) {
        throw new Error(`Test at index ${index} is missing 'input'.`);
      }
      return {
        name: String(row.name ?? `test_${index + 1}`),
        input: String(row.input),
        expected: row.expected !== undefined && row.expected !== null ? String(row.expected) : null,
        metric: row.metric ? String(row.metric) : row.expected !== undefined ? "exact_match" : "exact_match",
        pattern: row.pattern ? String(row.pattern) : null,
        schema: (row.schema as Record<string, unknown>) ?? null,
        evaluator: row.evaluator ? String(row.evaluator) : null,
        metadata: (row.metadata as Record<string, unknown>) ?? undefined,
      };
    }),
  );
}

/** Minimal RFC4180-style CSV parser for test rows. */
export function parseTestsCsv(raw: string): ParsedTest[] {
  const text = raw.trim();
  if (!text) throw new Error("CSV content is empty.");

  const rows = parseCsvRows(text);
  if (rows.length < 2) throw new Error("CSV must include a header row and at least one data row.");

  const headers = rows[0].map((h) => h.trim().toLowerCase());
  const inputIdx = headers.indexOf("input");
  if (inputIdx < 0) throw new Error("CSV must include an 'input' column.");

  const nameIdx = headers.indexOf("name");
  const expectedIdx = headers.indexOf("expected");
  const metricIdx = headers.indexOf("metric");
  const patternIdx = headers.indexOf("pattern");

  const tests: ParsedTest[] = [];
  for (let i = 1; i < rows.length; i++) {
    const row = rows[i];
    const input = (row[inputIdx] ?? "").trim();
    if (!input) continue;

    tests.push({
      name: nameIdx >= 0 && row[nameIdx]?.trim() ? row[nameIdx].trim() : `test_${tests.length + 1}`,
      input,
      expected: expectedIdx >= 0 ? row[expectedIdx]?.trim() || null : null,
      metric: metricIdx >= 0 && row[metricIdx]?.trim() ? row[metricIdx].trim() : "exact_match",
      pattern: patternIdx >= 0 ? row[patternIdx]?.trim() || null : null,
    });
  }

  if (!tests.length) throw new Error("CSV contained no rows with non-empty input.");
  return normalizeTests(tests);
}

export function parseTests(format: TestFormat, raw: string): ParsedTest[] {
  if (format === "yaml") return parseTestsYaml(raw);
  if (format === "json") return parseTestsJson(raw);
  return parseTestsCsv(raw);
}

function normalizeTests(tests: ParsedTest[]): ParsedTest[] {
  return tests.map((t, index) => ({
    ...t,
    name: t.name || `test_${index + 1}`,
    metric: t.metric || (t.expected !== undefined && t.expected !== null ? "exact_match" : "exact_match"),
  }));
}

function parseCsvRows(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n" || (ch === "\r" && next === "\n")) {
      row.push(field);
      field = "";
      if (row.some((cell) => cell.trim())) rows.push(row);
      row = [];
      if (ch === "\r") i++;
    } else if (ch !== "\r") {
      field += ch;
    }
  }

  row.push(field);
  if (row.some((cell) => cell.trim())) rows.push(row);
  return rows;
}

export async function readTestsFromFile(file: File, format: TestFormat): Promise<string> {
  const text = await file.text();
  if (format === "csv" && !file.name.toLowerCase().endsWith(".csv")) {
    return text;
  }
  if (format === "json" && !file.name.toLowerCase().endsWith(".json")) {
    return text;
  }
  return text;
}
