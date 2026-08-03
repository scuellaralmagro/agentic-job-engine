import { useEffect, useState } from "react";
import { ArrowLeft, FileDown, X } from "lucide-react";
import { Link, useParams } from "react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { GlassPanel } from "@/components/GlassPanel";
import type { TailoredCv } from "@/lib/api/types";
import {
  usePatchProjection,
  useProjection,
  useRenderProjection,
} from "./queries";

type KeyField =
  | "skill_keys"
  | "achievement_keys"
  | "education_keys"
  | "language_keys";

export function ProjectionEditorPage() {
  const { id } = useParams();
  const projectionId = Number(id);
  const { data: projection, isPending } = useProjection(projectionId);
  const patch = usePatchProjection(projectionId);
  const render = useRenderProjection();

  const [name, setName] = useState("");
  const [cv, setCv] = useState<TailoredCv | null>(null);

  useEffect(() => {
    if (projection && cv === null) {
      setName(projection.name);
      setCv(projection.content_json);
    }
  }, [projection, cv]);

  if (isPending || !cv || !projection)
    return <p className="text-ink-dim">Loading…</p>;

  const setBullet = (expIdx: number, bulletIdx: number, text: string) =>
    setCv({
      ...cv,
      experiences: cv.experiences.map((exp, i) =>
        i === expIdx
          ? {
              ...exp,
              bullets: exp.bullets.map((b, j) =>
                j === bulletIdx ? { ...b, text } : b,
              ),
            }
          : exp,
      ),
    });

  const removeKey = (field: KeyField, key: string) =>
    setCv({ ...cv, [field]: cv[field].filter((k) => k !== key) });

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link to="/library">
            <ArrowLeft className="size-4" /> Library
          </Link>
        </Button>
        <h1 className="mr-auto text-xl font-semibold">Edit tailored CV</h1>
        <Button
          variant="secondary"
          disabled={patch.isPending}
          onClick={() => patch.mutate({ content_json: cv, name })}
        >
          {patch.isPending ? "Saving…" : "Save"}
        </Button>
        <Button
          disabled={render.isPending}
          onClick={() => render.mutate(projectionId)}
        >
          <FileDown className="size-4" />
          {render.isPending ? "Rendering…" : "Render PDF"}
        </Button>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <div className="space-y-4 xl:col-span-2">
          <GlassPanel className="space-y-3">
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                className="bg-surface"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="headline">Headline</Label>
              <Input
                id="headline"
                className="bg-surface"
                value={cv.headline}
                onChange={(e) => setCv({ ...cv, headline: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="summary">Summary</Label>
              <Textarea
                id="summary"
                rows={4}
                className="bg-surface"
                value={cv.summary}
                onChange={(e) => setCv({ ...cv, summary: e.target.value })}
              />
            </div>
          </GlassPanel>

          <GlassPanel className="space-y-4">
            <h2 className="font-medium">Experiences</h2>
            {cv.experiences.map((exp, i) => (
              <div
                key={exp.source_key}
                className="space-y-2 rounded-xl bg-surface p-3"
              >
                <p className="font-mono text-xs text-ink-dim">
                  {exp.source_key}
                </p>
                {exp.bullets.map((b, j) => (
                  <Textarea
                    key={b.source_key}
                    rows={2}
                    className="bg-surface-2"
                    value={b.text}
                    onChange={(e) => setBullet(i, j, e.target.value)}
                  />
                ))}
              </div>
            ))}
          </GlassPanel>

          <GlassPanel className="space-y-3">
            <h2 className="font-medium">Included items</h2>
            {(
              [
                ["skill_keys", "Skills"],
                ["achievement_keys", "Achievements"],
                ["education_keys", "Education"],
                ["language_keys", "Languages"],
              ] as const
            ).map(([field, label]) => (
              <div key={field}>
                <p className="mb-1 text-sm text-ink-dim">{label}</p>
                <div className="flex flex-wrap gap-1.5">
                  {cv[field].length === 0 && (
                    <span className="text-xs text-ink-dim">none</span>
                  )}
                  {cv[field].map((key) => (
                    <Badge
                      key={key}
                      variant="secondary"
                      className="gap-1 font-mono"
                    >
                      {key}
                      <button
                        aria-label={`Remove ${key}`}
                        onClick={() => removeKey(field, key)}
                      >
                        <X className="size-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </GlassPanel>
        </div>

        <GlassPanel className="h-fit space-y-3">
          <h2 className="font-medium">Suggestions</h2>
          {projection.suggestions.length === 0 && (
            <p className="text-sm text-ink-dim">No suggestions recorded.</p>
          )}
          {projection.suggestions.map((s, i) => (
            <div key={i} className="rounded-xl bg-surface p-3 text-sm">
              <div className="mb-1 flex items-center gap-2">
                <Badge variant="outline">{s.kind}</Badge>
                <span className="truncate font-mono text-xs text-ink-dim">
                  {s.source_key}
                </span>
              </div>
              {s.before && (
                <p className="text-ink-dim line-through">{s.before}</p>
              )}
              {s.after && <p>{s.after}</p>}
              <p className="mt-1 text-xs text-ink-dim">{s.reason}</p>
            </div>
          ))}
        </GlassPanel>
      </div>
    </div>
  );
}
