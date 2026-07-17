import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap, unwrapSingle } from "@/lib/api";
import type { AgentRun } from "@/types";

export const agentRunKeys = {
  all: ["agentRuns"] as const,
  lists: () => [...agentRunKeys.all, "list"] as const,
  details: (runId: string) => [...agentRunKeys.all, "detail", runId] as const,
};

export function useAgentRuns() {
  return useQuery({
    queryKey: agentRunKeys.lists(),
    queryFn: async () =>
      unwrap<AgentRun>(await api.get<unknown>("/api/v1/agents/runs")),
  });
}

export function useAgentRun(runId: string | null) {
  return useQuery({
    queryKey: agentRunKeys.details(runId ?? ""),
    queryFn: async () =>
      unwrapSingle<AgentRun>(
        await api.get<unknown>(`/api/v1/agents/runs/${runId}`),
      ),
    enabled: runId !== null,
  });
}

export function useSubmitAgentRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      agent_type: string;
      input_payload?: Record<string, unknown>;
      topic?: string;
      source_id?: string;
    }) =>
      unwrapSingle<AgentRun>(
        api.post<unknown>("/api/v1/agents/run", body),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentRunKeys.lists() });
    },
  });
}

export function useCancelAgentRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (runId: string) =>
      unwrapSingle<Record<string, unknown>>(
        api.post<unknown, Record<string, never>>(`/api/v1/agents/runs/${runId}/cancel`, {}),
      ),
    onSuccess: (_data, runId) => {
      qc.invalidateQueries({ queryKey: agentRunKeys.lists() });
      qc.invalidateQueries({ queryKey: agentRunKeys.details(runId) });
    },
  });
}

export function useRefreshAgentRuns() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => null,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: agentRunKeys.lists() });
    },
  });
}
