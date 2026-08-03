import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api/client";
import type { MatchOut, MatchStatus } from "@/lib/api/types";

export function useQueue(status: MatchStatus, minFitness?: number) {
  return useQuery({
    queryKey: ["queue", status, minFitness ?? 0],
    queryFn: () => {
      const params = new URLSearchParams({ status, limit: "200" });
      if (minFitness) params.set("min_fitness", String(minFitness));
      return apiFetch<MatchOut[]>(`/queue?${params}`);
    },
  });
}

export type StatusAction = "accept" | "dismiss" | "reset";

export function useSetStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, action }: { id: number; action: StatusAction }) =>
      apiFetch<MatchOut>(`/matches/${id}/${action}`, { method: "POST" }),
    onMutate: async ({ id }) => {
      await qc.cancelQueries({ queryKey: ["queue"] });
      const prev = qc.getQueriesData<MatchOut[]>({ queryKey: ["queue"] });
      qc.setQueriesData<MatchOut[]>({ queryKey: ["queue"] }, (old) =>
        old?.filter((m) => m.id !== id),
      );
      return { prev };
    },
    onError: (err, _vars, ctx) => {
      ctx?.prev.forEach(([key, data]) => qc.setQueryData(key, data));
      toast.error(err instanceof ApiError ? err.detail : "Request failed");
    },
    onSettled: (_data, _err, { id }) => {
      qc.invalidateQueries({ queryKey: ["queue"] });
      qc.invalidateQueries({ queryKey: ["match", id] });
    },
  });
}
