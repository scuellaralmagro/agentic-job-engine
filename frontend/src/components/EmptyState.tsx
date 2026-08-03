import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  hint,
  action,
}: {
  icon: LucideIcon;
  title: string;
  hint?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-2 py-12 text-center">
      <Icon className="size-8 text-ink-dim" aria-hidden />
      <p className="font-medium">{title}</p>
      {hint && <p className="max-w-sm text-sm text-ink-dim">{hint}</p>}
      {action}
    </div>
  );
}
