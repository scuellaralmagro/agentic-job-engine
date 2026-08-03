import { useState } from "react";
import { Pencil, Play, Plus, RefreshCw, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { GlassPanel } from "@/components/GlassPanel";
import { useRunSearch, useSearches } from "@/features/dashboard/queries";
import type { SearchOut } from "@/lib/api/types";
import { SearchDialog } from "./SearchDialog";
import {
  useDeleteSearch,
  useImportOffer,
  useRebuildEmbeddings,
} from "./queries";
import pkg from "../../../package.json";

export function SettingsPage() {
  const searches = useSearches();
  const runSearch = useRunSearch();
  const deleteSearch = useDeleteSearch();
  const importOffer = useImportOffer();
  const rebuild = useRebuildEmbeddings();

  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<SearchOut | null>(null);
  const [importText, setImportText] = useState("");

  const openDialog = (search: SearchOut | null) => {
    setEditing(search);
    setDialogOpen(true);
  };

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
      <h1 className="text-xl font-semibold">Settings</h1>

      <GlassPanel>
        <div className="mb-3 flex items-center">
          <h2 className="mr-auto font-medium">Saved searches</h2>
          <Button size="sm" onClick={() => openDialog(null)}>
            <Plus className="size-3.5" /> New search
          </Button>
        </div>
        {(searches.data ?? []).length === 0 ? (
          <p className="text-sm text-ink-dim">
            No saved searches yet. Create one to start discovering offers.
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
                  onClick={() => openDialog(s)}
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
        <h2 className="mb-2 font-medium">Manual import</h2>
        <Textarea
          aria-label="Paste a job description or URL"
          placeholder="Paste a job description or URL…"
          rows={4}
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

      <GlassPanel className="flex items-center gap-4">
        <div className="mr-auto">
          <h2 className="font-medium">System</h2>
          <p className="text-xs text-ink-dim">aje-frontend v{pkg.version}</p>
        </div>
        <Button
          variant="secondary"
          disabled={rebuild.isPending}
          onClick={() => rebuild.mutate()}
        >
          <RefreshCw className="size-3.5" />
          {rebuild.isPending ? "Rebuilding…" : "Rebuild embeddings"}
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
