import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api/client";
import type { DocOut, OfferOut, RunOut, SearchOut } from "@/lib/api/types";

/** Poll fast while a run is in flight, slowly otherwise so scheduled runs still surface. */
export function runsRefetchInterval(runs: RunOut[] | undefined): number {
  return runs?.some((r) => r.finished_at === null) ? 2500 : 30_000;
}

export function useRuns() {
  return useQuery({
    queryKey: ["runs"],
    queryFn: () => apiFetch<RunOut[]>("/runs"),
    refetchInterval: (query) => runsRefetchInterval(query.state.data),
  });
}

export function useOffers() {
  return useQuery({
    queryKey: ["offers"],
    queryFn: () => apiFetch<OfferOut[]>("/offers?limit=200"),
  });
}

export function useSearches() {
  return useQuery({
    queryKey: ["searches"],
    queryFn: () => apiFetch<SearchOut[]>("/searches"),
  });
}

export function useDocs() {
  return useQuery({
    queryKey: ["docs"],
    queryFn: () => apiFetch<DocOut[]>("/generated-docs"),
  });
}

/** Takes no run: an asynchronous run has produced nothing yet, so there is nothing
 *  to report beyond the fact that it started. Claiming counts here would be a lie. */
export function runStartedMessage(): string {
  return "Run started — watch it in Search";
}

export function useRunSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (searchId: number) =>
      apiFetch<RunOut>(`/searches/${searchId}/run`, { method: "POST" }),
    onSuccess: () => {
      ["runs", "queue", "offers"].forEach((key) =>
        qc.invalidateQueries({ queryKey: [key] }),
      );
      toast(runStartedMessage());
    },
    onError: (e) => toast.error(e instanceof ApiError ? e.detail : "Run failed"),
  });
}
