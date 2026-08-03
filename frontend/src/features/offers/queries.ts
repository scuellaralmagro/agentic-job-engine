import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { MatchOut } from "@/lib/api/types";

export function useMatch(id: number) {
  return useQuery({
    queryKey: ["match", id],
    queryFn: () => apiFetch<MatchOut>(`/matches/${id}`),
  });
}
