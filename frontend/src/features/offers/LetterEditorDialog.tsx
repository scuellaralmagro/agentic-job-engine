import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { apiFetch, ApiError } from "@/lib/api/client";
import type { CoverLetterContent, DocOut, LetterOut } from "@/lib/api/types";

export function LetterEditorDialog({
  letter,
  open,
  onOpenChange,
}: {
  letter: LetterOut;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const qc = useQueryClient();
  const [content, setContent] = useState<CoverLetterContent>(
    letter.content_json,
  );

  const save = useMutation({
    mutationFn: () =>
      apiFetch<LetterOut>(`/cover-letters/${letter.id}`, {
        method: "PATCH",
        body: JSON.stringify({ content_json: content }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["letters"] });
      toast("Cover letter saved");
    },
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.detail : "Save failed"),
  });

  const render = useMutation({
    mutationFn: () =>
      apiFetch<DocOut>(`/cover-letters/${letter.id}/render`, {
        method: "POST",
      }),
    onSuccess: (doc) => {
      qc.invalidateQueries({ queryKey: ["docs"] });
      toast("PDF rendered", {
        action: {
          label: "Download",
          onClick: () => window.open(`/api/docs/${doc.id}/download`, "_blank"),
        },
      });
    },
    onError: (e) =>
      toast.error(e instanceof ApiError ? e.detail : "Render failed"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-elevated max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit cover letter</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label htmlFor="salutation">Salutation</Label>
            <Input
              id="salutation"
              className="bg-surface"
              value={content.salutation}
              onChange={(e) =>
                setContent({ ...content, salutation: e.target.value })
              }
            />
          </div>
          <div>
            <Label htmlFor="body">Body (one paragraph per block)</Label>
            <Textarea
              id="body"
              rows={10}
              className="bg-surface"
              value={content.paragraphs.join("\n\n")}
              onChange={(e) =>
                setContent({
                  ...content,
                  paragraphs: e.target.value.split(/\n{2,}/),
                })
              }
            />
          </div>
          <div>
            <Label htmlFor="closing">Closing</Label>
            <Input
              id="closing"
              className="bg-surface"
              value={content.closing}
              onChange={(e) =>
                setContent({ ...content, closing: e.target.value })
              }
            />
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <Button
              variant="secondary"
              disabled={save.isPending}
              onClick={() => save.mutate()}
            >
              {save.isPending ? "Saving…" : "Save"}
            </Button>
            <Button disabled={render.isPending} onClick={() => render.mutate()}>
              {render.isPending ? "Rendering…" : "Render PDF"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
