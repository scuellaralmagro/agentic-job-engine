import { useState } from "react";
import { Pencil, Plus, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type {
  Achievement,
  Education,
  Experience,
  LanguageItem,
  Skill,
} from "@/lib/api/types";
import { Provenance } from "./ProfilePage";

// ---------- Skills ----------

export function SkillsEditor({
  skills,
  onChange,
}: {
  skills: Skill[];
  onChange: (skills: Skill[]) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");

  const add = () => {
    if (!name.trim()) return;
    onChange([
      ...skills,
      {
        name: name.trim(),
        category: category.trim() || null,
        level: null,
        source_refs: [],
      },
    ]);
    setName("");
    setCategory("");
    setAdding(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        {skills.map((s) => (
          <span
            key={s.name}
            className="flex items-center gap-1 rounded-lg bg-surface px-2 py-1 text-sm"
          >
            {s.name}
            <Provenance refs={s.source_refs} />
            <button
              aria-label={`Remove ${s.name}`}
              className="text-ink-dim hover:text-danger"
              onClick={() => onChange(skills.filter((x) => x.name !== s.name))}
            >
              <X className="size-3" />
            </button>
          </span>
        ))}
      </div>
      {adding ? (
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <Label htmlFor="skill-name">Name</Label>
            <Input
              id="skill-name"
              className="bg-surface"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="skill-cat">Category</Label>
            <Input
              id="skill-cat"
              className="bg-surface"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
            />
          </div>
          <Button size="sm" onClick={add}>
            Add
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setAdding(false)}>
            Cancel
          </Button>
        </div>
      ) : (
        <Button size="sm" variant="secondary" onClick={() => setAdding(true)}>
          <Plus className="size-3.5" /> Add skill
        </Button>
      )}
    </div>
  );
}

// ---------- Experiences ----------

function ExperienceDialog({
  initial,
  onSave,
  trigger,
  title,
}: {
  initial: Experience;
  onSave: (exp: Experience) => void;
  trigger: React.ReactNode;
  title: string;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState(initial);

  const set = (patch: Partial<Experience>) => setDraft({ ...draft, ...patch });

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) setDraft(initial);
      }}
    >
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="glass-elevated max-w-lg">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="exp-title">Title</Label>
            <Input
              id="exp-title"
              className="bg-surface"
              value={draft.title}
              onChange={(e) => set({ title: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="exp-company">Company</Label>
            <Input
              id="exp-company"
              className="bg-surface"
              value={draft.company}
              onChange={(e) => set({ company: e.target.value })}
            />
          </div>
          <div>
            <Label htmlFor="exp-start">Start</Label>
            <Input
              id="exp-start"
              className="bg-surface"
              value={draft.start ?? ""}
              onChange={(e) => set({ start: e.target.value || null })}
            />
          </div>
          <div>
            <Label htmlFor="exp-end">End (empty = present)</Label>
            <Input
              id="exp-end"
              className="bg-surface"
              value={draft.end ?? ""}
              onChange={(e) => set({ end: e.target.value || null })}
            />
          </div>
          <div className="col-span-2">
            <Label htmlFor="exp-desc">Description</Label>
            <Textarea
              id="exp-desc"
              rows={2}
              className="bg-surface"
              value={draft.description ?? ""}
              onChange={(e) => set({ description: e.target.value || null })}
            />
          </div>
          <div className="col-span-2">
            <Label htmlFor="exp-bullets">Bullets (one per line)</Label>
            <Textarea
              id="exp-bullets"
              rows={5}
              className="bg-surface"
              value={draft.bullets.join("\n")}
              onChange={(e) =>
                set({
                  bullets: e.target.value.split("\n").filter((b) => b.trim()),
                })
              }
            />
          </div>
        </div>
        <Button
          onClick={() => {
            onSave(draft);
            setOpen(false);
          }}
        >
          Save
        </Button>
      </DialogContent>
    </Dialog>
  );
}

const emptyExperience: Experience = {
  company: "",
  title: "",
  description: null,
  start: null,
  end: null,
  bullets: [],
  skills: [],
  source_refs: [],
};

export function ExperiencesEditor({
  experiences,
  onChange,
}: {
  experiences: Experience[];
  onChange: (experiences: Experience[]) => void;
}) {
  return (
    <div className="space-y-3">
      {experiences.map((exp, i) => (
        <div
          key={`${exp.company}-${exp.title}-${i}`}
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
            <ExperienceDialog
              title="Edit experience"
              initial={exp}
              onSave={(updated) =>
                onChange(experiences.map((x, j) => (j === i ? updated : x)))
              }
              trigger={
                <Button
                  size="sm"
                  variant="ghost"
                  aria-label={`Edit ${exp.title}`}
                >
                  <Pencil className="size-3.5" /> Edit
                </Button>
              }
            />
            <Button
              size="sm"
              variant="ghost"
              className="text-danger"
              aria-label={`Delete ${exp.title}`}
              onClick={() => onChange(experiences.filter((_, j) => j !== i))}
            >
              <Trash2 className="size-3.5" />
            </Button>
          </div>
          <ul className="mt-1 list-inside list-disc text-sm text-ink-dim">
            {exp.bullets.map((b) => (
              <li key={b}>{b}</li>
            ))}
          </ul>
        </div>
      ))}
      <ExperienceDialog
        title="Add experience"
        initial={emptyExperience}
        onSave={(exp) => onChange([...experiences, exp])}
        trigger={
          <Button size="sm" variant="secondary">
            <Plus className="size-3.5" /> Add experience
          </Button>
        }
      />
    </div>
  );
}

// ---------- Simple lists ----------

function SimpleListEditor<T>({
  items,
  onChange,
  display,
  makeItem,
  addLabel,
}: {
  items: T[];
  onChange: (items: T[]) => void;
  display: (item: T) => string;
  makeItem: (text: string) => T;
  addLabel: string;
}) {
  const [text, setText] = useState("");
  return (
    <div className="space-y-1.5">
      {items.map((item, i) => (
        <div key={display(item)} className="flex items-center gap-2 text-sm">
          <span className="mr-auto">{display(item)}</span>
          <button
            aria-label={`Remove ${display(item)}`}
            className="text-ink-dim hover:text-danger"
            onClick={() => onChange(items.filter((_, j) => j !== i))}
          >
            <X className="size-3.5" />
          </button>
        </div>
      ))}
      <div className="flex gap-2">
        <Input
          aria-label={addLabel}
          placeholder={addLabel}
          className="bg-surface"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <Button
          size="sm"
          variant="secondary"
          onClick={() => {
            if (!text.trim()) return;
            onChange([...items, makeItem(text.trim())]);
            setText("");
          }}
        >
          Add
        </Button>
      </div>
    </div>
  );
}

export function EducationEditor(props: {
  items: Education[];
  onChange: (items: Education[]) => void;
}) {
  return (
    <SimpleListEditor
      {...props}
      display={(e) =>
        [e.institution, e.degree, e.field].filter(Boolean).join(" — ")
      }
      makeItem={(text) => ({
        institution: text,
        degree: null,
        field: null,
        start: null,
        end: null,
        source_refs: [],
      })}
      addLabel="Add education (institution)"
    />
  );
}

export function AchievementsEditor(props: {
  items: Achievement[];
  onChange: (items: Achievement[]) => void;
}) {
  return (
    <SimpleListEditor
      {...props}
      display={(a) => a.text}
      makeItem={(text) => ({ text, source_refs: [] })}
      addLabel="Add achievement"
    />
  );
}

export function LanguagesEditor(props: {
  items: LanguageItem[];
  onChange: (items: LanguageItem[]) => void;
}) {
  return (
    <SimpleListEditor
      {...props}
      display={(l) => (l.level ? `${l.name} (${l.level})` : l.name)}
      makeItem={(text) => ({ name: text, level: null, source_refs: [] })}
      addLabel="Add language"
    />
  );
}
