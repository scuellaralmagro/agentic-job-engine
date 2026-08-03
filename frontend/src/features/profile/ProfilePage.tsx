import { User } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/EmptyState";
import { GlassPanel } from "@/components/GlassPanel";
import { useProfile } from "./queries";

export function Provenance({ refs }: { refs: number[] }) {
  if (refs.length === 0)
    return (
      <Badge variant="outline" className="text-[10px] text-ink-dim">
        manual
      </Badge>
    );
  return (
    <Badge variant="outline" className="font-mono text-[10px] text-ink-dim">
      src {refs.join(",")}
    </Badge>
  );
}

export function ProfilePage() {
  const { data: profile, isPending, isError } = useProfile();

  if (isPending) return <p className="text-ink-dim">Loading…</p>;
  if (isError || !profile)
    return (
      <GlassPanel>
        <EmptyState icon={User} title="Couldn't load the profile" />
      </GlassPanel>
    );

  const totals = [
    ["Skills", profile.skills.length],
    ["Experiences", profile.experiences.length],
    ["Education", profile.education.length],
    ["Achievements", profile.achievements.length],
    ["Languages", profile.languages.length],
  ] as const;

  return (
    <div className="space-y-5">
      <GlassPanel className="flex flex-wrap items-center gap-6">
        <div className="mr-auto">
          <h1 className="text-xl font-semibold">
            {profile.contact.full_name ?? "Your profile"}
          </h1>
          <p className="text-sm text-ink-dim">
            {[
              profile.contact.headline,
              profile.contact.location,
              profile.contact.email,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        {totals.map(([label, n]) => (
          <div key={label} className="text-center">
            <p className="font-mono text-lg font-semibold">{n}</p>
            <p className="text-xs text-ink-dim">{label}</p>
          </div>
        ))}
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-2 font-medium">Skills</h2>
        <div className="flex flex-wrap gap-1.5">
          {profile.skills.map((s) => (
            <span
              key={s.name}
              className="flex items-center gap-1 rounded-lg bg-surface px-2 py-1 text-sm"
            >
              {s.name}
              <Provenance refs={s.source_refs} />
            </span>
          ))}
        </div>
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-2 font-medium">Experience</h2>
        <ul className="space-y-3">
          {profile.experiences.map((exp) => (
            <li
              key={`${exp.company}-${exp.title}`}
              className="rounded-xl bg-surface p-3"
            >
              <div className="flex items-center gap-2">
                <p className="mr-auto font-medium">
                  {exp.title} · {exp.company}
                </p>
                <span className="text-xs text-ink-dim">
                  {exp.start ?? "?"} – {exp.end ?? "now"}
                </span>
                <Provenance refs={exp.source_refs} />
              </div>
              <ul className="mt-1 list-inside list-disc text-sm text-ink-dim">
                {exp.bullets.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-2 font-medium">
          Education, achievements &amp; languages
        </h2>
        <ul className="space-y-1 text-sm">
          {profile.education.map((e) => (
            <li key={e.institution} className="flex items-center gap-2">
              <span className="mr-auto">
                {e.institution} {e.degree && `— ${e.degree}`}
              </span>
              <Provenance refs={e.source_refs} />
            </li>
          ))}
          {profile.achievements.map((a) => (
            <li key={a.text} className="flex items-center gap-2">
              <span className="mr-auto">{a.text}</span>
              <Provenance refs={a.source_refs} />
            </li>
          ))}
          {profile.languages.map((l) => (
            <li key={l.name} className="flex items-center gap-2">
              <span className="mr-auto">
                {l.name} {l.level && `(${l.level})`}
              </span>
              <Provenance refs={l.source_refs} />
            </li>
          ))}
        </ul>
      </GlassPanel>
    </div>
  );
}
