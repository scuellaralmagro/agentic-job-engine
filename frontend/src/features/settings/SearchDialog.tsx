import { useEffect, useState } from "react";
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
import type { SearchOut } from "@/lib/api/types";
import { useEstimate } from "@/lib/api/queries";
import { useSaveSearch } from "./queries";

export function SearchDialog({
  search,
  open,
  onOpenChange,
}: {
  search: SearchOut | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const save = useSaveSearch();
  const estimate = useEstimate();
  const [name, setName] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState("{}");
  const [schedule, setSchedule] = useState("");
  const [cap, setCap] = useState("25");
  const [filterError, setFilterError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setName(search?.name ?? "");
      setQuery(search?.query ?? "");
      setFilters(JSON.stringify(search?.filters ?? {}, null, 2));
      setSchedule(search?.schedule ?? "");
      // A new search shows the default explicitly: the dialog always sends this
      // field, so the API's omitted-field default never fires from here.
      setCap(
        search ? (search.max_offers != null ? String(search.max_offers) : "") : "25",
      );
      setFilterError(null);
    }
  }, [open, search]);

  const perOffer = estimate.data?.cost_per_offer_usd ?? 0;
  const ceiling = estimate.data?.max_offers ?? 0;
  const capped = cap.trim() !== "";
  const perRun = (capped ? Number(cap) : ceiling) * perOffer;

  const submit = () => {
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(filters);
    } catch {
      setFilterError("Filters must be valid JSON.");
      return;
    }
    save.mutate(
      {
        id: search?.id,
        name,
        query,
        filters: parsed,
        schedule: schedule.trim() || null,
        max_offers: capped ? Number(cap) : null,
      },
      { onSuccess: () => onOpenChange(false) },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="glass-elevated max-w-lg">
        <DialogHeader>
          <DialogTitle>{search ? "Edit search" : "New search"}</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label htmlFor="s-name">Name</Label>
            <Input
              id="s-name"
              className="bg-surface"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="s-query">Query</Label>
            <Input
              id="s-query"
              className="bg-surface"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="s-filters">Filters (JSON)</Label>
            <Textarea
              id="s-filters"
              rows={4}
              className="bg-surface font-mono text-xs"
              value={filters}
              onChange={(e) => setFilters(e.target.value)}
            />
            {filterError && (
              <p className="text-xs text-danger">{filterError}</p>
            )}
          </div>
          <div>
            <Label htmlFor="s-schedule">Schedule</Label>
            <Input
              id="s-schedule"
              className="bg-surface font-mono"
              placeholder="0 8 * * *"
              value={schedule}
              onChange={(e) => setSchedule(e.target.value)}
            />
            <p className="mt-1 text-xs text-ink-dim">
              Cron format — leave empty for manual-only.
            </p>
          </div>
          <div>
            <Label htmlFor="s-cap">Max offers per run</Label>
            <Input
              id="s-cap"
              className="bg-surface"
              // Not "25": a greyed 25 in an empty field reads as a value, while an
              // empty field here means uncapped — the opposite of what it suggests.
              placeholder="no cap"
              value={cap}
              onChange={(e) => setCap(e.target.value.replace(/\D/g, ""))}
            />
            {capped ? (
              <p className="mt-1 text-xs text-ink-dim">
                ~${perRun.toFixed(2)} per run
                {schedule.trim() &&
                  ` · ~$${(perRun * 30).toFixed(2)}/month if it runs daily`}
              </p>
            ) : (
              <p className="mt-1 text-xs text-danger">
                Uncapped — up to {ceiling} offers, ~${perRun.toFixed(2)} per run.
              </p>
            )}
          </div>
          <Button
            className="w-full"
            disabled={save.isPending || !name.trim() || !query.trim()}
            onClick={submit}
          >
            {save.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
