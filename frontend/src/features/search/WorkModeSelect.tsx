import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import type { WorkMode } from "@/lib/api/types";

const MODES: { value: WorkMode; label: string }[] = [
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "onsite", label: "On-site" },
];

export function WorkModeSelect({
  value,
  onChange,
}: {
  value: WorkMode[];
  onChange: (next: WorkMode[]) => void;
}) {
  const toggle = (mode: WorkMode) =>
    onChange(
      value.includes(mode) ? value.filter((m) => m !== mode) : [...value, mode],
    );

  return (
    <div>
      <Label>Work mode</Label>
      <div className="flex gap-1.5">
        {MODES.map(({ value: mode, label }) => {
          const on = value.includes(mode);
          return (
            <button
              key={mode}
              type="button"
              aria-pressed={on}
              onClick={() => toggle(mode)}
              className={cn(
                "rounded-full border px-3 py-1.5 text-sm transition-colors",
                on
                  ? "border-brand/40 bg-brand/10 text-brand"
                  : "border-line bg-surface text-ink-dim hover:text-ink",
              )}
            >
              {label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
