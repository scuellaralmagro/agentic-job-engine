import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FileText } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/EmptyState";
import { GlassPanel } from "@/components/GlassPanel";
import { LetterEditorDialog } from "@/features/offers/LetterEditorDialog";
import { useDocs, useOffers } from "@/features/dashboard/queries";
import { apiFetch } from "@/lib/api/client";
import type { LetterOut } from "@/lib/api/types";

function useAllLetters() {
  return useQuery({
    queryKey: ["letters", "all"],
    queryFn: () => apiFetch<LetterOut[]>("/cover-letters"),
  });
}

export function DocumentsTab() {
  const docs = useDocs();
  const offers = useOffers();
  const letters = useAllLetters();
  const [editing, setEditing] = useState<LetterOut | null>(null);

  const offerTitle = (id: number | null) =>
    offers.data?.find((o) => o.id === id)?.title ?? (id ? `#${id}` : "—");

  return (
    <div className="space-y-4">
      <GlassPanel>
        {(docs.data ?? []).length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No documents yet"
            hint="Render a tailored CV or cover letter to produce a PDF."
          />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kind</TableHead>
                <TableHead>Offer</TableHead>
                <TableHead>Created</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {docs.data!.map((d) => (
                <TableRow key={d.id}>
                  <TableCell>
                    <Badge variant={d.kind === "cv" ? "secondary" : "outline"}>
                      {d.kind}
                    </Badge>
                  </TableCell>
                  <TableCell>{offerTitle(d.offer_id)}</TableCell>
                  <TableCell className="text-ink-dim">
                    {new Date(d.created_at).toLocaleString()}
                  </TableCell>
                  <TableCell>
                    <a
                      href={`/api/docs/${d.id}/download`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand hover:underline"
                    >
                      Download
                    </a>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </GlassPanel>

      {(letters.data ?? []).length > 0 && (
        <GlassPanel>
          <h2 className="mb-2 font-medium">Cover letters</h2>
          <ul className="space-y-1 text-sm">
            {letters.data!.map((letter) => (
              <li key={letter.id}>
                <button
                  className="text-brand hover:underline"
                  onClick={() => setEditing(letter)}
                >
                  Letter #{letter.id} ({letter.language ?? "?"}) — edit & render
                </button>
              </li>
            ))}
          </ul>
        </GlassPanel>
      )}
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
