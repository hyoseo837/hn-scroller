# Direction

Work with no code yet. Nothing here is committed to; an item earns work when its **trigger** fires,
and an entry untouched for months is a dead idea, not a debt — delete it. Deferrals that live next
to code are `ponytail:` comments instead.

---

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
- **Actions: v7, and off the hour.** `checkout@v4` and `setup-python@v5` run a deprecated Node 20;
  both are at v7 (Node 24, nothing this workflow uses removed). The cron fires at minute 0, GitHub's
  busiest, and runs start 3-5 h late: move it to `37 0,6,12,18 * * *`. One commit, with the timing
  comments. Trigger: once the first Luna production run is checked, so one change is tested at a time.

## Watch, do not build

- **Scale words in Korean.** `prompt.ko.md` keeps "$20 million" as written rather than 만 or 억, since
  a converted figure cannot be checked. On 09-23 "보조금 $20 million으로" read fine, "입력 tokens
  million개당 $4.00" did not (its own table wrote "1M tokens당"). If more jar, allow "1M" style.
- **Scheduled Actions are disabled on repos with no recent activity (~60 days).** GitHub's docs say
  "no repository activity" without defining it, so whether the bot's own commits count is unverified. If they do not, the app dies silently in two
  months. Check before then.
- **A published card is frozen.** Dedup means a post is generated once, so a story caught early
  keeps its thin thread and early camps line forever, even if it becomes the week's biggest story.
  Fixing it needs a refresh rule that changes a card under a reader who already saw it — the cost of
  that is not obviously worth paying.
