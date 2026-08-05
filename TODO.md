# TODO

## Agreed queue (2026-08-04)

In order. Work mode is done; the rest are next.

1. ~~Work mode detection + search selection~~ — done
2. ~~Scoring prompt cache reorder~~ — done, but **it does not pay off yet.** The
   prompt is now system → whole profile → offer, a 1302-token prefix that is
   byte-identical across all 248 stored offers. Verified live, and the premise of
   the whole item turned out to be wrong: **this provider does not do prefix
   caching.** A byte-identical repeat cached 2690/2693 tokens, but two offers
   sharing the 1302-token prefix cached 0, even 90s apart. Scoring sends a
   different offer every call, so nothing caches in practice. The usage payload
   carries `cache_creation` / `cache_write_tokens` — Anthropic-style *explicit*
   breakpoint accounting — so the missing piece is likely a cache breakpoint that
   `ChatOpenAI` never emits. See "Prompt caching is not actually on" below.

   The reorder is kept because it costs nothing (identical content, identical
   token count) and is the shape prefix caching needs. Note the reorder alone was
   never enough: system + skills/languages/education is only 615 tokens, under the
   1024 minimum, so the per-offer profile-item *selection* had to go too. It was
   inert anyway — 3 profile items against `top_k: 8` meant all 3 were always sent.
   **If the profile ever grows past `top_k` items, revisit:** reintroduce
   selection per-profile, never per-offer, or the prefix stops being stable.
3. **Salary extraction + filter** — JobSpy returns min/max salary and
   `_to_raw_offer` discards it, exactly as it did `is_remote`. Same shape as work
   mode, so it follows cheaply.
4. **Fix cross-source dedup** — `compute_offer_hash` uses the raw location, so the
   same job on Indeed ("Madrid, MD, ES") and Tecnoempleo ("Madrid") is stored and
   scored twice. Normalizing location into the hash cuts duplicate spend.
5. **Application tracking** — the queue stops at `accepted`; there is no applied
   date, response or interview state. The CV and cover letter already hang off the
   match, so this is where they belong.

## Prompt caching is not actually on

**Found:** 2026-08-05, verifying the cache reorder against the live API.

Measured, 14 real scoring calls:

| case | input | cached |
|---|---|---|
| byte-identical prompt, repeated | 2693 | 2690 (~100%) |
| two offers sharing a 1302-token prefix, back to back | ~2500 | 0 |
| same, 90s apart to rule out population lag | ~2400 | 0 |

So caching exists and is reported, but only on an exact whole-prompt match, which
scoring never produces — it sends a different offer every call. The reorder is
therefore correct but currently worth $0.

Worth trying, cheapest first:

- Pass OpenAI's `prompt_cache_key` through `models.yaml → params` (the registry
  already splats `params` into `ChatOpenAI`), and re-run the check.
- The usage payload's `cache_creation` / `cache_write_tokens` fields are
  Anthropic-shaped, so this may be a gateway wanting an explicit `cache_control`
  breakpoint on the profile block. `ChatOpenAI` will not emit one.
- Confirm with the provider whether `gpt-5.6-terra` does automatic prefix caching
  at all, and what its minimum prefix is.

Re-run `scratchpad/latency_check.py`-style A/B after any change — the check is two
calls and settles it in 90 seconds. Do not trust a token count as evidence of a
cache hit; read `usage_metadata.input_token_details.cache_read` back from the API.

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
