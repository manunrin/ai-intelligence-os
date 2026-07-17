import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "@/lib/api";
import type { AgentRun } from "@/types";

export const agentRunKeys = {
  all: ["agentRuns"] as const,
  lists: () => [...agentRunKeys.all, "list"] as const,
};

export function useAgentRuns() {
  return useQuery({
    queryKey: agentRunKeys.lists(),
    queryFn: async () =>
      unwrap<AgentRun>(await api.get<unknown>("/api/v1/agents/runs")),
  });
}
