# Spec

A vertical-swipe feed that tells a beginner developer what happened in tech today, from Hacker News.

**Awareness tool, not a learning tool.** Open it without thinking, know what's going on, close it.
Depth is available but never required. See `DECISIONS.md` for why each choice was made.

## Audience

A beginner developer who wants to follow tech news, finds most HN posts hard to parse, and will not
research them one by one.

## Success / failure

| | |
|---|---|
| Works | User opens it cold, swipes 2-3 minutes, recognizes today's terms and roughly who is arguing about what. |
| Fails | User feels informed but retained nothing. Fluent summaries of things nobody understood. |

## Content model

One post = one **card stack**: the glance, then the detail. Two cards, or one when the source
supports no detail. There is no middle 'headline' rung — it restated the glance in longer words and
cost more to generate than it added (measured: removing it *raised* thinking tokens 27%, so the
reason to cut it was redundancy, never cost).

| Depth | Holds |
|---|---|
| 1 | **The glance.** One spoken sentence saying what the post is about, no jargon — the only layer most readers ever see. Not compressed: vague-but-short is worse than clear-but-longer. |
| 2 | The detail — the specifics (names, versions, figures) `simple` leaves out, shaped by post type: spec table (launch), method (research), argument (essay), the two camps (controversy). |

The source is **not** a card. It appears twice, on purpose: inline at the end of the detail tier,
where "read the whole thing" is the next thought a reader has, and as a 🔗 button beside the
comment button. The button is not redundant — a card whose substance failed verification has no
detail tier, and would otherwise offer no route to the article at all. Older day files still carry
a link tier; the viewer filters it out.

Two or three key words per text tier are marked `**like this**` and render as a highlight. The
viewer parses them by splitting and appending text nodes, never `innerHTML` — this text comes from
a model and sits beside raw comment text.

Rules:

1. **Facts come from the source. Definitions come from the glossary. Never mixed on one card.**
   The glance line is lowercase with no trailing full stop — it is the only line on the screen, so
   one stray capital is glaring.
2. Numbers, dates and versions only if they appear verbatim in the fetched source. No model recall.
   Spelling a number out is fine ("one hundred" -> 100); adding one is not. Where the source names
   something specifically (a "village fayre"), its word is used, not a near-synonym.
3. **The substance tier must show receipts.** The model returns verbatim source quotes backing its substance;
   the code checks each by exact match and drops the whole tier if any fails. Prompt instructions
   alone did not hold — a measured run invented a fluent technical claim with no source at all.
4. Never pad a depth tier. A 2-card post is correct when there is no substance for a third.
5. Show depth up front (dots) so a swipe right is never wasted.
6. Voice is casual and human — "someone made a digital brain of a fly to play Brood War", not
   "researchers have developed a neural simulation of Drosophila melanogaster". Register is part of
   the product; heavy prose breaks the lightness.

## Gestures

| Action | Result |
|---|---|
| Swipe up | Next post, always at depth 1. |
| Swipe right | Deeper into this post. |
| Swipe left | Back out. **Required before swipe up works** — depth locks the vertical axis. |
| Revisit a post | Starts at depth 1. Depth is not remembered. |
| ↑ ↓ / Space / j k | Previous / next post — **from any depth**. |
| ← → / h l | Out / deeper. `c` opens comments, `g` the glossary, Escape closes. |

Keyboard is not a second-class path: mandatory scroll-snap defeats native arrow scrolling (the
small increment is snapped straight back, so the key looks ignored), so keys move whole cards, and
one wheel gesture moves one card with a cooldown against trackpad momentum. The depth lock does
**not** apply to keys — it exists to stop ambiguous diagonal thumb swipes, which a keypress cannot be.

Depth must be visually obvious, since the vertical gesture is dead there — the hint says so, and
says it differently on a pointer device, where the axis is never locked.

## Comments and glossary

Two buttons per card, each with a count. Same grammar, nothing to explain.

**Comments** — bottom sheet, reel-style. Top-level only, HN's own order, replies dropped (no threading
UI). Verbatim text, plus a generated line that **names the camps rather than averaging them**. Needs an
empty state: high score does not imply a thread (measured: one post at 587 points had 3 comments).

**Glossary** — per-card terms, not a global dictionary. Accumulates across days and is reused, so it
gets cheaper and better over time. Indexes jargon from **comments as well as the article** — commenters
assume you are a peer, which is where most beginner confusion lives.

