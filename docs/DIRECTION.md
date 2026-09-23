# Direction

Work with no code yet. Nothing here is committed to; an item earns work when its **trigger** fires,
and an entry untouched for months is a dead idea, not a debt — delete it. Deferrals that live next
to code are `ponytail:` comments instead.

---

## A real design pass

**Now:** layout, icons, images and palette are done and recorded in `DESIGN.md`. The user keeps the
fonts, sizes and marker highlight — type is not on this list. What is left:

- **Undesigned states.** "Loading…", the empty case, and the caught-up card are plain text.
- **Nothing moves.** Cards cut in with no entry, and depth has no sense of travel.

**Do:** one authored motion for depth, then design the three states. Update `DESIGN.md` with them.

**Trigger:** before showing it to anyone who is not you.

**Not:** a component library. Two screens, no reusable surfaces — it would be more code than the app.

## Better images

**Now:** `og:image`, which is picked to look good in a social card — so often a banner, logo or
headshot rather than anything about the post, and only ~53% of cards have one. The viewer shows
it whole, never cropped (cropping a 1200x630 card to the frame kept 24% of its width), and drops
anything under 300px wide — measured, those were all logos or icons.

Cards without one get a clipping: the original HN title as a black-on-paper newspaper headline.

**Do:** fall back to the largest in-body `<img>`, then score candidates by size, position and alt
text — `fetch_page` already returns the HTML both need. Measured 2026-09-23 on the 33 no-image
cards: 12 have an in-body image ≥600px wide, 16 have no `<img>` at all (JS-rendered), 4 failed
to fetch. So ~53% → ~70% of cards with a picture, at the cost of sizing up to 15 images per page.

**Trigger:** when the clippings feel repetitive next to real pictures.

**Not:** generating images — costs per card and cannot be verified against a source.

## Translations: Korean first, then others — next up

**Now:** English only. `PRODUCT.md`: a Korean version is planned for the same reader, whose first
language is Korean, in the same register, with Korean text first-class (line breaking, fonts).

**Do:** add translations, Korean first, possibly more languages later. The design is still to be
discussed; this entry holds what is known.

**Facts the design has to fit:**
- Cards are written by GPT-6 Luna at high effort (`generate/models.py`). Each `data/<date>.json`
  carries its cards plus a `glossary` slice of their terms; a visit downloads the index plus one day.
- Four runs a day append new cards to the same day file.
- Only `substance` is checked mechanically (verbatim quotes). The glance, camps and glosses are
  prompt-governed.
- Viewer UI strings (buttons, hints, sheet titles, "You're caught up") live in `js/*.js` and
  `index.html`. Dates already follow the browser locale. `<html>` has no `lang` attribute today.
- `CLAUDE.md`: client state is `localStorage`, resume position only.

**Earlier findings, from this entry's previous version:**

| per card | cost |
|---|---|
| batched translation, one call per day, Flash (measured) | +$0.0020 |
| one call per card, Flash (measured) | +$0.0074, re-sends the instructions every time |
| batched, Luna (estimate at list price, unmeasured) | ~+$0.0003 |

- Translating the finished English, rather than writing Korean in the main call, was preferred:
  the English detail is what was checked against quotes, and a separate pass fails without costing
  an edition. Writing Korean in the main call was ~free but loses English.
- Rejected: Papago and other MT (the register is the product: "구린", "풀어버렸대", not news-wire
  Korean); Gemini Flash-Lite (wrote 오픈아이 for OpenAI, dropped Apache and Snap). Highlight markers
  survived translation fine. Each card's `entities` was proposed as a do-not-translate list.
- No Korean output from Luna has been seen yet.

**Open questions:**
- Where translations live: fields in the day file, a file per language per day, or something else.
- Which parts get translated: glance, detail, camps, data labels, glosses, glossary terms, UI.
  Comments and the HN title are verbatim English today.
- How a reader gets a language: browser language, a toggle, or both.
- Which Luna effort level for translation, and how to judge quality.
- Whether and how to check translations mechanically.
- Whether past days get translated.
- How a second language after Korean gets added.

**Trigger:** fired: the user picked this as the next task on 2026-09-23.

## Discussion as a selection signal

**Now:** selection is points only, at 150.

**Do:** add `OR comments >= ~150`. Points and discussion come apart, and a high comment-to-point
ratio is precisely a contested story — what the camps line exists for. Measured: a Waymo story at
135 points carried 223 comments and would never be selected.

**Trigger:** after a week of real editions, if camps lines feel thin.

## Extraction quality

**Now:** 28% of selected posts yield no article (paywall, PDF, JS-rendered, timeout) and fall back
to comments. Boilerplate stripping is conservative — 12% removed — because a tighter rule deleted
numbered lists and spec rows that were the substance, at 50% loss on one article.

**Do:** proper extraction — realistically Readability plus a DOM parser, the first dependency this
project would take.

**Trigger:** if comment-only cards read noticeably worse than article-backed ones. Measure first.

## Multimodal cards

Send the hero image for posts whose substance is visual (benchmark charts). **Blocked, not
scheduled:** a claim read off a chart cannot be backed by a verbatim quote, which is the whole
mechanism preventing fabrication. Needs an answer to that first, not a budget.

## Smaller, cheap

- **Offline reading.** A service worker so a downloaded edition survives the subway. The data is one
  static JSON per day, so this is genuinely small. Trigger: if the app gets opened while commuting.
- **Bump the Actions versions.** `checkout@v4` and `setup-python@v5` are pinned to a deprecated
  Node 20 runtime, and `ubuntu-latest` migrates to Ubuntu 26 in October 2026. Warnings only today.

## Watch, do not build

- **Scheduled Actions are disabled on repos with no recent activity (~60 days).** Whether the bot's
  own nightly commits count as activity is unverified. If they do not, the app dies silently in two
  months. Check before then.
- **A published card is frozen.** Dedup means a post is generated once, so a story caught early
  keeps its thin thread and early camps line forever, even if it becomes the week's biggest story.
  Fixing it needs a refresh rule that changes a card under a reader who already saw it — the cost of
  that is not obviously worth paying.
