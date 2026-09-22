# Direction

Work with no code yet. Nothing here is committed to; an item earns work when its **trigger** fires,
and an entry untouched for months is a dead idea, not a debt — delete it. Deferrals that live next
to code are `ponytail:` comments instead.

---

## A real design pass

**Now:** it reads as a prototype, in roughly this order of how much it gives away:

- **Emoji as icons** (📅 💬 🔗 📖). The loudest tell — they render differently on every platform,
  sit on their own baselines, and read as placeholders. Inline SVG, no dependency.
- **No header.** The top bar is a date and three dots. There is no title, no sense of edition, and
  nothing that says what you are looking at when someone opens it cold.
- **One ratio for every card.** The glance is always a full-bleed 9:19.5 poster whatever the image
  is, so a wide screenshot is cropped to a sliver and a square logo is blown up. Letting the frame
  follow the image — contained, with a blurred fill behind — is the same fix as the image entry.
- **No typographic identity.** `system-ui` throughout. It is legible and it is anonymous, and on a
  card that is one sentence on a screen, the type *is* the design.
- **Placeholder-grade fallbacks.** Cards with no image get a hue-rotated gradient, which is the
  universal signal for "art not done yet".
- **Undesigned states.** "Loading…", the empty case, and the caught-up card are all plain text in
  the default size.
- **Colour is one borrowed accent.** HN orange, used for links, highlights, dots and the active
  state alike, with no considered palette around it.
- **Nothing moves.** Cards cut in with no entry, and depth has no sense of travel.

**Do:** treat the glance card as a poster — one sentence at 34px over an image is a typography
problem before a layout one. Type, palette and an icon set settle the rest.

**Trigger:** before showing it to anyone who is not you.

**Not:** a component library. Two screens, no reusable surfaces — it would be more code than the app.

## Better images

**Now:** `og:image`, which is picked to look good in a social card — so often a banner, logo or
headshot rather than anything about the post, and only ~45% of articles declare one. The viewer
crops it `cover`, cutting the edges off a wide image in a tall frame.

**Do:** fall back to the largest in-body `<img>`, then score candidates by size, position and alt
text — `fetch_page` already returns the HTML both need. Viewer side, a blurred full-bleed copy
behind a contained one.

**Trigger:** when a day's scroll feels visually repetitive.

**Not:** generating images — costs per card and cannot be verified against a source.

## Korean alongside English

**Now:** English only, for a reader who is a Korean beginner. The glance line is the one sentence
they must not have to decode.

**Do:** a second pass over the finished day file adding `simple_ko` / `substance_ko`, with
**gemini-3.8-flash**, **batched** — a whole day in one call. Measured on real cards:

| | per card |
|---|---|
| batched translation | **+$0.0020** (+15%, ~₩66/day at 24 cards) |
| one call per card | +$0.0074 (+55%) — re-sends the instructions 24 times |
| Korean written directly in the main call | ~free, but loses English |

Translate rather than generate both in the main call, despite that being cheaper: the English
`substance` is what was verified against verbatim quotes, so translating carries that verification
across. Generated independently the two drift, and the Korean is unverified. A separate pass also
fails without costing an edition. Quotes and the comment sheet stay English — a Korean card over an
English thread is the design question here, not the cost.

**Trigger:** wanting to show it to someone who does not read English comfortably.

**Not:** Papago — the register *is* the product ("구린", "풀어버렸대", not news-wire Korean) and MT
has no setting for it. **Not** bare Lite: measured, it wrote 오픈아이 for OpenAI and dropped Apache
and Snap. Markers survive on Lite fine, so if ₩56/day ever matters, feed it the card's existing
`entities` array as a do-not-translate list.

## Discussion as a selection signal

**Now:** selection is points only, at 200.

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
