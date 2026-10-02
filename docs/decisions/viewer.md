# Decisions — Viewer

## 2026-09-23 — Viewer JS split into classic scripts in `js/`, not ES modules

**Why:** the user prefers a file per concern. Classic scripts loaded in order share one global scope, so `app.js` moved verbatim into six files: checked line for line, and headless Chromium gave identical screenshots and identical state after keys, swipes and sheets.
**Rejected:** ES modules (explicit imports, but nine shared variables such as `post`, `depth` and `date` are reassigned across sections and an importer cannot assign an import, so every use would move into a state object: a rewrite, not a move); one `app.js` (the user's preference).

## 2026-09-23 — Back uses one history entry, pushed only while there is something to back out of

**Why:** on a home screen the app had no history, so Android's back closed it even from an open sheet. While a sheet is open or depth > 0 one entry sits on top: back closes the sheet, then returns to the glance, then leaves. Closing from inside the app takes the entry back off, so no back press is ever a dead one.
**Rejected:** a permanent entry (back at the glance would need two presses to leave); an entry per level (a sheet over depth would need unwinding that the one entry already gives, as it is re-pushed while depth > 0).

## 2026-09-26 — Vertical touch is paged in JS, one post per swipe

**Why:** `scroll-snap-stop: always` cut the browser's glide off at the next post, which read on a phone as the app cancelling the scroll; without it a hard flick skipped posts. No CSS sets glide friction, so the feed follows the finger and glides one post on release. Depth swipes, wheel and keys stay native.
**Rejected:** snap-stop on every post (the cut-off); no snap-stop (skips posts); snap-stop on the post two away (the same cut-off, later).

## 2026-09-29 — Newest first, no resume: the feed opens at the top in reverse processing order

**Why:** the user's call. Each day file is in processing order and the viewer reverses it, so the whole feed, days included, reads latest run first; you scroll down until you meet what you read before. An index-based resume would drift as runs add cards on top. Only a language switch keeps its place, for that one reload (`sessionStorage`).
**Rejected:** resume by card id (the top is where the new cards are, so resume would skip past them); reordering the day files in the generator (old days would keep the old order).

## 2026-09-29 — No caught-up card: a card you already read is the stop signal

**Why:** the user's call. With the feed newest first, the card sat under today's oldest post, usually one already read, so it said nothing; a plain date divider now separates days.
**Rejected:** moving the card above the first already-seen card (needs a seen-id in `localStorage` for a signal the feed already gives).

## 2026-09-29 — Each run goes in front of the day file; the viewer shows files as they are

**Why:** the user's call, superseding the viewer reversal from earlier today: reversing the whole file put each run worst first. Prepending keeps runs newest first and each run best first.
**Rejected:** reversing in the viewer (each run worst first); a file per run (index, calendar, Korean pass and glossary all assume one file per day).

## 2026-09-30 — Continue is offered, not forced: the feed still opens at the top

**Why:** the user found that without it, a forgotten date means scrolling through everything. Opening at the top still shows the new runs first; a pill offers the last card viewed (`localStorage`, by card id, so new runs on top cannot shift it).
**Rejected:** opening on the saved card (hides the new runs above it); a saved index (shifts as runs are prepended).

## 2026-09-30 — Link previews per language: `/` is English, `/ko/` is a forwarding page with the Korean one

**Why:** a crawler runs no JS and sends no language, so one URL gets one preview. The user wanted an English and a Korean image; `/ko/` carries the Korean tags, sets the language to Korean and forwards to `/`.
**Rejected:** one bilingual image (the user wanted one per language); a copy of the whole app under `/ko/` (duplicate markup for a preview).

## 2026-09-30 — Calendar is a month grid

**Why:** the list of date chips grew by one a day. A month grid stays one screen; only days with an edition are links, and the arrows skip months with none. Scrolling already steps back a day at a time, so the calendar is for jumps.
**Rejected:** previous/next-day buttons (what scrolling already does); a native date input (it cannot mark which days have editions).

## 2026-09-30 — The HN score shown is the score when the card was generated

**Why:** the user wanted the score beside the posted date. The card stores `points` from the HN item at generation; cards from before carry none and show none.
**Rejected:** a live score (a fetch per card for every reader, against a static site with no server).

## 2026-09-30 — Continue survives switching apps: save on hide, reload on return only if a run landed

**Why:** a phone keeps the page alive across an app switch, so no load ran to offer continue and the feed stayed old. Coming back reloads only when today's top card changed; otherwise the page is already where the reader left it.
**Rejected:** reloading on every return (loses the place after reading an article); a time threshold (arbitrary, and still reloads when nothing is new).

## 2026-09-30 — A Ko-fi link on the date card; no ads yet

**Why:** the date card is the one card with no story on it, so a tip link there interrupts nothing. Ads wait on traffic (4 sampled page loads in September); the trigger is in `DIRECTION.md`.
**Rejected:** ads now (cents at this traffic, cookies and a consent banner for AdSense); a tip link between posts or in the header.

## 2026-09-30 — Share links open the card; one Pages Function fills their preview

**Why:** the share button sends `/?date=…&post=<id>[&lang=ko]`, which opens that card. Chat crawlers run no JS, so `functions/index.js` rewrites the preview tags for that link from the day's JSON; every other request passes through.
**Rejected:** a static page per card (~70 files a day, the user's call); no per-story preview (a shared story would look like the app); a page per day (a preview of the day, not the story).

## 2026-09-30 — One feed: a calendar pick jumps within it, never opens a day on its own

**Why:** the user's call: scrolling up from a picked day should show the next day's last post, as if scrolled there from the top. The pick loads down to that day and lands on its first post; the card being read is offered as Continue for the way back. Old `?date=` links do the same.
**Rejected:** a picked day as its own feed (nothing newer above it, and it needed its own paths for Continue and the new-run check); loading upward on demand (more code; a `ponytail:` in `jumpTo` marks when it pays).
