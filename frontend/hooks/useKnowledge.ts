import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap, unwrapSingle } from "@/lib/api";
import type { KnowledgeItem, KnowledgeSearchResult, RAGResponse } from "@/types";

export const knowledgeKeys = {
  all: ["knowledge"] as const,
  lists: () => [...knowledgeKeys.all, "list"] as const,
};

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

export function useKnowledgeSearch() {
  return useQuery({
    queryKey: ["knowledge", "search"],
    queryFn: async () => [],
    enabled: false,
  });
}

export function useKnowledgeSearchMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (params: {
      query: string;
      limit?: number;
      kind_filter?: string | null;
      tag_filter?: string | null;
      score_threshold?: number | null;
    }) => {
      const raw = await api.post<unknown>("/api/v1/knowledge/search", params);
      if (typeof raw === "object" && raw !== null && "data" in raw) {
        const obj = raw as Record<string, unknown>;
        if ("data" in obj && typeof obj.data === "object") {
          const inner = obj.data as Record<string, unknown>;
          return (inner.results ?? []) as KnowledgeSearchResult[];
        }
      }
      return [];
    },
    onSuccess: (results) => {
      qc.setQueryData(["knowledge", "searchResults"], results);
    },
  });
}

export function useRAGQuery() {
  return useMutation({
    mutationFn: async (params: { query: string; limit?: number }) => {
      const raw = await api.post<unknown>("/api/v1/knowledge/rag", {
        query: params.query,
        limit: params.limit ?? 5,
      });
      return unwrapSingle<RAGResponse>(raw);
    },
  });
}
