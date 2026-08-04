import type { WorkMode } from "@/lib/api/types";

const LABELS: Record<WorkMode, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
};

/** null when the posting never stated it — show nothing rather than a guess. */
export function workModeLabel(mode: WorkMode | null | undefined): string | null {
  return mode ? LABELS[mode] : null;
}
