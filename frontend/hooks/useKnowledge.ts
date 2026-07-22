import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState, useCallback } from "react";
import { api, unwrap, unwrapSingle } from "@/lib/api";
import { getStoredToken } from "@/lib/auth-storage";
import type { KnowledgeItem, KnowledgeSearchResult, RAGResponse } from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const knowledgeKeys = {
  all: ["knowledge"] as const,
  lists: () => [...knowledgeKeys.all, "list"] as const,
};

interface SearchParams {
  query: string;
  limit?: number;
  kind_filter?: string | null;
  tag_filter?: string | null;
  score_threshold?: number | null;
}

export function parseSearchResponse(raw: unknown): KnowledgeSearchResult[] {
  if (typeof raw === "object" && raw !== null && "data" in raw) {
    const obj = raw as Record<string, unknown>;
    if ("data" in obj && typeof obj.data === "object") {
      const inner = obj.data as Record<string, unknown>;
      return (inner.results ?? []) as KnowledgeSearchResult[];
    }
  }
  return [];
}

export function useKnowledgeItems() {
  return useQuery({
    queryKey: knowledgeKeys.lists(),
    queryFn: async () =>
      unwrap<KnowledgeItem>(await api.get<unknown>("/api/v1/knowledge")),
  });
}

export function useCreateKnowledge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<unknown>("/api/v1/knowledge", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: knowledgeKeys.lists() });
    },
  });
}

export function useUpdateKnowledge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.put<unknown>(`/api/v1/knowledge/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: knowledgeKeys.lists() });
    },
  });
}

export function useKnowledgeSearch(params: SearchParams) {
  return useQuery({
    queryKey: [
      "knowledge",
      "search",
      params.query,
      params.limit,
      params.kind_filter,
      params.tag_filter,
      params.score_threshold,
    ],
    queryFn: async ({ signal }: { signal?: AbortSignal }) => {
      const raw = await api.post<unknown>(
        "/api/v1/knowledge/search",
        {
          query: params.query,
          limit: params.limit ?? 5,
          ...(params.kind_filter ? { kind_filter: params.kind_filter } : {}),
          ...(params.tag_filter ? { tag_filter: params.tag_filter } : {}),
          ...(params.score_threshold !== undefined
            ? { score_threshold: params.score_threshold }
            : {}),
        },
        { signal }
      );
      return parseSearchResponse(raw);
    },
    enabled: !!params.query.trim(),
  });
}

export function useKnowledgeSearchMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: SearchParams) => {
      const raw = await api.post<unknown>("/api/v1/knowledge/search", params);
      return parseSearchResponse(raw);
    },
    onSuccess: (results) => {
      qc.setQueryData(["knowledge", "searchResults"], results);
    },
  });
}

export function useRAGQuery() {
  return useMutation({
    mutationFn: async (params: {
      query: string;
      limit?: number;
      kind_filter?: string | null;
      tag_filter?: string | null;
    }) => {
      const raw = await api.post<unknown>("/api/v1/knowledge/rag", {
        query: params.query,
        limit: params.limit ?? 5,
        kind_filter: params.kind_filter,
        tag_filter: params.tag_filter,
      });
      return unwrapSingle<RAGResponse>(raw);
    },
  });
}

interface RAGStreamCallbacks {
  onToken: (content: string) => void;
  onDone: (sources: Array<{ knowledge_id: string; title: string }>) => void;
  onError: (message: string) => void;
}

/**
 * Stream a RAG answer via SSE. Returns a controller with start/stop.
 * Only one stream can be active at a time per hook instance.
 */
export function useRAGStream() {
  const abortRef = useRef<AbortController | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const stop = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setIsStreaming(false);
  }, []);

  const start = useCallback(
    (
      query: string,
      kind_filter: string | null,
      tag_filter: string | null,
      cbs: RAGStreamCallbacks
    ) => {
      stop();
      const controller = new AbortController();
      abortRef.current = controller;
      setIsStreaming(true);

      const token = getStoredToken();
      fetch(`${API_BASE}/api/v1/knowledge/rag/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          query,
          limit: 5,
          kind_filter,
          tag_filter,
        }),
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok) {
            let message = "RAG stream failed";
            try {
              const errBody = await response.json();
              message = errBody.message || errBody.detail || message;
            } catch {
              // ignore
            }
            throw new Error(message);
          }

          if (!response.body) {
            throw new Error("Stream body unavailable");
          }

          await parseSSE(response.body, controller.signal, cbs);
        })
        .catch((err: Error) => {
          if (controller.signal.aborted) return;
          cbs.onError(err.message || "RAG stream failed");
        })
        .finally(() => {
          if (!controller.signal.aborted) {
            setIsStreaming(false);
            abortRef.current = null;
          }
        });
    },
    [stop]
  );

  return { isStreaming, start, stop };
}

async function parseSSE(
  body: ReadableStream<Uint8Array>,
  signal: AbortSignal,
  cbs: RAGStreamCallbacks
): Promise<void> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      if (signal.aborted) break;
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (signal.aborted) break;
        const trimmed = line.trim();
        if (!trimmed.startsWith("data:")) continue;
        const payload = trimmed.slice(5).trim();
        if (!payload) continue;

        try {
          const event = JSON.parse(payload) as {
            type: string;
            content?: string;
            sources?: Array<{ knowledge_id: string; title: string }>;
            message?: string;
          };
          if (event.type === "token" && event.content !== undefined) {
            cbs.onToken(event.content);
          } else if (event.type === "done") {
            cbs.onDone(event.sources ?? []);
          } else if (event.type === "error") {
            cbs.onError(event.message ?? "RAG generation failed");
          }
        } catch {
          // ignore malformed SSE events
        }
      }
    }
  } catch (err) {
    if (signal.aborted) return;
    cbs.onError(err instanceof Error ? err.message : "Stream read failed");
  } finally {
    reader.releaseLock();
  }
}
