import { Inbox } from "lucide-react";
import { useSearchParams } from "react-router";
import { toast } from "sonner";
import { EmptyState } from "@/components/EmptyState";
import { GlassPanel } from "@/components/GlassPanel";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { MatchOut, MatchStatus } from "@/lib/api/types";
import { QueueRow } from "./QueueRow";
import { useQueue, useSetStatus } from "./queries";

export function QueuePage() {
  const [params, setParams] = useSearchParams();
  const status = (params.get("status") ?? "new") as MatchStatus;
  const min = Number(params.get("min") ?? 0) || undefined;
  const q = params.get("q") ?? "";
  const sort = params.get("sort") ?? "fitness";

  const { data, isPending, isError, refetch } = useQueue(status, min);
  const setStatus = useSetStatus();

  const setParam = (key: string, value: string) =>
    setParams(
      (p) => {
        if (value) p.set(key, value);
        else p.delete(key);
        return p;
      },
      { replace: true },
    );

  const act = (match: MatchOut, action: "accept" | "dismiss") => {
    setStatus.mutate(
      { id: match.id, action },
      {
        onSuccess: () =>
          toast(action === "accept" ? "Accepted" : "Dismissed", {
            action: {
              label: "Undo",
              onClick: () =>
                setStatus.mutate({ id: match.id, action: "reset" }),
            },
          }),
      },
    );
  };

  const needle = q.toLowerCase();
  const rows = (data ?? [])
    .filter(
      (m) =>
        !needle ||
        `${m.offer?.title} ${m.offer?.company}`.toLowerCase().includes(needle),
    )
    .sort((a, b) =>
      sort === "date"
        ? (b.offer?.created_at ?? "").localeCompare(a.offer?.created_at ?? "")
        : b.fitness - a.fitness,
    );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="mr-auto">
          <h1 className="text-xl font-semibold">Review Queue</h1>
          <p className="text-xs text-ink-dim">
            j/k navigate · a accept · d dismiss
          </p>
        </div>
        <Input
          placeholder="Search title or company…"
          value={q}
          onChange={(e) => setParam("q", e.target.value)}
          className="w-56 bg-surface"
        />
        <Select value={status} onValueChange={(v) => setParam("status", v)}>
          <SelectTrigger className="w-36 bg-surface">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="new">New</SelectItem>
            <SelectItem value="accepted">Accepted</SelectItem>
            <SelectItem value="dismissed">Dismissed</SelectItem>
          </SelectContent>
        </Select>
        <Select
          value={String(min ?? 0)}
          onValueChange={(v) => setParam("min", v === "0" ? "" : v)}
        >
          <SelectTrigger className="w-32 bg-surface">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="0">Any fitness</SelectItem>
            <SelectItem value="50">≥ 50%</SelectItem>
            <SelectItem value="75">≥ 75%</SelectItem>
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={(v) => setParam("sort", v)}>
          <SelectTrigger className="w-32 bg-surface">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="fitness">By fitness</SelectItem>
            <SelectItem value="date">By date</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <GlassPanel className="space-y-2">
        {isPending && <p className="py-8 text-center text-ink-dim">Loading…</p>}
        {isError && (
          <EmptyState
            icon={Inbox}
            title="Couldn't load the queue"
            hint="Check that the backend is running."
            action={
              <button className="text-sm text-brand" onClick={() => refetch()}>
                Retry
              </button>
            }
          />
        )}
        {data && rows.length === 0 && (
          <EmptyState
            icon={Inbox}
            title="Queue is empty"
            hint="Scored offers above the threshold appear here. Run a saved search from Settings to discover offers."
          />
        )}
        {rows.map((m) => (
          <QueueRow
            key={m.id}
            match={m}
            selected={false}
            onAccept={() => act(m, "accept")}
            onDismiss={() => act(m, "dismiss")}
          />
        ))}
      </GlassPanel>
    </div>
  );
}
