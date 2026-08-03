import { cn } from "@/lib/utils";
import { fitnessLevel, type FitnessLevel } from "@/lib/fitness";

const styles: Record<FitnessLevel, string> = {
  high: "text-ok border-ok/40 bg-ok/10",
  medium: "text-warn border-warn/40 bg-warn/10",
  low: "text-danger border-danger/40 bg-danger/10",
};

export function FitnessBadge({ fitness }: { fitness: number }) {
  return (
    <span
      data-testid="fitness-badge"
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-xs font-medium",
        styles[fitnessLevel(fitness)],
      )}
    >
      {Math.round(fitness)}%
    </span>
  );
}
