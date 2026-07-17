import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export const deleteKeys = {
  invalidateAll: () => {
    const qc = useQueryClient();
    const keys = [
      ["articles"],
      ["tasks"],
      ["knowledge"],
      ["reports"],
      ["agentRuns"],
    ];
    keys.forEach((k) => qc.invalidateQueries({ queryKey: k }));
  },
};

export function useDeleteArticle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/articles/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [["articles"]] });
    },
  });
}

export function useDeleteTask() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/tasks/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [["tasks"]] });
    },
  });
}

export function useDeleteKnowledge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/v1/knowledge/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [["knowledge"]] });
    },
  });
}
