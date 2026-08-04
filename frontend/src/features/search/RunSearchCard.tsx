import { useState } from "react";
import { Play, Search } from "lucide-react";
import { useNavigate } from "react-router";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { GlassPanel } from "@/components/GlassPanel";
import { WorkModeSelect } from "./WorkModeSelect";
import type { WorkMode } from "@/lib/api/types";
import { useCreateRun, useEstimate } from "./queries";

export function RunSearchCard() {
  const navigate = useNavigate();
  const estimate = useEstimate();
  const createRun = useCreateRun();
  const [term, setTerm] = useState("");
  const [location, setLocation] = useState("");
  const [workMode, setWorkMode] = useState<WorkMode[]>([]);
  const [cap, setCap] = useState("");
  const [confirming, setConfirming] = useState(false);

  const ceiling = estimate.data;
  const scoredCeiling = cap.trim()
    ? Math.min(Number(cap), ceiling?.max_offers ?? Number(cap))
    : (ceiling?.max_offers ?? 0);
  const projected = scoredCeiling * (ceiling?.cost_per_offer_usd ?? 0);

  const launch = () => {
    createRun.mutate(
      {
        term: term.trim(),
        filters: {
          ...(location.trim() ? { location: location.trim() } : {}),
          ...(workMode.length ? { work_mode: workMode } : {}),
        },
        ...(cap.trim() ? { max_offers: Number(cap) } : {}),
      },
      {
        onSuccess: (run) => {
          setConfirming(false);
          navigate(`/search/runs/${run.id}`);
        },
      },
    );
  };

  return (
    <GlassPanel className="space-y-3">
      <h2 className="font-medium">Run a search</h2>
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-64 flex-1">
          <Label htmlFor="q">Search query</Label>
          <Input
            id="q"
            className="bg-surface"
            placeholder="python backend"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="loc">Location</Label>
          <Input
            id="loc"
            className="w-40 bg-surface"
            placeholder="Madrid"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
          />
        </div>
        <WorkModeSelect value={workMode} onChange={setWorkMode} />
        <div>
          <Label htmlFor="cap">Max offers to score</Label>
          <Input
            id="cap"
            className="w-36 bg-surface"
            placeholder={String(ceiling?.max_offers ?? "")}
            value={cap}
            onChange={(e) => setCap(e.target.value.replace(/\D/g, ""))}
          />
        </div>
        <Button disabled={!term.trim()} onClick={() => setConfirming(true)}>
          <Search className="size-4" /> Run search
        </Button>
      </div>
      {workMode.length > 0 && (
        <p className="text-xs text-ink-dim">
          Offers that don't state a mode are still included — most postings never
          say.
        </p>
      )}

      <Dialog open={confirming} onOpenChange={setConfirming}>
        <DialogContent className="glass-elevated">
          <DialogHeader>
            <DialogTitle>Start this search?</DialogTitle>
          </DialogHeader>
          <div className="space-y-2 text-sm">
            <p>
              Searching <span className="font-medium">{term}</span> across all
              enabled sources.
            </p>
            <p className="text-ink-dim">
              How many offers a query returns can't be known in advance, so this
              is a ceiling, not a forecast: up to{" "}
              <span className="font-mono">{scoredCeiling}</span> offers scored,
              up to <span className="font-mono">${projected.toFixed(2)}</span>.
            </p>
            <p className="text-ink-dim">
              Everything found is recorded; anything past the cap stays unscored.
            </p>
          </div>
          <Button disabled={createRun.isPending} onClick={launch}>
            <Play className="size-4" />
            {createRun.isPending ? "Starting…" : "Start run"}
          </Button>
        </DialogContent>
      </Dialog>
    </GlassPanel>
  );
}
