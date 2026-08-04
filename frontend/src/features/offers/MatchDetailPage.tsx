import { ExternalLink } from "lucide-react";
import { useParams } from "react-router";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GlassPanel } from "@/components/GlassPanel";
import { useSetStatus } from "@/features/queue/queries";
import { AdaptActions } from "./AdaptActions";
import { FitnessPanel } from "./FitnessPanel";
import { useMatch } from "./queries";
import { workModeLabel } from "@/lib/workMode";

export function MatchDetailPage() {
  const { id } = useParams();
  const matchId = Number(id);
  const { data: match, isPending, isError, refetch } = useMatch(matchId);
  const setStatus = useSetStatus();

  if (isPending) return <p className="text-ink-dim">Loading…</p>;
  if (isError || !match)
    return (
      <GlassPanel className="text-center">
        <p className="text-danger">Couldn't load this match.</p>
        <Button variant="ghost" onClick={() => refetch()}>
          Retry
        </Button>
      </GlassPanel>
    );

  const offer = match.offer;
  const act = (action: "accept" | "dismiss") =>
    setStatus.mutate(
      { id: match.id, action },
      {
        onSuccess: () =>
          toast(action === "accept" ? "Accepted" : "Dismissed"),
      },
    );

  return (
    <div className="grid gap-5 xl:grid-cols-5">
      <div className="space-y-5 xl:col-span-3">
        <GlassPanel>
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <h1 className="mr-auto text-xl font-semibold">
              {offer?.title ?? `Offer #${match.offer_id}`}
            </h1>
            <Badge variant="outline">{offer?.source}</Badge>
            {match.status !== "new" && (
              <Badge variant="secondary">{match.status}</Badge>
            )}
          </div>
          <p className="text-sm text-ink-dim">
            {[
              offer?.company,
              offer?.location,
              offer?.seniority,
              workModeLabel(offer?.work_mode),
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <div className="my-3 flex flex-wrap gap-1.5">
            {offer?.skills.map((s) => (
              <Badge key={s} variant="secondary">
                {s}
              </Badge>
            ))}
          </div>
          <div className="whitespace-pre-wrap rounded-xl bg-surface p-4 text-sm leading-relaxed">
            {offer?.description ?? "No description captured."}
          </div>
          {offer?.url && (
            <a
              href={offer.url}
              target="_blank"
              rel="noreferrer"
              className="mt-3 inline-flex items-center gap-1 text-sm text-brand hover:underline"
            >
              View original posting <ExternalLink className="size-3.5" />
            </a>
          )}
        </GlassPanel>
      </div>
      <div className="space-y-5 xl:col-span-2">
        <FitnessPanel match={match} />
        <GlassPanel className="space-y-3">
          <div className="flex gap-2">
            <Button
              className="flex-1"
              disabled={match.status === "accepted" || setStatus.isPending}
              onClick={() => act("accept")}
            >
              Accept
            </Button>
            <Button
              variant="secondary"
              className="flex-1"
              disabled={match.status === "dismissed" || setStatus.isPending}
              onClick={() => act("dismiss")}
            >
              Dismiss
            </Button>
          </div>
          <AdaptActions match={match} />
        </GlassPanel>
      </div>
    </div>
  );
}
