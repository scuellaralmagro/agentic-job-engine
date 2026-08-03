import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api/client";
import type { SearchOut } from "@/lib/api/types";

const fail = (e: unknown) =>
  toast.error(e instanceof ApiError ? e.detail : "Request failed");

export interface SearchInput {
  id?: number;
  name: string;
  query: string;
  filters: Record<string, unknown>;
  schedule: string | null;
}

export function useSaveSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...body }: SearchInput) =>
      id
        ? apiFetch<SearchOut>(`/searches/${id}`, {
            method: "PUT",
            body: JSON.stringify(body),
          })
        : apiFetch<SearchOut>("/searches", {
            method: "POST",
            body: JSON.stringify(body),
          }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["searches"] }),
    onError: fail,
  });
}

export function useDeleteSearch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<{ deleted: number }>(`/searches/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["searches"] }),
    onError: fail,
  });
}

export function useImportOffer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { text?: string; url?: string }) =>
      apiFetch<{ id: number; title: string }>("/offers/import", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: (offer) => {
      qc.invalidateQueries({ queryKey: ["offers"] });
      toast(`Imported: ${offer.title}`);
    },
    onError: fail,
  });
}

export function useRebuildEmbeddings() {
  return useMutation({
    mutationFn: () =>
      apiFetch<unknown>("/embeddings/rebuild", { method: "POST" }),
    onSuccess: () => toast("Embeddings rebuilt"),
    onError: fail,
  });
}
