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

## Korean alongside English

**Now:** English only, for a reader who is a Korean beginner. The glance line is the one sentence
they must not have to decode.

**Do:** a second pass over the finished day file adding `simple_ko` / `substance_ko`,
**batched** — a whole day in one call. Measured with gemini-3.8-flash on real cards:

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

**Which model, still open.** Nothing checks the Korean mechanically, so model quality is the only
guard — the opposite of the main pass. Estimated from the Flash measurement at list prices:
GPT-6 Luna ~$0.20/mo, Flash ~$1.50 (~$3 from 2027-01-01), GPT-6 Sol ~$4. A ~$4/mo spread, so
choose on register and proper nouns: translate the same few cards with all three, `entities` as
the do-not-translate list, judge by eye. No Korean data on Luna or Sol yet (both 2026-09-22).

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
