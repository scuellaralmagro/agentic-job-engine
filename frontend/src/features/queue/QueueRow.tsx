import { Check, X } from "lucide-react";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { FitnessBadge } from "@/components/FitnessBadge";
import { cn } from "@/lib/utils";
import type { MatchOut } from "@/lib/api/types";
import { workModeLabel } from "@/lib/workMode";

export function QueueRow({
  match,
  selected,
  onAccept,
  onDismiss,
}: {
  match: MatchOut;
  selected: boolean;
  onAccept: () => void;
  onDismiss: () => void;
}) {
  const offer = match.offer;
  return (
    <div
      data-testid="queue-row"
      data-selected={selected || undefined}
      className={cn(
        "flex items-center gap-4 rounded-xl border border-transparent bg-surface px-4 py-3 transition-colors",
        selected && "border-brand/50",
      )}
    >
      <FitnessBadge fitness={match.fitness} />
      <div className="min-w-0 flex-1">
        <Link
          to={`/matches/${match.id}`}
          className="block truncate font-medium hover:text-brand"
        >
          {offer?.title ?? `Offer #${match.offer_id}`}
        </Link>
        <p className="truncate text-sm text-ink-dim">
          {[offer?.company, offer?.location, workModeLabel(offer?.work_mode)]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
      <div className="hidden items-center gap-1.5 lg:flex">
        {offer?.skills.slice(0, 2).map((s) => (
          <Badge key={s} variant="secondary">
            {s}
          </Badge>
        ))}
        {match.gaps[0] && (
          <Badge variant="outline" className="text-warn">
            gap: {match.gaps[0].requirement}
          </Badge>
        )}
      </div>
      {offer?.source && <Badge variant="outline">{offer.source}</Badge>}
      <div className="flex gap-1.5">
        <Button size="sm" variant="secondary" onClick={onAccept}>
          <Check className="size-4" /> Accept
        </Button>
        <Button size="sm" variant="ghost" onClick={onDismiss}>
          <X className="size-4" /> Dismiss
        </Button>
      </div>
    </div>
  );
}
