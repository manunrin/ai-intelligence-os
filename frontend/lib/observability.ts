/**
 * Client-side observability — tracks API latency, page views, and agent run lifecycle.
 *
 * Metrics are collected in-memory and flushed to the backend /metrics endpoint
 * on an interval. In non-browser environments (SSR, tests) this is a no-op.
 */

export interface ObsMetric {
  name: string;
  value: number;
  labels?: Record<string, string>;
}

type CounterMap = Map<string, number>;
type HistogramMap = Map<string, number[]>;

const counters: CounterMap = new Map();
const histograms: HistogramMap = new Map();

function ensureCounter(name: string): void {
  if (!counters.has(name)) counters.set(name, 0);
}

function ensureHistogram(name: string): void {
  if (!histograms.has(name)) histograms.set(name, []);
}

export function inc(name: string, labels: Record<string, string> | undefined = {}): void {
  const key = `${name}${_labelStr(labels)}`;
  ensureCounter(key);
  counters.set(key, (counters.get(key)! + 1) as number);
}

export function hist(name: string, value: number, labels: Record<string, string> | undefined = {}): void {
  const key = `${name}${_labelStr(labels)}`;
  ensureHistogram(key);
  const arr = histograms.get(key)!;
  arr.push(value);
}

function _labelStr(labels: Record<string, string>): string {
  const parts = Object.entries(labels).sort((a, b) => a[0].localeCompare(b[0]));
  return parts.length ? `{${parts.map(([k, v]) => `${k}="${v}"`).join(",")}}` : "";
}

/** Render all collected metrics in Prometheus text exposition format. */
export function renderPrometheus(): string {
  const lines: string[] = [];
  for (const [key, count] of [...counters.entries()].sort()) {
    lines.push(`# HELP ${key} Client counter metric`);
    lines.push(`# TYPE ${key} counter`);
    lines.push(`${key} ${count}`);
  }
  for (const [key, values] of [...histograms.entries()].sort()) {
    if (values.length === 0) continue;
    const s = [...values].sort((a, b) => a - b);
    const total = s.length;
    lines.push(`# HELP ${key} Client histogram metric`);
    lines.push(`# TYPE ${key} histogram`);
    lines.push(`${key}_count ${total}`);
    lines.push(`${key}_sum ${s.reduce((a, b) => a + b, 0).toFixed(6)}`);
    lines.push(`${key}_p50 ${s[Math.floor(total * 0.5)].toFixed(6)}`);
    lines.push(`${key}_p95 ${s[Math.min(Math.floor(total * 0.95), total - 1)].toFixed(6)}`);
    lines.push(`${key}_p99 ${s[Math.min(Math.floor(total * 0.99), total - 1)].toFixed(6)}`);
  }
  return lines.join("\n") + "\n";
}

let flushTimer: ReturnType<typeof setInterval> | null = null;
let flushInFlight = false;

/** Flush collected metrics to the backend /metrics endpoint. */
async function flushToBackend(): Promise<void> {
  if (typeof window === "undefined") return;
  // Prevent concurrent flushes — one in-flight at a time
  if (flushInFlight) return;
  flushInFlight = true;
  try {
    await fetch("/api/metrics", {
      method: "POST",
      headers: { "Content-Type": "text/plain" },
      body: renderPrometheus(),
    });
  } catch {
    // Backend not available — metrics still collected in-memory, next flush will retry
  } finally {
    flushInFlight = false;
  }
}

export function startObservability(): void {
  if (typeof window === "undefined") return;
  if (flushTimer) return; // already started
  flushTimer = setInterval(flushToBackend, 30_000);
}

export function stopObservability(): void {
  if (flushTimer) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
}
