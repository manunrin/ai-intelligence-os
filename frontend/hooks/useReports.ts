import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import type { IntelligenceReport } from "@/types";

export const reportKeys = {
  all: ["reports"] as const,
  lists: () => [...reportKeys.all, "list"] as const,
};

export function useReports() {
  return useQuery({
    queryKey: reportKeys.lists(),
    queryFn: async () =>
      unwrap<IntelligenceReport>(await api.get<unknown>("/api/v1/reports")),
  });
}

export function useCreateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<unknown>("/api/v1/reports", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: reportKeys.lists() });
    },
  });
}
