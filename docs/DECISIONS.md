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

## 2026-09-23 — Gemini 3.8 Flash is paid, not free tier

**Why:** the code bills it (`PRICE_IN` $0.75 / `PRICE_OUT` $3.75 per 1M) and a measured 35-card run cost $0.455, ~$0.31/day at ~24 posts. Supersedes the free-tier and "$0 at any user count" claims of the 2026-09-21 model entry; the model choice itself stands. Cost still does not move with readers.
**Rejected:** —; this corrects a premise, not a choice.

## 2026-09-23 — Host is Cloudflare Pages, not GitHub Pages

**Why:** `hn.hyoseo.dev` is already in Cloudflare. Supersedes the host in the 2026-09-21 stack entry; Actions still runs the cron, and its push triggers the deploy.
**Rejected:** GitHub Pages (a second place to manage the domain).

## 2026-09-23 — Generate every 6h, not once at 00:00 UTC

**Why:** dedup generates each post once, so cost is unchanged and a run with nothing new is one free query; a failed run costs 6h of staleness, not 24. The 200-point bar gates age: of 158 qualifying stories in a week, one was under 6h old.
**Rejected:** once daily (a failure means a stale day).

## 2026-09-23 — Six doc files: PRODUCT.md and DESIGN.md join for the design skill

**Why:** the impeccable design skill reads product truth and the visual system from these two files at the repo root; folding them into `SPEC.md` would mean the tool never finds them. Chosen by the user. Supersedes the four-file rule.
**Rejected:** folding into `SPEC.md` (tool can't read it there); no design doc (the visual system would live only in CSS, with no record of intent).

## 2026-09-23 — GPT-6 Luna at high effort replaces Gemini 3.8 Flash

**Why:** measured on the same 9 posts and prompt: Luna kept its detail tier on 8 of 9 once the `&#x2F;` decoding bug was fixed (Flash 5 of 5 before Google's 503 stopped it), at $0.0024 a card against Flash's ~$0.012, which doubles on 2027-01-01. High over medium: it kept the prompt's format (camps 9/9 vs 6/9) for ~$0.80/mo more. Chosen by the user after reading the cards side by side. Supersedes the Gemini model entries.
**Rejected:** medium (format drift); xhigh (60-100+ s a post, one call past the 120 s timeout); Sol ($2/$10, headroom the quote check makes unnecessary); Gemini kept as a fallback (unused code; git history has it).

## 2026-09-23 — Each day file carries its own glosses; readers never fetch glossary.json

**Why:** the viewer downloaded every gloss ever written on every visit, and the file changes with nearly every edition: 22 KB now, ~2 MB estimated after a year at ~2.2 new terms per card. A day's slice keeps a visit at index + one day however many months pile up. `glossary.json` stays as the generator's memory, so known terms keep their gloss. Tradeoff: a rebuilt gloss reaches old days only if their slices are rewritten too.
**Rejected:** a database (needs a server for what is still one day read whole); fetching glossary.json only when the sheet opens (still the whole growing file); sharding it by letter (more files, same total).

## 2026-09-23 — Threshold 150, down from 200

**Why:** chosen by the user once Luna made a card ~$0.0024. Measured over 14 settled days: a median of 32 stories/day clear 150 (22-43) against 24 at 200 (16-32), ~$2.30/mo. Supersedes the number in the 2026-09-21 threshold entry; no age delay and no cap still hold. The query now fetches up to 1000 hits: at 150 the 3-day window held 84, and a busy stretch passes the old 100, which silently dropped the oldest qualifiers.
**Rejected:** staying at 200 (set for reading load: ~24 cards fits a 2-3 minute swipe; the user chose coverage); 100 (~45/day, where a cap used to do the selecting).

## 2026-09-23 — Viewer JS split into classic scripts in `js/`, not ES modules

**Why:** the user prefers a file per concern. Classic scripts loaded in order share one global scope, so `app.js` moved verbatim into six files: checked line for line, and headless Chromium gave identical screenshots and identical state after keys, swipes and sheets.
**Rejected:** ES modules (explicit imports, but nine shared variables such as `post`, `depth` and `date` are reassigned across sections and an importer cannot assign an import, so every use would move into a state object: a rewrite, not a move); one `app.js` (the user's preference).

## 2026-09-23 — Translations are a separate pass over the finished English, one overlay file per language per day

**Why:** the English detail is what was checked against quotes, and a failed pass costs no edition, only that card's Korean. An overlay keyed by card id leaves the English file, and every English reader's download, unchanged; a second language is another file. Every number and name must survive, per card, else English ships: a changed figure is the same failure as an invented one.
**Rejected:** Korean written in the main call (~free, but loses the English); translated fields inline in the day file (every reader downloads every language); Papago and other MT (they follow the English sentence, and the register is the product); Gemini Flash-Lite (wrote 오픈아이 for OpenAI, dropped Apache and Snap).

## 2026-09-23 — Korean register: a tech headline's; comments keep their commenter's voice

**Why:** the user's call, after reading Luna's Korean. The app's own lines end in nouns (~중, ~함) with a headline's compact Sino-Korean (환승시, 대기중, 취약점), and the tech words Korean developers write in English stay English (tool, glossary terms). Comments are people talking: turned into headlines they lose the sarcasm that is much of why the sheet gets opened. Whole-line prompt examples come from output the user approved.
**Rejected:** "-대" hearsay endings (the earlier "풀어버렸대" examples); plain native phrasing (갈아타면, 구멍: long and loose as a headline); noun endings for comments.

## 2026-09-23 — Names stay as the source writes them, except Korean companies

**Why:** the user's call. The reader meets these names in Latin letters in the title, the source line, the comments and a search, and exact spelling makes the name check mechanical. Korean companies read in Hangul (Samsung → 삼성) from a map in code. People's names are never transliterated: a romanized Korean name has several Hangul spellings, and a guessed one is a wrong fact.
**Rejected:** transliterating every name (구글, 오픈AI).

## 2026-09-23 — The Korean view translates comments too

**Why:** the user's call: a Korean reader wants the reactions, not only the camps line. Comments are ~1,550 characters a card against ~550 the model writes, so the pass's output roughly triples. The sheet says it is a translation and keeps the link to the originals on HN.
**Rejected:** English comments under a Korean camps line (cheaper, and verbatim).

## 2026-09-23 — Language: the browser's by default, a toggle to override, kept in `localStorage`

**Why:** many Korean developers run their phones in English, so the browser language alone would hide Korean from them. The toggle sits beside the date button; switching reloads, and resume restores the position. `localStorage` holds the resume position and the language.
**Rejected:** browser language only.

## 2026-09-23 — The Korean pass runs Luna at medium effort

**Why:** measured on the same 10 cards with the revised prompt: the user preferred medium's glance on 9 of 10, at $0.0013 a card and ~21 s against high's $0.0025 and ~36 s (~$1.25/mo against ~$2.40 at 32 cards a day). High also added a name its English did not mention. The effort level never fixed translationese: low, medium and high all wrote it under the first prompt, and the prompt's rewrite fixed it.
**Rejected:** high (twice the cost, and the user preferred medium's lines); low (list-like detail, and it dropped a "1:1" that failed the check, at $0.0006 a card).
