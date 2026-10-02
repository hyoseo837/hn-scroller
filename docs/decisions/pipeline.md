# Decisions — Pipeline

## 2026-09-21 — v1 sources ~25-35 posts/day via a points threshold, not the front page

**Why:** ~990 stories/day are submitted, ~33 cleared 100 points (measured 2026-09-21); the threshold does the filtering for free and a floating count honestly reflects how busy the day was. Selection costs nothing, so a 3-day query window + dedup by item ID absorbs slow burners and mod resurrections.
**Rejected for now:** fixed N per day (scrapes the barrel on quiet days); front-page snapshot as the source (misses midday peaks, and includes fresh posts the community hasn't judged); beginner-relevance ranking beyond raw points. Threshold (100) and volume are the expansion knobs — revisit once a week of real data exists.

## 2026-09-21 — Gemini 3.8 Flash, free tier, for both development and production

**Why:** it beats Gemini 3.1 Pro Preview on 8 of 9 benchmarks (AA Intelligence 41.2 vs 30.4, Agentic 41.1 vs 10.3) — Pro is on a separate preview track, so the version numbers mislead. Free tier allows 1,000 req/day against our ~35, generation is once-daily and server-side, so cost stays $0 at any user count. Familiar API, and swapping providers is one function since the pipeline is text in / JSON out.
**Rejected:** 3.1 Pro (~$20/mo for worse benchmarks); a cheap-dev / paid-prod split (pointless once one model is both best and free, and tuning on a model you don't ship is a liability); Batch API and context caching (complexity for single-digit dollars). **Caveat:** one real-world test found Flash fluent-but-wrong where Pro was robust — hence the spot-check step in `SPEC.md`, not prompt-only trust.

## 2026-09-21 — Generator is Python, and the prompt lives in prompt.md

Supersedes the Node choice in the stack entry above; everything else there still holds.

**Why:** prompt text is the file that gets edited most, so it sits outside the code as `prompt.md` and is read at runtime — no escaping, no redeploy to reword a sentence, and it diffs as prose. Python is stdlib-only here (`urllib`, `concurrent.futures`), so the zero-dependency property survives the switch.
**Rejected:** prompt as a constant in the script (harder to iterate on, and prompt churn would dominate the code diff); a `prompts/` directory (one prompt exists — make it a directory when there are two); the Gemini SDK, still a dependency for a dozen lines.
**Untested:** live article extraction. The dev sandbox reaches the HN APIs but blocks arbitrary domains, so `article_text` has never run against a real page — the parser is pinned by an HTML fixture in `--check` instead. Run `--dry` on a real network before trusting extraction quality.

## 2026-09-21 — Threshold 200, no age delay: the bar is the maturity test

**Why:** at 100 points ~45 stories/day qualified against a cap of 35, so the cap silently did the selecting on 12 of 13 measured days and the "count floats with the day" property was false — every day looked identical. At 200 it is ~24/day (15-32), so the threshold filters, the count floats, the cap becomes a real safety net, and nothing above the bar ages out unseen. An 18-24h maturity delay was measured and proposed (comment growth: +4.6% at 6-12h, +0.9% at 12-18h, 0.0% past 24h) and then **rejected by the user on better reasoning**: a post at 200 points has proven itself whether that took six hours or two days, so the threshold already is the maturity test, and holding back a story that broke overnight is the worse failure for an awareness app. Measured on the live window: 11 of 35 selected were under 24h old, the best at 588 points — all of which a delay would have dropped.
**Rejected:** age delay (above); today-only windows (miss late risers entirely); allowing days to overlap so repeat readers scroll past (forces per-post read state, i.e. the unread-count model the spec refuses — the calendar already serves the reader who missed yesterday).

## 2026-09-23 — Gemini 3.8 Flash is paid, not free tier

**Why:** the code bills it (`PRICE_IN` $0.75 / `PRICE_OUT` $3.75 per 1M) and a measured 35-card run cost $0.455, ~$0.31/day at ~24 posts. Supersedes the free-tier and "$0 at any user count" claims of the 2026-09-21 model entry; the model choice itself stands. Cost still does not move with readers.
**Rejected:** —; this corrects a premise, not a choice.

## 2026-09-23 — Generate every 6h, not once at 00:00 UTC

**Why:** dedup generates each post once, so cost is unchanged and a run with nothing new is one free query; a failed run costs 6h of staleness, not 24. The 200-point bar gates age: of 158 qualifying stories in a week, one was under 6h old.
**Rejected:** once daily (a failure means a stale day).

## 2026-09-23 — GPT-6 Luna at high effort replaces Gemini 3.8 Flash

**Why:** measured on the same 9 posts and prompt: Luna kept its detail tier on 8 of 9 once the `&#x2F;` decoding bug was fixed (Flash 5 of 5 before Google's 503 stopped it), at $0.0024 a card against Flash's ~$0.012, which doubles on 2027-01-01. High over medium: it kept the prompt's format (camps 9/9 vs 6/9) for ~$0.80/mo more. Chosen by the user after reading the cards side by side. Supersedes the Gemini model entries.
**Rejected:** medium (format drift); xhigh (60-100+ s a post, one call past the 120 s timeout); Sol ($2/$10, headroom the quote check makes unnecessary); Gemini kept as a fallback (unused code; git history has it).

## 2026-09-23 — Each day file carries its own glosses; readers never fetch glossary.json

**Why:** the viewer downloaded every gloss ever written on every visit, and the file changes with nearly every edition: 22 KB now, ~2 MB estimated after a year at ~2.2 new terms per card. A day's slice keeps a visit at index + one day however many months pile up. `glossary.json` stays as the generator's memory, so known terms keep their gloss. Tradeoff: a rebuilt gloss reaches old days only if their slices are rewritten too.
**Rejected:** a database (needs a server for what is still one day read whole); fetching glossary.json only when the sheet opens (still the whole growing file); sharding it by letter (more files, same total).

## 2026-09-23 — Threshold 150, down from 200

**Why:** chosen by the user once Luna made a card ~$0.0024. Measured over 14 settled days: a median of 32 stories/day clear 150 (22-43) against 24 at 200 (16-32), ~$2.30/mo. Supersedes the number in the 2026-09-21 threshold entry; no age delay and no cap still hold. The query now fetches up to 1000 hits: at 150 the 3-day window held 84, and a busy stretch passes the old 100, which silently dropped the oldest qualifiers.
**Rejected:** staying at 200 (set for reading load: ~24 cards fits a 2-3 minute swipe; the user chose coverage); 100 (~45/day, where a cap used to do the selecting).
