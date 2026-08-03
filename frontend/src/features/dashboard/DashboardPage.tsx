import { CheckCheck, FileText, Inbox, Play, Search, Sparkles } from "lucide-react";
import { Link } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { FitnessBadge } from "@/components/FitnessBadge";
import { GlassPanel } from "@/components/GlassPanel";
import { StatCard } from "@/components/StatCard";
import { useQueue } from "@/features/queue/queries";
import {
  useDocs,
  useOffers,
  useRuns,
  useRunSearch,
  useSearches,
} from "./queries";

const runTone: Record<string, string> = {
  ok: "text-ok",
  partial: "text-warn",
  failed: "text-danger",
};

export function DashboardPage() {
  const pending = useQueue("new", undefined);
  const accepted = useQueue("accepted", undefined);
  const offers = useOffers();
  const runs = useRuns();
  const searches = useSearches();
  const docs = useDocs();
  const runSearch = useRunSearch();

  const weekAgo = Date.now() - 7 * 24 * 3600 * 1000;
  const discovered7d = (offers.data ?? []).filter(
    (o) => new Date(o.created_at).getTime() >= weekAgo,
  ).length;
  const top = (pending.data ?? []).slice(0, 5);

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold">Dashboard</h1>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Offers (7 days)" value={discovered7d} icon={Sparkles} />
        <StatCard
          label="Pending review"
          value={pending.data?.length ?? "…"}
          icon={Inbox}
        />
        <StatCard
          label="Accepted"
          value={accepted.data?.length ?? "…"}
          icon={CheckCheck}
        />
        <StatCard
          label="Docs generated"
          value={docs.data?.length ?? "…"}
          icon={FileText}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <GlassPanel>
          <h2 className="mb-3 font-medium">Top pending matches</h2>
          {top.length === 0 ? (
            <EmptyState
              icon={Inbox}
              title="Nothing to review"
              hint="Run a saved search to discover and score offers."
            />
          ) : (
            <ul className="space-y-2">
              {top.map((m) => (
                <li
                  key={m.id}
                  className="flex items-center gap-3 rounded-lg bg-surface px-3 py-2"
                >
                  <FitnessBadge fitness={m.fitness} />
                  <Link
                    to={`/matches/${m.id}`}
                    className="min-w-0 flex-1 truncate hover:text-brand"
                  >
                    {m.offer?.title}
                  </Link>
                  <span className="truncate text-sm text-ink-dim">
                    {m.offer?.company}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </GlassPanel>

        <GlassPanel>
          <h2 className="mb-3 font-medium">Discovery runs</h2>
          {(runs.data ?? []).length === 0 ? (
            <EmptyState
              icon={Play}
              title="No runs yet"
              hint="Trigger one from a saved search below."
            />
          ) : (
            <ul className="space-y-2 text-sm">
              {runs.data!.slice(0, 8).map((r) => (
                <li
                  key={r.id}
                  className="flex items-center gap-3 rounded-lg bg-surface px-3 py-2"
                >
                  {r.finished_at === null ? (
                    <span className="animate-pulse text-brand">running…</span>
                  ) : (
                    <span className={runTone[r.status]}>{r.status}</span>
                  )}
                  <span className="text-ink-dim">
                    {new Date(r.started_at).toLocaleString()}
                  </span>
                  <span className="ml-auto font-mono">
                    {r.offers_new}/{r.offers_found} new
                  </span>
                </li>
              ))}
            </ul>
          )}
        </GlassPanel>
      </div>

      <GlassPanel>
        <h2 className="mb-3 font-medium">Saved searches</h2>
        {(searches.data ?? []).length === 0 ? (
          <EmptyState
            icon={Search}
            title="No searches yet"
            hint="Create one in Settings to start discovering offers."
            action={
              <Button asChild variant="secondary" size="sm">
                <Link to="/settings">Open Settings</Link>
              </Button>
            }
          />
        ) : (
          <ul className="grid gap-2 md:grid-cols-2">
            {searches.data!.map((s) => (
              <li
                key={s.id}
                className="flex items-center gap-3 rounded-lg bg-surface px-3 py-2"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{s.name}</p>
                  <p className="truncate text-xs text-ink-dim">
                    {s.query}
                    {s.schedule ? ` · ${s.schedule}` : " · manual"}
                  </p>
                </div>
                {s.schedule && <Badge variant="outline">scheduled</Badge>}
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={runSearch.isPending}
                  onClick={() => runSearch.mutate(s.id)}
                >
                  <Play className="size-3.5" /> Run
                </Button>
              </li>
            ))}
          </ul>
        )}
      </GlassPanel>
    </div>
  );
}
