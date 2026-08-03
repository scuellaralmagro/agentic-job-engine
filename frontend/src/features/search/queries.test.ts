import type { RunOut } from "@/lib/api/types";
import { resultsRefetchInterval } from "./queries";

const run = (status: RunOut["status"]): RunOut => ({
  id: 1,
  saved_search_id: null,
  kind: "manual",
  term: "python",
  filters: {},
  status,
  offers_found: 0,
  offers_new: 0,
  source_results: [],
  started_at: "2026-08-03T00:00:00",
  finished_at: status === "running" ? null : "2026-08-03T00:01:00",
});

test("polls while the run is going", () => {
  expect(resultsRefetchInterval(run("running"))).toBe(2000);
});

test("stops polling once the run reaches a terminal state", () => {
  // a finished run never changes again — keep polling and it costs forever
  expect(resultsRefetchInterval(run("ok"))).toBe(false);
  expect(resultsRefetchInterval(run("partial"))).toBe(false);
  expect(resultsRefetchInterval(run("failed"))).toBe(false);
  expect(resultsRefetchInterval(undefined)).toBe(false);
});
