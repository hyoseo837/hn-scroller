# Decisions

## 2026-09-21 — Docs are three files: CLAUDE.md, SPEC.md, DECISIONS.md

**Why:** agent context is the scarce resource; a docs tree goes stale and poisons every session that reads it.
**Rejected:** ADR-per-file directory (too much ceremony for one dev), README-as-spec (mixes public pitch with working notes).

## 2026-09-21 — v1 sources ~25-35 posts/day via a points threshold, not the front page

**Why:** ~990 stories/day are submitted, ~33 cleared 100 points (measured 2026-09-21); the threshold does the filtering for free and a floating count honestly reflects how busy the day was. Selection costs nothing, so a 3-day query window + dedup by item ID absorbs slow burners and mod resurrections.
**Rejected for now:** fixed N per day (scrapes the barrel on quiet days); front-page snapshot as the source (misses midday peaks, and includes fresh posts the community hasn't judged); beginner-relevance ranking beyond raw points. Threshold (100) and volume are the expansion knobs — revisit once a week of real data exists.

## 2026-09-21 — Card facts come only from the source; definitions come only from the glossary

**Why:** the target user cannot tell a wrong number from a right one — that's why they're here — so every claim on a card must be checkable against the linked source. Background knowledge (what x.ai is) is unavoidable for de-jargoning but is quarantined in the reusable glossary, where one bad entry is fixable in one place instead of smeared across a day's cards.
**Rejected:** enrichment from model recall inside cards (dates, versions, benchmark scores); inventing a depth tier when the source has no substance for one — fewer cards beats a padded one.

## 2026-09-21 — Gemini 3.8 Flash, free tier, for both development and production

**Why:** it beats Gemini 3.1 Pro Preview on 8 of 9 benchmarks (AA Intelligence 41.2 vs 30.4, Agentic 41.1 vs 10.3) — Pro is on a separate preview track, so the version numbers mislead. Free tier allows 1,000 req/day against our ~35, generation is once-daily and server-side, so cost stays $0 at any user count. Familiar API, and swapping providers is one function since the pipeline is text in / JSON out.
**Rejected:** 3.1 Pro (~$20/mo for worse benchmarks); a cheap-dev / paid-prod split (pointless once one model is both best and free, and tuning on a model you don't ship is a liability); Batch API and context caching (complexity for single-digit dollars). **Caveat:** one real-world test found Flash fluent-but-wrong where Pro was robust — hence the spot-check step in `SPEC.md`, not prompt-only trust.

## 2026-09-21 — v1 stack: vanilla JS viewer, one Node script, GitHub Pages + Actions

**Why:** every constraint already settled (static-hostable, one JSON/day, no DB, no auth) points here. App state is three integers over a static array, and `scroll-snap-type` does the 2D grid in CSS — a framework would add a build step and a render model to manage that. Actions+Pages makes the cron and the host one free thing, with version history on every day's JSON for free.
**Rejected for now:** React or any framework (nothing here it makes easier; the JSON contract means swapping the viewer is one file); Gemini SDK and a Readability dependency (both are ~30 lines of stdlib); service worker. **Revisit when:** the viewer outgrows vanilla state handling, extraction quality forces a real parser, or a second data consumer appears. Stack is expected to change in later versions — it is the least load-bearing decision here, since the day-file shape is the actual contract.

## 2026-09-21 — Generator is Python, and the prompt lives in prompt.md

Supersedes the Node choice in the stack entry above; everything else there still holds.

**Why:** prompt text is the file that gets edited most, so it sits outside the code as `prompt.md` and is read at runtime — no escaping, no redeploy to reword a sentence, and it diffs as prose. Python is stdlib-only here (`urllib`, `concurrent.futures`), so the zero-dependency property survives the switch.
**Rejected:** prompt as a constant in the script (harder to iterate on, and prompt churn would dominate the code diff); a `prompts/` directory (one prompt exists — make it a directory when there are two); the Gemini SDK, still a dependency for a dozen lines.
**Untested:** live article extraction. The dev sandbox reaches the HN APIs but blocks arbitrary domains, so `article_text` has never run against a real page — the parser is pinned by an HTML fixture in `--check` instead. Run `--dry` on a real network before trusting extraction quality.

## 2026-09-21 — Depth 2 requires verbatim source quotes, checked in code

**Why:** measured, not theorised. On the second live card the model invented "chat context caused hallucinated filler text to persist across later prompts" — absent from article and comments, and the one nearby comment said the opposite ("I can tell it's AI generated not from style, layout, or even hallucinations, but just the size"). The absolute rule was already in the prompt and did not hold. So the model now returns `support`: verbatim quotes, six words minimum, checked by normalised exact match; any miss drops `substance` and the card ships as 2 tiers. A fabricated claim has no real quote behind it, so it cannot pass.
**Rejected:** trusting the prompt (falsified above); checking only numbers (the fabrication contained none); rejecting the whole card (a shorter card is already specced as correct, and the headline was accurate); an LLM judge (a second model with the same weakness, at double the cost).
**Still unguarded:** `headline` and `camps` are prose with no mechanical check. Judge those by eye while tuning `prompt.md`.

## 2026-09-21 — A full generation run is never a test; ask before spending

**Why:** across one session ~$1.20 was spent on generation, of which ~$0.75 bought nothing — two full batches run to verify code changes, one killed mid-run and one superseded by a prompt rewrite an hour later. `--sample` costs ~1/40th as much and answers the same question: does the schema parse, does the prompt produce the register we want. The cost is small per run, which is exactly why it erodes without a rule.
**Rejected:** relying on care alone (a promise does not survive a context reset, which is why this is in `CLAUDE.md` too); a `--yes` confirmation flag on full runs (the cron job would carry it permanently, so it would guard nothing where it matters). **Ladder:** `--check` free, `--dry` free, `--sample N` cents, full run only on an explicit request for fresh content.

## 2026-09-21 — Threshold 200, no age delay: the bar is the maturity test

**Why:** at 100 points ~45 stories/day qualified against a cap of 35, so the cap silently did the selecting on 12 of 13 measured days and the "count floats with the day" property was false — every day looked identical. At 200 it is ~24/day (15-32), so the threshold filters, the count floats, the cap becomes a real safety net, and nothing above the bar ages out unseen. An 18-24h maturity delay was measured and proposed (comment growth: +4.6% at 6-12h, +0.9% at 12-18h, 0.0% past 24h) and then **rejected by the user on better reasoning**: a post at 200 points has proven itself whether that took six hours or two days, so the threshold already is the maturity test, and holding back a story that broke overnight is the worse failure for an awareness app. Measured on the live window: 11 of 35 selected were under 24h old, the best at 588 points — all of which a delay would have dropped.
**Rejected:** age delay (above); today-only windows (miss late risers entirely); allowing days to overlap so repeat readers scroll past (forces per-post read state, i.e. the unread-count model the spec refuses — the calendar already serves the reader who missed yesterday).

## 2026-09-22 — A fourth doc, DIRECTION.md, for work that has no code yet

**Why:** the three-file rule had nowhere to put "we should do this eventually". `ponytail:` comments cover deferrals that live next to code, but an idea with no code — better image sourcing, story threading, discussion as a selection signal — had only this conversation to live in, and a conversation is not a durable place. Requested by the user, who wrote the three-file rule in the first place.
**Guarded against becoming a TODO dump:** every entry needs a **trigger**, the condition that would actually start the work; an entry with no trigger is a wish and gets deleted. Capped at 120 lines, prune freely, and an untouched entry is treated as evidence the idea died rather than as a debt. Anything already deferred in code stays a `ponytail:` comment, so the two do not overlap.

## 2026-09-22 — DIRECTION cap raised 120 -> 150

**Why:** adding the bilingual entry took it to 148. Compressing every entry that had slack got it to 130, and what remained was measured findings — cost tables, the Lite transliteration failure, the 28% extraction rate — not prose. The cap existed to stop a wish-list dump; the trigger rule does that job, and `DIRECTION.md` is never auto-loaded, so its context cost is zero until someone opens it. Deleting a live, trigger-gated entry to satisfy a number picked out of the air is the wrong trade.
**Rejected:** cutting an entry instead (none were dead — every one still had a real trigger); leaving it over cap silently, which is how caps stop meaning anything. Compression came first and got 18 lines; the raise covers what compression could not.
