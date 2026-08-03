import { GlassPanel } from "@/components/GlassPanel";
import { fitnessLevel } from "@/lib/fitness";
import { cn } from "@/lib/utils";
import type { MatchOut, RubricCriterion } from "@/lib/api/types";

const dialColor = {
  high: "stroke-ok",
  medium: "stroke-warn",
  low: "stroke-danger",
} as const;

const barColor = {
  high: "bg-ok",
  medium: "bg-warn",
  low: "bg-danger",
} as const;

function Dial({ fitness }: { fitness: number }) {
  const r = 54;
  const c = 2 * Math.PI * r;
  return (
    <div data-testid="fitness-dial" className="relative mx-auto size-32">
      <svg viewBox="0 0 128 128" className="size-full -rotate-90">
        <circle
          cx="64"
          cy="64"
          r={r}
          className="stroke-white/10"
          strokeWidth="10"
          fill="none"
        />
        <circle
          cx="64"
          cy="64"
          r={r}
          className={cn(dialColor[fitnessLevel(fitness)], "transition-all")}
          strokeWidth="10"
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - fitness / 100)}
        />
      </svg>
      <p className="absolute inset-0 grid place-items-center font-mono text-2xl font-semibold">
        {Math.round(fitness)}%
      </p>
    </div>
  );
}

export function FitnessPanel({ match }: { match: MatchOut }) {
  // Belt and braces: the API filters the rubric down to scored dimensions, but a
  // stored rubric also holds the dealbreaker flag and a null reason, and reading
  // .score off those took down the whole route.
  const dimensions = Object.entries(match.rubric ?? {}).filter(
    (entry): entry is [string, RubricCriterion] =>
      typeof entry[1] === "object" &&
      entry[1] !== null &&
      typeof (entry[1] as RubricCriterion).score === "number",
  );

  return (
    <GlassPanel className="space-y-5">
      <Dial fitness={match.fitness} />
      {match.dealbreaker && (
        <div className="rounded-xl border border-danger/40 bg-danger/10 p-3 text-sm">
          <p className="font-medium text-danger">Dealbreaker</p>
          <p className="text-ink-dim">
            {match.dealbreaker_reason ??
              "A hard blocker was found that the candidate cannot resolve."}
          </p>
        </div>
      )}
      <div className="space-y-3">
        {dimensions.map(([name, crit]) => (
          <div key={name}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="capitalize">{name}</span>
              <span className="font-mono text-ink-dim">{crit.score}</span>
            </div>
            <div className="h-1.5 rounded-full bg-white/10">
              <div
                className={cn(
                  "h-full rounded-full",
                  barColor[fitnessLevel(crit.score)],
                )}
                style={{ width: `${Math.min(crit.score, 100)}%` }}
              />
            </div>
            <p className="mt-0.5 text-xs text-ink-dim">{crit.evidence}</p>
          </div>
        ))}
      </div>
      {match.gaps.length > 0 && (
        <div>
          <p className="mb-1 text-sm font-medium">Gaps</p>
          <ul className="space-y-1 text-sm text-ink-dim">
            {match.gaps.map((g) => (
              <li key={g.requirement}>
                <span className="text-warn">▲</span> {g.requirement}{" "}
                <span className="text-xs">({g.severity})</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {match.explanation && (
        <p className="border-t border-line pt-3 text-sm text-ink-dim">
          {match.explanation}
        </p>
      )}
    </GlassPanel>
  );
}
