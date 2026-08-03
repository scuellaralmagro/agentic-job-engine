import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { apiFetch, ApiError } from "@/lib/api/client";
import type { ProfileData, SourceDocumentOut } from "@/lib/api/types";

export function useProfile() {
  return useQuery({
    queryKey: ["profile"],
    queryFn: () => apiFetch<ProfileData>("/profile"),
  });
}

export function useSaveProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: ProfileData) =>
      apiFetch<ProfileData>("/profile", {
        method: "PUT",
        body: JSON.stringify(data),
      }),
    onSuccess: (saved) => {
      qc.setQueryData(["profile"], saved);
      toast("Profile saved");
    },
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.detail : "Save failed"),
  });
}

export function useSourceDocuments() {
  return useQuery({
    queryKey: ["source-documents"],
    queryFn: () => apiFetch<SourceDocumentOut[]>("/source-documents"),
  });
}
