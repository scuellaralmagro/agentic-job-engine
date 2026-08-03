import { useEffect, useState } from "react";
import { Trash2, User } from "lucide-react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { GlassPanel } from "@/components/GlassPanel";
import type { ProfileData } from "@/lib/api/types";
import {
  AchievementsEditor,
  EducationEditor,
  ExperiencesEditor,
  LanguagesEditor,
  SkillsEditor,
} from "./editors";
import { IngestCard } from "./IngestCard";
import {
  useProfile,
  useResetProfile,
  useSaveProfile,
  useSourceDocuments,
} from "./queries";

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
  const save = useSaveProfile();
  const sourceDocs = useSourceDocuments();
  const reset = useResetProfile();
  const [draft, setDraft] = useState<ProfileData | null>(null);

  useEffect(() => {
    if (profile && draft === null) setDraft(profile);
  }, [profile, draft]);

  if (isPending) return <p className="text-ink-dim">Loading…</p>;
  if (isError || !profile)
    return (
      <GlassPanel>
        <EmptyState icon={User} title="Couldn't load the profile" />
      </GlassPanel>
    );
  if (!draft) return <p className="text-ink-dim">Loading…</p>;

  const dirty = JSON.stringify(draft) !== JSON.stringify(profile);
  const totals = [
    ["Skills", draft.skills.length],
    ["Experiences", draft.experiences.length],
    ["Education", draft.education.length],
    ["Achievements", draft.achievements.length],
    ["Languages", draft.languages.length],
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
        <div className="w-full">
          <IngestCard />
        </div>
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-2 font-medium">Skills</h2>
        <SkillsEditor
          skills={draft.skills}
          onChange={(skills) => setDraft({ ...draft, skills })}
        />
      </GlassPanel>

      <GlassPanel>
        <h2 className="mb-2 font-medium">Experience</h2>
        <ExperiencesEditor
          experiences={draft.experiences}
          onChange={(experiences) => setDraft({ ...draft, experiences })}
        />
      </GlassPanel>

      <div className="grid gap-5 lg:grid-cols-3">
        <GlassPanel>
          <h2 className="mb-2 font-medium">Education</h2>
          <EducationEditor
            items={draft.education}
            onChange={(education) => setDraft({ ...draft, education })}
          />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-2 font-medium">Achievements</h2>
          <AchievementsEditor
            items={draft.achievements}
            onChange={(achievements) => setDraft({ ...draft, achievements })}
          />
        </GlassPanel>
        <GlassPanel>
          <h2 className="mb-2 font-medium">Languages</h2>
          <LanguagesEditor
            items={draft.languages}
            onChange={(languages) => setDraft({ ...draft, languages })}
          />
        </GlassPanel>
      </div>

      <GlassPanel>
        <h2 className="mb-2 font-medium">Source documents</h2>
        {(sourceDocs.data ?? []).length === 0 ? (
          <p className="text-sm text-ink-dim">Nothing ingested yet.</p>
        ) : (
          <ul className="space-y-1 text-sm">
            {sourceDocs.data!.map((d) => (
              <li key={d.id} className="flex items-center gap-2">
                <Badge variant="outline">{d.kind}</Badge>
                <span className="mr-auto truncate text-ink-dim">
                  {d.file_ref}
                </span>
                <Badge
                  variant={d.status === "extracted" ? "secondary" : "outline"}
                >
                  {d.status}
                </Badge>
              </li>
            ))}
          </ul>
        )}
      </GlassPanel>

      <GlassPanel className="flex flex-wrap items-center gap-4 border-danger/30">
        <div className="mr-auto">
          <h2 className="font-medium text-danger">Danger zone</h2>
          <p className="text-sm text-ink-dim">
            Delete the entire profile, every ingested document, and its stored
            copies.
          </p>
        </div>
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" className="text-danger">
              <Trash2 className="size-4" /> Delete profile
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent className="glass-elevated">
            <AlertDialogHeader>
              <AlertDialogTitle>Delete everything in the profile?</AlertDialogTitle>
              <AlertDialogDescription>
                This clears every skill, experience, education entry, achievement
                and language, deletes the {sourceDocs.data?.length ?? 0} ingested
                document{(sourceDocs.data?.length ?? 0) === 1 ? "" : "s"} along
                with the uploaded copies on disk, and drops the profile
                embeddings. You can re-ingest afterwards. Saved offers and
                tailored CVs are kept, but their fitness scores will be stale
                until you rebuild the profile and rescore. This cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                disabled={reset.isPending}
                onClick={() =>
                  // drop the local draft too, or the page keeps showing the old
                  // profile and reports phantom unsaved changes
                  reset.mutate(undefined, { onSuccess: () => setDraft(null) })
                }
              >
                {reset.isPending ? "Deleting…" : "Delete everything"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </GlassPanel>

      {dirty && (
        <div className="glass-elevated sticky bottom-4 flex items-center gap-3 px-4 py-3">
          <p className="mr-auto text-sm text-ink-dim">Unsaved changes</p>
          <Button variant="ghost" onClick={() => setDraft(profile)}>
            Discard
          </Button>
          <Button disabled={save.isPending} onClick={() => save.mutate(draft)}>
            {save.isPending ? "Saving…" : "Save profile"}
          </Button>
        </div>
      )}
    </div>
  );
}
