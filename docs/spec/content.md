# Content

A vertical-swipe feed that tells a beginner developer what happened in tech today, from Hacker News.

**Awareness tool, not a learning tool.** Open it without thinking, know what's going on, close it.
Depth is available but never required. See `docs/decisions/` for why each choice was made.

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
where "read the whole thing" is the next thought a reader has, and as the glance card's source line
(the host name), which is a link. The second is not redundant — a card whose substance failed
verification has no detail tier, and would otherwise offer no route to the article at all.

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

## Non-goals (v1)

No video, audio or TTS. No accounts or auth. No push. No topic filtering — the off-topic posts are the
texture that makes it feel alive. No personalization or interest ranking. No breaking news or intraday
updates; this is a once-a-day object. No comment threading. No linking between related stories — an
awareness app shows you today, and a reader who wants the history has the calendar. No database — a static host, one JSON per day, one page per card.

## Open

- Does the camps line appear on the card face, or only inside the comment sheet?
