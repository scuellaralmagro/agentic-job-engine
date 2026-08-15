# TODO

## Agreed queue (2026-08-04)

In order. Work mode is done; the rest are next.

1. ~~Work mode detection + search selection~~ — done
2. ~~Scoring prompt cache reorder~~ — **tried, measured, reverted.** Do not
   re-attempt without first re-checking the finding below.

   The premise of the item turned out to be wrong: **this provider does not do
   prefix caching.** The prompt was reordered to system → whole profile → offer,
   giving a 1302-token prefix byte-identical across all 248 stored offers. Verified
   live: a byte-identical repeat cached 2690/2693 tokens, but two offers sharing
   that prefix cached 0, even 90s apart. Scoring sends a different offer every
   call, so an exact whole-prompt match never happens and nothing cached. See
   "Prompt caching is not actually on" below.

   Reverted in favour of the original offer-first prompt, which restores the
   prefilter's per-offer profile-item selection. That selection had to be dropped
   to make the prefix work — system + skills/languages/education is only 615
   tokens, under the 1024 minimum, so the experience items had to be inside the
   prefix — and it is the one thing the reorder actually cost. It was inert at 3
   profile items against `top_k: 8`, but it stops being inert the moment the
   profile grows past `top_k`, and it buys nothing to keep a prompt shaped for a
   cache that does not exist.

   **If prefix caching is ever switched on, this becomes live again** — and the
   tradeoff is real then: a stable prefix and per-offer item selection cannot both
   hold. Select per-profile, not per-offer.
3. ~~Scheduled-run spend cap~~ — done 2026-08-15. Promoted ahead of salary because
   it was a measured ~$25/month leak while item 2 turned out to be worth $0. See
   "Scheduled runs have no spend cap" below for what it closed.
4. ~~Salary extraction + filter~~ — **dropped 2026-08-15, the premise was wrong.**
   See "Salary is not in the data" below before reconsidering.
5. ~~Fix cross-source dedup~~ — done 2026-08-15. See "Cross-source dedup" below;
   the payoff was queue quality, not the spend this item claimed.
6. **Application tracking** ← **next.** The queue stops at `accepted`; there is no applied
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
scoring never produces — it sends a different offer every call. The reorder was
therefore worth $0 and has been reverted (item 2 above).

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

## Study switching to OpenRouter

**Raised:** 2026-08-15. Study first, decide after — this is a spike, not a commitment.

Motivated by the caching finding above: the per-task model choice in `models.yaml` is
currently pinned to one provider, so "this provider does not do prefix caching" is
something we can only work around, not shop around. OpenRouter would make the provider a
config value per task rather than a fixed assumption.

Structurally cheap. `llm/registry.py` already dispatches on `spec.provider` through
`register_chat_provider`, and OpenRouter is OpenAI-compatible, so the whole adapter is
roughly `_openrouter_chat` = `ChatOpenAI(base_url=..., api_key=...)` in `providers.py`,
one `AJE_OPENROUTER_API_KEY` in `config.py`, and `provider: openrouter` per task in
`models.yaml`. No call site changes.

What the study has to answer before any of that is worth doing:

- **Structured output.** Scoring, extraction and discovery all rely on
  `.with_structured_output(...)`. Support varies by underlying model and OpenRouter's
  normalization of it is uneven. This is the one that can sink the idea — check it first,
  against the actual `RubricResult` schema, not a toy one.
- **Embeddings.** Verify whether OpenRouter serves them at all. If not,
  `text-embedding-3-small` stays on OpenAI direct and the switch is partial — which is
  fine (the registry already allows per-task providers) but should be a deliberate
  choice, not a surprise.
- **Caching.** Which models reachable through it actually do prefix caching, and whether
  the discount survives the hop. If some do, item 2 above comes back to life — and the
  reverted commit `452251b` is the shape to restore.
- **Cost and latency.** OpenRouter takes a margin and adds a hop. Compare against the
  measured ~1.1¢/rubric call and the current latency, and account for the extra failure
  mode of a third party between us and the model.
- **Usage metadata.** The cost model depends on reading `usage_metadata` back. Confirm
  token accounting survives the proxy, or the spend numbers quietly become fiction.

Re-run the caching A/B (see above) against any candidate before believing a claim on its
pricing page.

## ~~Scheduled runs have no spend cap~~ — fixed 2026-08-15

**Found:** 2026-08-04. **Fixed:** 2026-08-15, together with the path divergence below.

`SavedSearch.max_offers` now caps scoring on every path. NULL means deliberately
uncapped; rows predating the column were backfilled to 25. The measurement that
motivated it: one fire of "AI Engineer" discovered 91 offers, 76 new, and scored all 76
uncapped — ~$0.84 for a single run, ~$25/month nightly against a $2–12/month design
estimate for the whole product.

**Two uncapped paths, not one.** The cron path was the one recorded here. The second was
found while designing the fix: `POST /searches/{id}/run` called `enqueue_run(run.id)`
with no cap argument, so "Run now" on a saved search had always been uncapped too.

The paths no longer diverge. `jobs.py::start_run_for_search` applies the concurrency
guard, creates the run and enqueues it with the cap; the API and cron differ only in
whether a collision is a 409 or a logged skip, so `jobs.py`'s "manual and scheduled runs
travel one code path" docstring is finally true. `run_saved_search` is deleted and
`run_discovery` builds its run through `create_run`, leaving one constructor. Adopting
the guard on the cron path also stops a nightly run slower than its own interval from
overlapping itself and double-spending.

