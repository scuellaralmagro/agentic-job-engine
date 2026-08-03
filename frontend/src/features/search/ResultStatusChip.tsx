import { cn } from "@/lib/utils";
import type { ResultMatch, ResultStatus } from "@/lib/api/types";

const STYLES: Record<ResultStatus, string> = {
  discovered: "text-ink-dim border-line bg-white/5",
  scoring: "text-brand border-brand/40 bg-brand/10 animate-pulse",
  prefiltered: "text-warn/80 border-warn/30 bg-warn/5",
  scored: "text-ok border-ok/40 bg-ok/10",
  failed: "text-danger border-danger/40 bg-danger/10",
};

const LABELS: Record<ResultStatus, string> = {
  discovered: "discovered",
  scoring: "scoring…",
  prefiltered: "prefiltered",
  scored: "scored",
  failed: "failed",
};

const TITLES: Partial<Record<ResultStatus, string>> = {
  discovered: "Stored, not scored yet",
  scoring: "The LLM is reading this offer now",
  prefiltered: "Rejected by the vector prefilter — no LLM call was made",
};

export function ResultStatusChip({
  status,
  error,
}: {
  status: ResultStatus;
  error: string | null;
}) {
  return (
    <span
      data-testid="result-status"
      data-status={status}
      title={status === "failed" ? (error ?? "Scoring failed") : TITLES[status]}
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
        STYLES[status],
      )}
    >
      {LABELS[status]}
    </span>
  );
}

/** What *you* did, as opposed to what the system did. Deliberately a separate
 *  column: "rejected by the prefilter" and "rejected by you" are different facts. */
export function ReviewChip({ match }: { match: ResultMatch | null }) {
  let label = "—";
  if (match) {
    if (match.status === "accepted") label = "accepted";
    else if (match.status === "dismissed") label = "dismissed";
    else if (match.above_threshold) label = "queued";
  }
  return (
    <span data-testid="review-status" className="text-xs text-ink-dim">
      {label}
    </span>
  );
}
