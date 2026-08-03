import type { RunOut } from "@/lib/api/types";
import { runsRefetchInterval } from "./queries";

const run = (finished_at: string | null): RunOut => ({
  id: 1,
  saved_search_id: null,
  status: "ok",
  offers_found: 0,
  offers_new: 0,
  source_results: [],
  started_at: "2026-08-03T00:00:00",
  finished_at,
});

test("polls fast while a run is active", () => {
  expect(runsRefetchInterval([run(null), run("2026-08-03T01:00:00")])).toBe(
    2500,
  );
});

test("polls slowly when all runs are finished (or none exist)", () => {
  expect(runsRefetchInterval([run("2026-08-03T01:00:00")])).toBe(30_000);
  expect(runsRefetchInterval([])).toBe(30_000);
  expect(runsRefetchInterval(undefined)).toBe(30_000);
});
