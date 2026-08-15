import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { RunEstimate } from "@/lib/api/types";

/** Shared: both the Search tab's run card and the saved-search dialog price a run. */
export function useEstimate() {
  return useQuery({
    queryKey: ["run-estimate"],
    queryFn: () => apiFetch<RunEstimate>("/runs/estimate"),
    staleTime: 60_000,
  });
}
