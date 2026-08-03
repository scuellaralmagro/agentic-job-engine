import { useState } from "react";
import { FileText, Mail } from "lucide-react";
import { Link } from "react-router";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api/client";
import type { LetterOut, MatchOut } from "@/lib/api/types";
import { LetterEditorDialog } from "./LetterEditorDialog";
import {
  useAdapt,
  useCreateLetter,
  useMatchLetters,
  useMatchProjections,
} from "./queries";

export function AdaptActions({ match }: { match: MatchOut }) {
  const accepted = match.status === "accepted";
  const projections = useMatchProjections(match.offer_id);
  const letters = useMatchLetters(match.id);
  const adapt = useAdapt(match.id);
  const createLetter = useCreateLetter(match.id);
  const [editing, setEditing] = useState<LetterOut | null>(null);

  const fail = (e: unknown) =>
    toast.error(e instanceof ApiError ? e.detail : "Request failed");

  return (
    <div className="space-y-3 border-t border-line pt-3">
      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1"
          disabled={!accepted || adapt.isPending}
          onClick={() => adapt.mutate(undefined, { onError: fail })}
        >
          <FileText className="size-4" />
          {adapt.isPending ? "Adapting…" : "Adapt CV"}
        </Button>
        <Button
          variant="outline"
          className="flex-1"
          disabled={!accepted || createLetter.isPending}
          onClick={() =>
            createLetter.mutate(undefined, {
              onSuccess: (letter) => setEditing(letter),
              onError: fail,
            })
          }
        >
          <Mail className="size-4" />
          {createLetter.isPending ? "Writing…" : "Cover letter"}
        </Button>
      </div>
      {(adapt.isPending || createLetter.isPending) && (
        <p className="text-xs text-ink-dim">
          The agent is working — this can take a minute.
        </p>
      )}
      {!accepted && (
        <p className="text-xs text-ink-dim">Accept the offer to unlock.</p>
      )}
      {(projections.data ?? []).length > 0 && (
        <ul className="space-y-1 text-sm">
          {projections.data!.map((p) => (
            <li key={p.id} className="flex items-center justify-between gap-2">
              <Link
                to={`/library/projections/${p.id}`}
                className="truncate text-brand hover:underline"
              >
                {p.name}
              </Link>
              <span className="shrink-0 text-xs text-ink-dim">
                {p.suggestions.length} suggestion
                {p.suggestions.length === 1 ? "" : "s"}
              </span>
            </li>
          ))}
        </ul>
      )}
      {(letters.data ?? []).map((letter) => (
        <button
          key={letter.id}
          className="block text-sm text-brand hover:underline"
          onClick={() => setEditing(letter)}
        >
          Cover letter #{letter.id} — edit & render
        </button>
      ))}
      {editing && (
        <LetterEditorDialog
          letter={editing}
          open
          onOpenChange={(open) => !open && setEditing(null)}
        />
      )}
    </div>
  );
}
