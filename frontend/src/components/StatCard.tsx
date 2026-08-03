import type { LucideIcon } from "lucide-react";
import { GlassPanel } from "@/components/GlassPanel";

export function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: number | string;
  icon: LucideIcon;
}) {
  return (
    <GlassPanel className="flex items-center gap-4">
      <div className="rounded-xl bg-brand/10 p-2.5 text-brand">
        <Icon className="size-5" aria-hidden />
      </div>
      <div>
        <p className="font-mono text-2xl font-semibold leading-tight">{value}</p>
        <p className="text-sm text-ink-dim">{label}</p>
      </div>
    </GlassPanel>
  );
}
