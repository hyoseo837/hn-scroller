# Direction

Things worth doing later. Not a backlog and not a promise — nothing here is committed to, and an
item earns work only when its **trigger** fires. If an item has sat here unchanged for months, that
is information: delete it.

Anything already deferred in code is a `ponytail:` comment, not an entry here. This file is for
work that has no code yet.

---

## A real design pass

**Now:** it reads as a prototype, and specifically because of these, roughly in order of how much
they give it away:

- **Emoji as icons** (📅 💬 🔗 📖). The loudest tell — they render differently on every platform,
  sit on their own baselines, and read as placeholders. Inline SVG, no dependency.
- **No typographic identity.** `system-ui` throughout. It is legible and it is anonymous, and on a
  card that is one sentence on a screen, the type *is* the design.
- **Placeholder-grade fallbacks.** Cards with no image get a hue-rotated gradient, which is the
  universal signal for "art not done yet".
- **Undesigned states.** "Loading…", the empty case, and the caught-up card are all plain text in
  the default size.
- **Colour is one borrowed accent.** HN orange, used for links, highlights, dots and the active
  state alike, with no considered palette around it.
- **Nothing moves.** Cards cut in with no entry, and depth has no sense of travel.

**Do:** treat the glance card as a poster — it is a single sentence at 34px over an image, which is
a typography problem more than a layout one. Everything else follows from settling type, a palette
and an icon set.

**Trigger:** before showing it to anyone who is not you. It is fine while the audience is one
person who knows why it looks like this.

**Not:** a component library or a CSS framework. There are two screens and no reusable surfaces;
a design system here would be more code than the app.

## Better images

**Now:** the card background is the article's `og:image`. That tag is chosen to look good in a
social card, so it is often a site banner, a logo or an author headshot rather than anything about
the post — and only ~45% of articles declare one at all. The viewer crops it with
`object-fit: cover`, which cuts the edges off a wide image in a tall frame.

**Do:** fall back to the largest in-body `<img>` when there is no `og:image`, then score candidates
by dimensions, position and alt text. `fetch_page` already returns the raw HTML both need. On the
viewer side, a blurred full-bleed copy behind a contained one, the way music apps show album art.

**Trigger:** when a scroll through a day's cards feels visually repetitive, or when the share of
cards with no image stops feeling acceptable.

**Not:** generating images. It costs real money per card and cannot be verified against a source,
which is the opposite of how everything else here works.

## Story threading

**Now:** `entities` is recorded on every card and nothing reads it.

**Do:** link a post to earlier posts about the same entity — "4th post this month about Zig 0.14",
"previously: announced in March". This is the strongest answer to the beginner's real problem, that
every story arrives mid-conversation with no history. It is also the honest version of showing a
developing story, as opposed to repeating a card.

**Trigger:** a few weeks of archive. It does nothing on a thin index and cannot be evaluated early.

## Discussion as a selection signal

**Now:** selection is points only, at 200.

**Do:** add `OR comments >= ~150`. Points and discussion come apart, and a high comment-to-point
ratio is precisely a contested story — which is what the camps line exists for. Measured example: a
Waymo story at 135 points carried 223 comments and would never be selected today.

**Trigger:** after a week of reading real editions, if the camps lines feel thin or the interesting
arguments are visibly missing.

## Extraction quality

**Now:** 28% of selected posts yield no article at all (paywall, PDF, JS-rendered, timeout) and fall
back to comments only. Boilerplate stripping is deliberately conservative — 12% removed — because a
tighter rule deleted numbered lists and spec rows that were the substance, measured at 50% loss on
one article.

**Do:** proper content extraction, which realistically means Readability plus a DOM parser. That is
the first dependency this project would take, so it needs to be worth it.

**Trigger:** if comment-only cards start reading noticeably worse than article-backed ones. Worth
measuring before assuming.

## Multimodal cards

**Now:** the model is sent text only and never sees the hero image or any chart.

**Do:** send the image for posts whose substance is visual — benchmark charts, before/after shots.

**Trigger:** not soon. It breaks the verification model: a claim read off a chart cannot be backed
by a verbatim text quote, which is the whole mechanism preventing fabrication. It needs its own
answer to that question first, not just a budget.

## Smaller, cheap

- **Offline reading.** A service worker so a downloaded edition survives the subway. The data is one
  static JSON per day, so this is genuinely small. Trigger: if the app gets opened while commuting.
- **Glossary browse view.** 171 terms after one day. A searchable list is a few lines once it is
  large enough to be interesting on its own.
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
