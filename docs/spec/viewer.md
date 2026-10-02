# Viewer

## Gestures

| Action | Result |
|---|---|
| Swipe up | Next post, always at depth 1 — exactly one, however hard the flick. |
| Swipe right | Deeper into this post. |
| Swipe left | Back out. **Required before swipe up works** — depth locks the vertical axis. |
| Revisit a post | Starts at depth 1. Depth is not remembered. |
| Back button | Closes an open sheet, then returns to the glance, then leaves the app. |
| ↑ ↓ / Space / j k | Previous / next post — **from any depth**. |
| ← → / h l | Out / deeper. `c` opens comments, `g` the glossary, Escape closes. |

Keyboard is not a second-class path: mandatory scroll-snap defeats native arrow scrolling (the
small increment is snapped straight back, so the key looks ignored), so keys move whole cards, and
one wheel gesture moves one card with a cooldown against trackpad momentum. The depth lock does
**not** apply to keys — it exists to stop ambiguous diagonal thumb swipes, which a keypress cannot be.

Depth must be visually obvious, since the vertical gesture is dead there — the hint says so, and
says it differently on a pointer device, where the axis is never locked.

## Comments and glossary

Comments and glossary (each with a count) and share, bottom-right where a thumb rests. Nothing
to explain. A header carries the name, the edition date (opens the calendar), the position in the
day (`3/24` — where you are, not what is unread) and the depth dots.

**Comments** — bottom sheet, reel-style; a swipe down closes it, as it does the glossary. Top-level only, HN's own order, replies dropped (no threading
UI). Verbatim text, plus a generated line that **names the camps rather than averaging them**. Needs an
empty state: high score does not imply a thread (measured: one post at 587 points had 3 comments).

**Glossary** — per-card terms, not a global dictionary. Accumulates across days and is reused, so it
gets cheaper and better over time. Indexes jargon from **comments as well as the article** — commenters
assume you are a peer, which is where most beginner confusion lives. Each term links to a Google
search for it: the gloss is one sentence, and the link is the way to more.

**Share** — a link that opens on the card in the main feed, `/?date=…&post=<id>` (`&lang=ko` when read in
Korean; a saved language still wins); the address then goes back to `/`. Chat crawlers run no JS, so `functions/index.js` fills that link's preview tags from
the card. Share sheet on a phone, clipboard elsewhere. Previews: `/` in English, `/ko/` in Korean.

## Session model

- An edition is dated by its **UTC run date**. The job runs every 6h; each run puts its newly
  qualifying posts in front of that day's file, best first, never replacing it.
- Opens at the top, latest run first; the last card viewed is **offered, not forced** ("Continue from <day>"), gone after three posts.
- **No caught-up card.** Meeting a card you already read is the signal. Older editions load below
  today, one at a time, each behind its own date divider; nothing older is ever counted as unread.
- **One feed**: the calendar jumps to a day in it, newer days above. **No backlog**: away a week → today.
- No accounts, unread counts, streaks or notifications. Cron failure → keep serving yesterday.
