import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api/client";
import type { DiscoveryResultOut, RunEstimate, RunOut } from "@/lib/api/types";

/** A finished run never changes again — stop polling rather than slowing it down. */
export function resultsRefetchInterval(run: RunOut | undefined): number | false {
  return run?.status === "running" ? 2000 : false;
}

export function useRun(runId: number) {
  return useQuery({
    queryKey: ["run", runId],
    queryFn: () => apiFetch<RunOut>(`/runs/${runId}`),
    refetchInterval: (query) => resultsRefetchInterval(query.state.data),
  });
}

export function useRunResults(runId: number, run: RunOut | undefined) {
  return useQuery({
    queryKey: ["run-results", runId],
    queryFn: () => apiFetch<DiscoveryResultOut[]>(`/runs/${runId}/results`),
    refetchInterval: resultsRefetchInterval(run),
  });
}

export function useEstimate() {
  return useQuery({
    queryKey: ["run-estimate"],
    queryFn: () => apiFetch<RunEstimate>("/runs/estimate"),
    staleTime: 60_000,
  });
}

export interface CreateRunInput {
  term: string;
  filters?: Record<string, unknown>;
  max_offers?: number;
}

export function useCreateRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateRunInput) =>
      apiFetch<RunOut>("/runs", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.detail : "Could not start the run"),
  });
}
