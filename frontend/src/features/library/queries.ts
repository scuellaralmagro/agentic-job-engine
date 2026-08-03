import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api/client";
import type { DocOut, ProjectionOut, TailoredCv } from "@/lib/api/types";

const fail = (e: unknown) =>
  toast.error(e instanceof ApiError ? e.detail : "Request failed");

export function useProjections() {
  return useQuery({
    queryKey: ["projections"],
    queryFn: () => apiFetch<ProjectionOut[]>("/projections"),
  });
}

export function useProjection(id: number) {
  return useQuery({
    queryKey: ["projection", id],
    queryFn: () => apiFetch<ProjectionOut>(`/projections/${id}`),
  });
}

export function useDeleteProjection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<void>(`/projections/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["projections"] }),
    onError: fail,
  });
}

export function useRenderProjection() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      apiFetch<DocOut>(`/projections/${id}/render`, { method: "POST" }),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["docs"] });
      toast("PDF rendered", {
        action: {
          label: "Download",
          onClick: () => window.open(`/api/docs/${doc.id}/download`, "_blank"),
        },
      });
    },
    onError: fail,
  });
}

export function usePatchProjection(id: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { content_json?: TailoredCv; name?: string }) =>
      apiFetch<ProjectionOut>(`/projections/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      }),
    onSuccess: (updated) => {
      qc.setQueryData(["projection", id], updated);
      qc.invalidateQueries({ queryKey: ["projections"] });
      toast("Saved");
    },
    onError: fail,
  });
}
