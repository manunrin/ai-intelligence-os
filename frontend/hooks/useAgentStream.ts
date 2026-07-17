/**
 * useAgentStream — SSE-based live progress for an agent run.
 *
 * Tries EventSource (SSE) first; falls back to HTTP polling at 3s intervals
 * when SSE is unavailable (CORS, proxies, etc.).
 */
import { useEffect, useRef, useCallback, useState } from "react";
import { api, unwrapSingle } from "@/lib/api";
import type { AgentRun } from "@/types";

export interface AgentStreamEvent {
  type: string;
  run_id: string;
  timestamp: string;
  stage_name?: string;
  status?: string;
  output_summary?: Record<string, unknown>;
  error_message?: string | null;
  duration_ms?: number | null;
  extra?: Record<string, unknown>;
}

interface UseAgentStreamOptions {
  runId: string | null;
  onEvent?: (event: AgentStreamEvent) => void;
  enabled?: boolean;
}

const POLL_INTERVAL_MS = 3000;

export function useAgentStream({
  runId,
  onEvent,
  enabled: enabledProp = true,
}: UseAgentStreamOptions) {
  const [isSse, setIsSse] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;
  const sseFailedRef = useRef(false);

  const stop = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    sseFailedRef.current = false;
  }, []);

  useEffect(() => {
    if (!runId || !enabledProp) {
      stop();
      return;
    }

    let cancelled = false;
    const sseUrl = `/api/v1/agents/runs/${runId}/stream`;

    // ── Polling fallback ────────────────────────────────────────────
    const startPolling = () => {
      const poll = async () => {
        if (cancelled) return;
        try {
          const raw = await api.get<unknown>(`/api/v1/agents/runs/${runId}`);
          const run = await unwrapSingle<AgentRun>(raw);
          onEventRef.current?.({
            type: "poll_update",
            run_id: runId,
            timestamp: new Date().toISOString(),
            status: run.status,
          });
        } catch {
          // poll failure — silently retry next interval
        }
      };
      pollIntervalRef.current = setInterval(poll, POLL_INTERVAL_MS);
    };

    // ── Try SSE first ─────────────────────────────────────────────
    try {
      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      const allHandler = (e: MessageEvent) => {
        if (cancelled) return;
        try {
          const event: AgentStreamEvent = JSON.parse(e.data);
          onEventRef.current?.(event);
        } catch {
          // ignore parse errors on heartbeat / raw messages
        }
      };

      for (const eventType of [
        "stage_start",
        "stage_complete",
        "stage_failed",
        "run_complete",
        "run_failed",
        "run_cancelled",
        "heartbeat",
      ]) {
        es.addEventListener(eventType, allHandler as EventListener, false);
      }

      es.onerror = () => {
        if (cancelled) return;
        // SSE failed — switch to polling fallback
        if (!sseFailedRef.current) {
          sseFailedRef.current = true;
          setIsSse(false);
          es.close();
          startPolling();
        }
      };

      es.onopen = () => {
        if (cancelled) return;
        setIsSse(true);
      };
    } catch {
      // EventSource not supported — immediately fall back to polling
      setIsSse(false);
      startPolling();
    }

    return () => {
      cancelled = true;
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only re-run when runId or enabledProp changes
  }, [runId, enabledProp, stop]);

  return { isSse };
}
