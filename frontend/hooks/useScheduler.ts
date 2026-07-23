import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, unwrap, unwrapSingle } from "@/lib/api";
import type { ScheduledJob } from "@/types";

export const schedulerKeys = {
  all: ["schedulerJobs"] as const,
  lists: () => [...schedulerKeys.all, "list"] as const,
  detail: (jobId: string) => [...schedulerKeys.all, "detail", jobId] as const,
};

export function useSchedulerJobs() {
  return useQuery({
    queryKey: schedulerKeys.lists(),
    queryFn: async () =>
      unwrap<ScheduledJob>(await api.get<unknown>("/api/v1/scheduler/jobs")),
  });
}

export function useSchedulerJob(jobId: string | null) {
  return useQuery({
    queryKey: schedulerKeys.detail(jobId ?? ""),
    queryFn: async () =>
      unwrapSingle<ScheduledJob>(
        await api.get<unknown>(`/api/v1/scheduler/jobs/${jobId}`),
      ),
    enabled: jobId !== null,
  });
}

export function useCreateScheduledJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      name: string;
      cron_expression: string;
      job_type: string;
      enabled?: boolean;
      input_payload?: Record<string, unknown>;
    }) =>
      unwrapSingle<ScheduledJob>(
        api.post<unknown>("/api/v1/scheduler/jobs", body),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: schedulerKeys.lists() });
    },
  });
}

export function useUpdateScheduledJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      jobId,
      ...patch
    }: {
      jobId: string;
      name?: string;
      cron_expression?: string;
      job_type?: string;
      enabled?: boolean;
      input_payload?: Record<string, unknown>;
    }) =>
      unwrapSingle<ScheduledJob>(
        api.put<unknown, Record<string, unknown>>(
          `/api/v1/scheduler/jobs/${jobId}`,
          patch,
        ),
      ),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: schedulerKeys.lists() });
      qc.invalidateQueries({ queryKey: schedulerKeys.detail(vars.jobId) });
    },
  });
}

export function useDeleteScheduledJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      unwrapSingle<Record<string, unknown>>(
        api.delete<unknown>(`/api/v1/scheduler/jobs/${jobId}`),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: schedulerKeys.lists() });
    },
  });
}

export function useTriggerScheduledJob() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: string) =>
      unwrapSingle<ScheduledJob>(
        api.post<unknown, Record<string, never>>(
          `/api/v1/scheduler/jobs/${jobId}/trigger`,
          {},
        ),
      ),
    onSuccess: (_data, jobId) => {
      qc.invalidateQueries({ queryKey: schedulerKeys.detail(jobId) });
    },
  });
}