## Session model

- One batch per day, cut at **00:00 UTC** (captures the full US day; lands ~09:00 KST).
- Resume where you stopped **within today**. Finished already → the caught-up screen.
- The caught-up screen is a **boundary, not a dead end**: older editions load below it, one at a
  time, each behind its own date divider. Scrolling past the boundary is a deliberate choice, so
  this is not a backlog — nothing older is ever pushed at you or counted as unread.
- **Resume never points into an older edition.** It is capped at today's last slide, because a day
  having a bottom is what makes the app feel light.
- Calendar to browse past days. Pull, not push: no badge, nothing accumulates.
- **No backlog.** Away a week → you get today, not 200 cards.
- No accounts, no unread counts, no streaks, no notifications.
- Resume position is per-device (`localStorage`). Cron failure → keep serving yesterday.

## Pipeline

Daily job. Select is free; only generate costs money.

```
select    Algolia search_by_date, tags=story, points>=200, 3-day window
          → dedupe by HN item ID against everything published
fetch     article text (cap ~6k tokens) + top-level comments (Firebase)
generate  card stack + camps line + glossary terms, per post
publish   one JSON file for the day
```

- **Model: Gemini 3.8 Flash**, free tier (1,000 req/day against our ~35). Same model for prompt
  development and production, so the prompt is tuned on exactly what ships.
- **Quote verification is mechanical, not manual** (`verify_substance`). Flash is capable of
  fluent-but-wrong, which is the one failure this app cannot absorb. Headline and camps are still
  only prompt-governed — read those by eye when tuning.
- Generation is once-daily and server-side; users read a static file. **Cost is constant at any number
  of users** — nothing about growth moves this off the free tier.
- `https://hn.algolia.com/api/v1/search_by_date` — day-wide selection. URL-encode the `>` or it 400s.
- `https://hacker-news.firebaseio.com/v0/` — item details and comments.
- **If article extraction yields too little, build the card from title + comments only.** Measured:
  28% of selected posts fetch nothing usable (paywall, PDF, JS-rendered, 403, timeout). A good
  thread alone carries the card; a post is skipped only if it has neither. Real error path.
- **A soft failure looks like success.** A sign-in wall returns HTTP 200 with HTML, so `looks_gated`
  treats a short body carrying sign-in language as no article at all. Deliberately conservative:
  a wrong reject costs one article, a wrong accept puts a subscribe prompt on a card.
- Site chrome is stripped from articles (not comments) before the model sees them — a "Recent
  stories" block is a list of *other* articles' headlines. Conservative by necessity: a rule tight
  enough to catch linked headlines also deletes numbered lists and spec rows, which are often the
  substance. Measured at 12% removed; the tight version cost 50% on a list-shaped article.
- **The threshold is also the maturity test.** No age delay: a post at 200 points has proven itself
  whether it took six hours or two days, and holding back an overnight story is the worse failure.
  The 3-day window catches late risers; `published.json` means a post is generated once, ever.
- 200 measured over 13 days: ~24 stories/day clear it (15-32), so the count floats with how busy
  the day was. **No cap.** Hacker News bounds this itself; a cap would silently drop real news on a
  busy day, and at 100 points that is exactly what happened — the cap, not the threshold, was doing
  the selecting on 12 of 13 days.
- Record entities from day one even though nothing consumes them yet — free now, and the archive
  cannot be accumulated retroactively.

### Day file shape

```json
{
  "date": "2026-09-21",
  "cards": [{
    "id": 49792730,
    "url": "https://...",
    "depth": [
      {"text": "..."},
      {"text": "...", "data": [["latency", "2.1s"]]},
      {"link": true}
    ],
    "camps": "Two camps: ...",
    "comment_count": 470,
    "terms": ["x.ai", "frontier model"],
    "entities": ["x.ai"]
  }]
}
```

## Non-goals (v1)

No video, audio or TTS. No accounts or auth. No push. No topic filtering — the off-topic posts are the
texture that makes it feel alive. No personalization or interest ranking. No breaking news or intraday
updates; this is a once-a-day object. No comment threading. No related-posts UI until an archive exists
to link into. No database — a static host and one JSON per day.

## Open

- Does the camps line appear on the card face, or only inside the comment sheet?
- The 2D scroll-snap needs thumbing on a real phone before it is designed further.
