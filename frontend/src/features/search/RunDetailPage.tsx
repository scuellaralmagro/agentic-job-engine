import { useState } from "react";
import { ArrowLeft, Inbox } from "lucide-react";
import { Link, useParams } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/EmptyState";
import { FitnessBadge } from "@/components/FitnessBadge";
import { GlassPanel } from "@/components/GlassPanel";
import type { ResultStatus } from "@/lib/api/types";
import { ResultStatusChip, ReviewChip } from "./ResultStatusChip";
import { useRun, useRunResults } from "./queries";

const RUN_TONE: Record<string, string> = {
  running: "text-brand animate-pulse",
  ok: "text-ok",
  partial: "text-warn",
  failed: "text-danger",
};

interface SourceResult {
  source: string;
  count: number;
  error: string | null;
}

export function RunDetailPage() {
  const { id } = useParams();
  const runId = Number(id);
  const { data: run, isPending } = useRun(runId);
  const { data: results } = useRunResults(runId, run);
  const [newOnly, setNewOnly] = useState(false);
  const [status, setStatus] = useState<ResultStatus | "all">("all");

  if (isPending || !run) return <p className="text-ink-dim">Loading…</p>;

  const rows = (results ?? []).filter(
    (r) => (!newOnly || r.is_new) && (status === "all" || r.status === status),
  );
  const sources = (run.source_results ?? []) as SourceResult[];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to="/search">
            <ArrowLeft className="size-4" /> Search
          </Link>
        </Button>
        <h1 className="mr-auto text-xl font-semibold">{run.term ?? "—"}</h1>
        <Badge variant="outline">{run.kind}</Badge>
        <span className={RUN_TONE[run.status]}>{run.status}</span>
      </div>

      <GlassPanel className="flex flex-wrap items-center gap-6 text-sm">
        <span className="text-ink-dim">
          Started {new Date(run.started_at).toLocaleString()}
        </span>
        <span className="font-mono">
          {run.offers_new}/{run.offers_found} new
        </span>
        <div className="flex flex-wrap gap-2">
          {sources.map((s) => (
            <Badge
              key={s.source}
              variant="outline"
              className={s.error ? "text-danger" : undefined}
              title={s.error ?? undefined}
            >
              {s.source}: {s.error ? "failed" : s.count}
            </Badge>
          ))}
        </div>
      </GlassPanel>

      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            aria-label="New only"
            checked={newOnly}
            onChange={(e) => setNewOnly(e.target.checked)}
          />
          New only
        </label>
        <label className="flex items-center gap-2 text-sm">
          Status
          <select
            aria-label="Status filter"
            className="rounded-lg bg-surface px-2 py-1"
            value={status}
            onChange={(e) => setStatus(e.target.value as ResultStatus | "all")}
          >
            <option value="all">All</option>
            <option value="discovered">Discovered</option>
            <option value="scoring">Scoring</option>
            <option value="prefiltered">Prefiltered</option>
            <option value="scored">Scored</option>
            <option value="failed">Failed</option>
          </select>
        </label>
      </div>

      <GlassPanel>
        {rows.length === 0 ? (
          <EmptyState icon={Inbox} title="No results match these filters" />
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fitness</TableHead>
                <TableHead>Title</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>New</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Review</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell>
                    {r.match ? <FitnessBadge fitness={r.match.fitness} /> : "—"}
                  </TableCell>
                  <TableCell>
                    {r.match ? (
                      <Link
                        to={`/matches/${r.match.id}`}
                        className="hover:text-brand"
                      >
                        {r.offer?.title}
                      </Link>
                    ) : (
                      r.offer?.title
                    )}
                  </TableCell>
                  <TableCell className="text-ink-dim">{r.offer?.company}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{r.offer?.source}</Badge>
                  </TableCell>
                  <TableCell className="text-ink-dim">
                    {r.is_new ? "new" : "seen"}
                  </TableCell>
                  <TableCell>
                    <ResultStatusChip status={r.status} error={r.error} />
                  </TableCell>
                  <TableCell>
                    <ReviewChip match={r.match} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </GlassPanel>
    </div>
  );
}
