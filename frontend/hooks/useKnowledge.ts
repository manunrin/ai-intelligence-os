import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import type { KnowledgeItem } from "@/types";

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
