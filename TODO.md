# TODO

## Agreed queue (2026-08-04)

In order. Work mode is done; the rest are next.

1. ~~Work mode detection + search selection~~ — done
2. **Scoring prompt cache reorder** — the prompt puts volatile content first so
   nothing caches. Reordering makes input ~90% cheaper on the highest-volume call,
   and scoring is ~75% of spend. Biggest cost win for the smallest change.
3. **Salary extraction + filter** — JobSpy returns min/max salary and
   `_to_raw_offer` discards it, exactly as it did `is_remote`. Same shape as work
   mode, so it follows cheaply.
4. **Fix cross-source dedup** — `compute_offer_hash` uses the raw location, so the
   same job on Indeed ("Madrid, MD, ES") and Tecnoempleo ("Madrid") is stored and
   scored twice. Normalizing location into the hash cuts duplicate spend.
5. **Application tracking** — the queue stops at `accepted`; there is no applied
   date, response or interview state. The CV and cover letter already hang off the
   match, so this is where they belong.

## Scheduled runs have no spend cap

**Found:** 2026-08-04, verifying the scheduled discovery path for the first time.

`run_saved_search` calls `run_discovery` without `max_offers`, and `discover_into_run`
reads `None` as "score every new offer". The per-run cap in the Search tab — the only
spend control in the product — applies to ad-hoc runs and is unreachable from a
scheduled one. There is no cap column on `SavedSearch`, so the UI cannot set one.

Measured: one fire of a saved search on "AI Engineer" discovered 91 offers, 76 of them
new, and scored all 76 uncapped. At `scoring.yaml → estimate.cost_per_offer_usd` of
~1.1¢ that is ~$0.84 for a single run. Nightly, that one search is ~$25/month against
a design estimate of $2–12/month total.

Needs a `max_offers` column on `SavedSearch`, a field in the saved-search UI, and
`run_saved_search` passing it through. Consider a sensible default rather than `None`,
so a search saved before the column exists cannot spend without limit.

## The cron path and the "run now" path are different code

**Found:** 2026-08-04, same investigation.

`jobs.py` opens with "manual and scheduled runs travel one code path". They do not:

- **Run now** (`api/discovery.py::run_search`) → `create_run` + `enqueue_run` →
  `execute_run` → `discover_into_run`, guarded by `active_run_for_search` (409)
- **Cron** (`discovery/scheduler.py::run_saved_search_job`) → `run_saved_search` →
  `run_discovery` → `discover_into_run`, with no guard

They converge at `discover_into_run`, so results are recorded identically and the
scheduled path is verified working. But the cron path skips the active-run check, and
the divergence is where the missing spend cap comes from. Collapsing
`run_saved_search_job` onto `create_run` + `execute_run` would fix both at once and make
the docstring true.

## Queue source filter

Specced in the UI spec, never implemented. Status, min-fitness, sort and text search all
exist; filtering by source does not.

## Unverified

- **Adzuna** is enabled in `sources.yaml` but `AJE_ADZUNA_APP_ID` / `AJE_ADZUNA_APP_KEY`
  are absent, so `registry.py` skips it with a warning. It is the only official-API
  source, which the design doc prefers over scrapers on legal grounds. Free credentials
  at developer.adzuna.com.

## Deliberately out of scope so far

Cancelling an in-flight run, re-running a historical run, pruning old run data.
