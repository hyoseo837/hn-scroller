# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

People who want to keep up with Hacker News lightly — no pressure, in easy words. Not necessarily
confident developers: most HN posts are hard for them to parse and they will not research them one
by one. A Korean version serves the same reader when they are less confident in English, since
their first language is Korean: the browser's language picks it, a select beside the date switches.

Situation: phone, one hand, a spare two or three minutes (commute, in bed). Opened without thinking.

## Product Purpose

Tell the reader what happened in tech today, from Hacker News, as a vertical swipe feed.
An awareness tool, not a learning tool: open, know what's going on, close.

- **Works:** opened cold, 2-3 minutes of swiping, the reader recognizes today's terms and roughly
  who is arguing about what.
- **Fails:** the reader feels informed but retained nothing — fluent summaries nobody understood.

## Positioning

A day has a bottom. One edition, reached in about two minutes, then a "caught up" boundary — no
backlog, no unread counts, no streaks, no notifications. Every card fact is checked against the
source: the detail tier ships only with verbatim quotes that match the fetched article or thread.

## Operating Context

- Four runs a day (every 6h) append newly qualifying posts (≥150 points) to the UTC day's edition.
- Per post: a glance card (one plain lowercase sentence), optionally a detail card (names,
  versions, figures, the two camps). Swipe up for the next post, right for depth, left to back out.
- Per card: comments sheet (top-level, verbatim, with a generated "camps" line), glossary sheet
  (jargon from article and comments), link to the source.
- Older editions load below the caught-up boundary; a calendar browses past days.

## Capabilities and Constraints

- Static site on Cloudflare Pages (`hn.hyoseo.dev`), installable PWA. Vanilla HTML/CSS/JS, no
  build step, zero dependencies. Data contract: one JSON per day (`docs/SPEC.md`).
- Keyboard and wheel are first-class on desktop; the phone frame is centred there (430px column).
- Card text comes from a model and is rendered as text nodes, never `innerHTML`.
- Images are `og:image` when the article declares one (~45%); many cards have none.
- Name is open: "HN Scroller" may change. Domain stays `hn.hyoseo.dev`.
- **Undecided:** whether the camps line appears on the card face or only in the comment sheet.

## Brand Commitments

Voice is casual and human, a little amused — "someone made a digital brain of a fly to play Brood
War", not news-wire. Register is part of the product; heavy prose breaks the lightness. The Korean
version reads as a Korean tech headline: noun endings, compact Sino-Korean words, and the tech
words Korean developers write in English kept in English; comments keep each commenter's own voice.

## Evidence on Hand

Real editions in `data/` (e.g. `data/2026-09-22.json`, 35 cards), glossary in `data/glossary.json`.
No users, testimonials, or metrics exist — do not invent any.

## Product Principles

1. Lightness over completeness — a shorter card beats a padded one.
2. Never wrong: facts only from the source, definitions only from the glossary.
3. Pull, not push — nothing accumulates, nothing nags.
4. Depth is available, never required.

## Accessibility & Inclusion

- One-handed phone use: primary actions within thumb reach.
- WCAG AA text contrast in both light and dark themes.
- Korean text is first-class: lines break at spaces, labels drop Latin letter-spacing, and a card
  not yet translated stays English, marked `lang="en"`.
