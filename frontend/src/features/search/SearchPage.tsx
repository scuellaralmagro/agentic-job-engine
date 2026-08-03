import { useState } from "react";
import { Pencil, Play, Plus, Search, Trash2 } from "lucide-react";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { EmptyState } from "@/components/EmptyState";
import { GlassPanel } from "@/components/GlassPanel";
import { useRuns, useRunSearch, useSearches } from "@/features/dashboard/queries";
import { SearchDialog } from "@/features/settings/SearchDialog";
import { useDeleteSearch, useImportOffer } from "@/features/settings/queries";
import type { SearchOut } from "@/lib/api/types";
import { RunSearchCard } from "./RunSearchCard";

const RUN_TONE: Record<string, string> = {
  running: "text-brand animate-pulse",
  ok: "text-ok",
  partial: "text-warn",
  failed: "text-danger",
};

export function SearchPage() {
  const runs = useRuns();
  const searches = useSearches();
  const runSearch = useRunSearch();
  const deleteSearch = useDeleteSearch();
  const importOffer = useImportOffer();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<SearchOut | null>(null);
  const [importText, setImportText] = useState("");

  const doImport = () => {
    const value = importText.trim();
    if (!value) return;
    const isUrl = /^https?:\/\/\S+$/.test(value);
    importOffer.mutate(isUrl ? { url: value } : { text: value }, {
      onSuccess: () => setImportText(""),
    });
  };

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Search</h1>

      <RunSearchCard />

      <GlassPanel>
        <h2 className="mb-3 font-medium">Runs</h2>
        {(runs.data ?? []).length === 0 ? (
          <EmptyState
            icon={Search}
            title="No runs yet"
            hint="Run a search above, or trigger a saved search."
          />
        ) : (
          <ul className="space-y-2">
            {runs.data!.map((r) => (
              <li
                key={r.id}
                className="flex flex-wrap items-center gap-3 rounded-lg bg-surface px-3 py-2"
              >
                <Badge variant="outline">{r.kind}</Badge>
                <span className="min-w-0 flex-1 truncate font-medium">
                  {r.term ?? "—"}
                </span>
                <span className={RUN_TONE[r.status]}>{r.status}</span>
                <span className="font-mono text-sm text-ink-dim">
                  {r.offers_new}/{r.offers_found} new
                </span>
                <span className="text-xs text-ink-dim">
                  {new Date(r.started_at).toLocaleString()}
                </span>
                <Button asChild size="sm" variant="secondary">
                  <Link to={`/search/runs/${r.id}`}>View</Link>
                </Button>
              </li>
            ))}
          </ul>
        )}
      </GlassPanel>

      <GlassPanel>
        <div className="mb-3 flex items-center">
          <h2 className="mr-auto font-medium">Saved searches</h2>
          <Button
            size="sm"
            onClick={() => {
              setEditing(null);
              setDialogOpen(true);
            }}
          >
            <Plus className="size-3.5" /> New search
          </Button>
        </div>
        {(searches.data ?? []).length === 0 ? (
          <p className="text-sm text-ink-dim">
            No saved searches yet. Create one to run it on a schedule.
          </p>
        ) : (
          <ul className="space-y-2">
            {searches.data!.map((s) => (
              <li
                key={s.id}
                className="flex items-center gap-2 rounded-lg bg-surface px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{s.name}</p>
                  <p className="truncate text-xs text-ink-dim">{s.query}</p>
                </div>
                {s.schedule ? (
                  <Badge variant="outline" className="font-mono">
                    {s.schedule}
                  </Badge>
                ) : (
                  <Badge variant="outline">manual</Badge>
                )}
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={runSearch.isPending}
                  onClick={() => runSearch.mutate(s.id)}
                >
                  <Play className="size-3.5" /> Run
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Edit ${s.name}`}
                  onClick={() => {
                    setEditing(s);
                    setDialogOpen(true);
                  }}
                >
                  <Pencil className="size-3.5" />
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  className="text-danger"
                  aria-label={`Delete ${s.name}`}
                  onClick={() => deleteSearch.mutate(s.id)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-2 font-medium">Import a single offer</h2>
        <Textarea
          aria-label="Paste a job description or URL"
          placeholder="Paste a job description or URL…"
          rows={3}
          className="bg-surface"
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
        />
        <Button
          className="mt-2"
          disabled={importOffer.isPending || !importText.trim()}
          onClick={doImport}
        >
          {importOffer.isPending ? "Importing…" : "Import offer"}
        </Button>
      </GlassPanel>

      <SearchDialog
        search={editing}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
      />
    </div>
  );
}