Two traps worth remembering:

- **No `default=` on the column.** SQLAlchemy applies a column default whenever the
  value is None at INSERT and cannot tell "explicitly None" from "unset", so a default
  there swallows an explicit NULL and makes "uncapped" unexpressible. The 25 lives on
  `SavedSearchIn`, the only layer where omitted and null differ.
- **The dialog always sends the field**, so the API's omitted-field default never fires
  from the UI. The dialog pre-fills 25 itself.

## Salary is not in the data

**Found:** 2026-08-15, measuring before implementing the queued salary item. **Dropped.**

The item said "JobSpy returns min/max salary and `_to_raw_offer` discards it, exactly as
it did `is_remote`". The discarding was real; the returning is not. Live scrapes:

| source | postings | with salary |
|---|---|---|
| Indeed ES — "AI Engineer" | 40 | 0 |
| Indeed ES — "Software Engineer" | 30 | 0 |
| Indeed ES — "Data Engineer" | 30 | 0 |
| LinkedIn Madrid | 30 | 0 |

Structural, not bad luck: JobSpy only runs description-based salary extraction when
`country_indeed == USA` (`jobspy/__init__.py:169`). Outside the US you get board-supplied
compensation only, and Indeed ES essentially never has it. Building the item as written
gives a filter over a permanently empty column.

**If it is ever revisited, the data is at Tecnoempleo, not JobSpy.** Its listing pages
publish explicit ranges (`30.000€ - 33.000€ b/a`) and `tecnoempleo.py::_to_raw_offer`
never parses them — and Tecnoempleo is 115 of the 248 stored offers. That is the version
worth building. The JobSpy mapping is three lines and can ride along, but it is not the
feature.

## Seniority filter — feasible, but not where it looks

**Assessed:** 2026-08-15, alongside the salary measurement. Not built.

Three things a future attempt should not have to rediscover:

- **`Offer.seniority` already exists and is already populated** — by the scoring LLM via
  `enrich_offer`, from `OfferRequirements.seniority`. It is free prose and unfilterable:
  122 of 248 offers have a value and nearly every value is unique, e.g. *"Senior Software
  Engineer; explicitly requires 5+ years of Python experience and large-scale scraping
  projects, plus technical leadership/innovation in scraping."*
- **LinkedIn's `job_level` is a clean categorical** (`entry level`, `associate`,
  `mid-senior level`, `director`, `executive`), confirmed populating 10/10 — **but only
  with `linkedin_fetch_description=True`**, which `jobspy_source.py` does not pass.
  Without it the field is an empty string and descriptions come back empty too. It costs
  one HTTP fetch per job. Note LinkedIn currently contributes **0** stored offers — all
  248 are `jobspy:indeed` and `tecnoempleo` — plausibly because all four configured sites
  share one `max_results: 50` budget and LinkedIn is truncated out. Fix that first.
- **The cheapest path is already running.** The rubric call extracts
  `requirements.seniority` today and is already paid for. Constraining that field to an
  enum instead of prose makes it filterable at zero extra LLM cost.

The layering matters: work mode filters *searches* because the source supplies it before
scoring. Seniority from the rubric is only known *after* paying to score, so it filters
the **Queue**, not discovery. Only the LinkedIn route could filter searches.

## Cross-source dedup — fixed 2026-08-15

**The item's justification was wrong and is worth recording.** It claimed normalizing
location "cuts duplicate spend". Measured across all 248 stored offers before building:

| | |
|---|---|
| title+company groups with more than one offer | 7 |
| …spanning more than one source | **2** |
| …within a single source | 5 |
| offers scored twice for the same job | 6 |
| wasted spend, whole project history | **$0.066** |

Seven cents. The real payoff is that the same job stops appearing twice in the review
queue. Fixed anyway — it is cheap and correct — but do not cite it as a cost measure.

**Five of the seven groups were not duplicates at all.** They are real openings in
different cities under one title and company (MAP advertises the same consultant role in
Madrid, Málaga and Barcelona). The current hash kept them apart *because* it included
location, so the obvious fix — drop location from the hash — would have silently deleted
real jobs. `canonical_location` normalizes instead: Indeed's `City, REGION, COUNTRY` and
Tecnoempleo's bare `City` reduce to one key, and every spelling of remote collapses to
one token, but different cities stay different.
`test_hash_keeps_different_cities_apart` is the guard.

**The migration was the hard part**, and two things about it were not in the design:

- `content_hash` is unique, so both rows of a collided pair cannot hold the new hash. The
  loser keeps what it had and becomes an inert historical row; nothing is deleted.
- "Loser keeps its old hash" breaks when the loser's old hash *is* the contested value,
  which happens whenever the Tecnoempleo row already spelled the location canonically.
  Win order is therefore: scored row first, then a row already holding its own new hash,
  then lowest id. Getting this backwards would have pointed the canonical hash at the
  *unscored* row, so every re-find would pay to score a job that was already scored — the
  fix would have cost money instead of saving it.

Migration is forward-only: `downgrade` cannot restore the previous hash values.

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
