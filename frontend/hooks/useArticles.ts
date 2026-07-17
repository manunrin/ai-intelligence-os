import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import type { Article } from "@/types";

export const articleKeys = {
  all: ["articles"] as const,
  lists: () => [...articleKeys.all, "list"] as const,
  details: () => [...articleKeys.all, "detail"] as const,
};

export function useArticles() {
  return useQuery({
    queryKey: articleKeys.lists(),
    queryFn: async () => unwrap<Article>(await api.get<unknown>("/api/v1/articles")),
  });
}

export function useCreateArticle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<unknown>("/api/v1/articles", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.lists() });
    },
  });
}

export function useUpdateArticle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Record<string, unknown> }) =>
      api.put<unknown>(`/api/v1/articles/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: articleKeys.lists() });
    },
  });
}
