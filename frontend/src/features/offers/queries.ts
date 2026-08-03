import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import type { LetterOut, MatchOut, ProjectionOut } from "@/lib/api/types";

export function useMatch(id: number) {
  return useQuery({
    queryKey: ["match", id],
    queryFn: () => apiFetch<MatchOut>(`/matches/${id}`),
  });
}

export function useMatchProjections(offerId: number) {
  return useQuery({
    queryKey: ["projections", { offer: offerId }],
    queryFn: () => apiFetch<ProjectionOut[]>(`/projections?offer_id=${offerId}`),
  });
}

export function useMatchLetters(matchId: number) {
  return useQuery({
    queryKey: ["letters", { match: matchId }],
    queryFn: () => apiFetch<LetterOut[]>(`/cover-letters?match_id=${matchId}`),
  });
}

export function useAdapt(matchId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<ProjectionOut>(`/matches/${matchId}/adapt`, {
        method: "POST",
        body: JSON.stringify({ language: null, notes: null }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projections"] }),
  });
}

export function useCreateLetter(matchId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<LetterOut>(`/matches/${matchId}/cover-letter`, {
        method: "POST",
        body: JSON.stringify({ language: null, notes: null }),
      }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["letters"] }),
  });
}
