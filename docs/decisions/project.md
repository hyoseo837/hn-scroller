# Decisions — Project: docs, hosting, cost

## 2026-09-21 — Docs are three files: CLAUDE.md, SPEC.md, DECISIONS.md

**Why:** agent context is the scarce resource; a docs tree goes stale and poisons every session that reads it.
**Rejected:** ADR-per-file directory (too much ceremony for one dev), README-as-spec (mixes public pitch with working notes).

## 2026-09-21 — v1 stack: vanilla JS viewer, one Node script, GitHub Pages + Actions

**Why:** every constraint already settled (static-hostable, one JSON/day, no DB, no auth) points here. App state is three integers over a static array, and `scroll-snap-type` does the 2D grid in CSS — a framework would add a build step and a render model to manage that. Actions+Pages makes the cron and the host one free thing, with version history on every day's JSON for free.
**Rejected for now:** React or any framework (nothing here it makes easier; the JSON contract means swapping the viewer is one file); Gemini SDK and a Readability dependency (both are ~30 lines of stdlib); service worker. **Revisit when:** the viewer outgrows vanilla state handling, extraction quality forces a real parser, or a second data consumer appears. Stack is expected to change in later versions — it is the least load-bearing decision here, since the day-file shape is the actual contract.

## 2026-09-21 — A full generation run is never a test; ask before spending

**Why:** across one session ~$1.20 was spent on generation, of which ~$0.75 bought nothing — two full batches run to verify code changes, one killed mid-run and one superseded by a prompt rewrite an hour later. `--sample` costs ~1/40th as much and answers the same question: does the schema parse, does the prompt produce the register we want. The cost is small per run, which is exactly why it erodes without a rule.
**Rejected:** relying on care alone (a promise does not survive a context reset, which is why this is in `CLAUDE.md` too); a `--yes` confirmation flag on full runs (the cron job would carry it permanently, so it would guard nothing where it matters). **Ladder:** `--check` free, `--dry` free, `--sample N` cents, full run only on an explicit request for fresh content.

## 2026-09-22 — A fourth doc, DIRECTION.md, for work that has no code yet

**Why:** the three-file rule had nowhere to put "we should do this eventually". `ponytail:` comments cover deferrals that live next to code, but an idea with no code — better image sourcing, story threading, discussion as a selection signal — had only this conversation to live in, and a conversation is not a durable place. Requested by the user, who wrote the three-file rule in the first place.
**Guarded against becoming a TODO dump:** every entry needs a **trigger**, the condition that would actually start the work; an entry with no trigger is a wish and gets deleted. Capped at 120 lines, prune freely, and an untouched entry is treated as evidence the idea died rather than as a debt. Anything already deferred in code stays a `ponytail:` comment, so the two do not overlap.

## 2026-09-22 — DIRECTION cap raised 120 -> 150

**Why:** adding the bilingual entry took it to 148. Compressing every entry that had slack got it to 130, and what remained was measured findings — cost tables, the Lite transliteration failure, the 28% extraction rate — not prose. The cap existed to stop a wish-list dump; the trigger rule does that job, and `DIRECTION.md` is never auto-loaded, so its context cost is zero until someone opens it. Deleting a live, trigger-gated entry to satisfy a number picked out of the air is the wrong trade.
**Rejected:** cutting an entry instead (none were dead — every one still had a real trigger); leaving it over cap silently, which is how caps stop meaning anything. Compression came first and got 18 lines; the raise covers what compression could not.

## 2026-09-23 — Host is Cloudflare Pages, not GitHub Pages

**Why:** `hn.hyoseo.dev` is already in Cloudflare. Supersedes the host in the 2026-09-21 stack entry; Actions still runs the cron, and its push triggers the deploy.
**Rejected:** GitHub Pages (a second place to manage the domain).

## 2026-09-23 — Six doc files: PRODUCT.md and DESIGN.md join for the design skill

**Why:** the impeccable design skill reads product truth and the visual system from these two files at the repo root; folding them into `SPEC.md` would mean the tool never finds them. Chosen by the user. Supersedes the four-file rule.
**Rejected:** folding into `SPEC.md` (tool can't read it there); no design doc (the visual system would live only in CSS, with no record of intent).

## 2026-09-26 — Cloudflare Web Analytics, beacon added to `index.html` by hand

**Why:** the user turned on Web Analytics for the Pages project, but no deployment ever carried the injected beacon — not production, not a preview, not after adding `</body>`. The hand-added snippet was checked on a preview and live: one tag, and `cdn-cgi/rum` answers 204. Cloudflare documents it as cookieless (not measured here); its token is public by design.
**Rejected:** relying on Pages' automatic injection (never appeared); closing `</body>` as the fix (tested on a preview, still no beacon).

## 2026-10-01 — No global 200-line file cap

**Why:** the user's call. `DECISIONS.md` grows forever by design and had reached 200, so the global cap forbade logging the next decision. The per-doc caps in `CLAUDE.md`'s table still hold.
**Rejected:** splitting `DECISIONS.md` (a seventh doc file); pruning past entries (append-only).

## 2026-10-01 — Docs split by area; no line caps but CLAUDE.md's

**Why:** the user's call. The caps were there to keep each doc short; one file per area does that, and lets an agent read only its own area's spec and decisions. Moved verbatim, checked block by block. Supersedes the six-file rule, the no-`docs/`-tree anti-rule and the per-doc caps; `CLAUDE.md` keeps 100 lines, being loaded every session.
**Rejected:** cutting to fit the caps (deletes measured findings); one `DECISIONS.md` read by grep (an area's decisions cannot be read whole).
