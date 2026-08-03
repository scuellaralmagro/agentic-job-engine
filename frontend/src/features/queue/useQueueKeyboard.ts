import { useEffect, useState } from "react";
import type { MatchOut } from "@/lib/api/types";

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  );
}

export function useQueueKeyboard(
  rows: MatchOut[],
  handlers: {
    onAccept: (m: MatchOut) => void;
    onDismiss: (m: MatchOut) => void;
  },
): number | null {
  const [index, setIndex] = useState(-1);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (isTyping(e.target) || rows.length === 0) return;
      if (e.key === "j") setIndex((i) => Math.min(i + 1, rows.length - 1));
      else if (e.key === "k") setIndex((i) => Math.max(i - 1, 0));
      else if (e.key === "a" && rows[index]) handlers.onAccept(rows[index]);
      else if (e.key === "d" && rows[index]) handlers.onDismiss(rows[index]);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  const selected =
    index >= 0 ? rows[Math.min(index, rows.length - 1)] : undefined;
  return selected?.id ?? null;
}
