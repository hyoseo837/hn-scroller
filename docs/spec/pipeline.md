# Pipeline

## Pipeline

Runs every 6h. Select is free; only generate costs money.

```
select    Algolia search_by_date, tags=story, points>=150, 3-day window
          → dedupe by HN item ID against everything published
fetch     article text (cap ~6k tokens) + top-level comments (Firebase)
generate  card stack + camps line + glossary terms, per post
publish   one JSON file for the day
```

- **Model: GPT-6 Luna at high reasoning effort**: ~$0.0024/card (measured on 9 posts), ~$0.06/day
  at ~24 posts. Same model for prompt development and production, so the prompt is tuned on exactly what ships.
- **Quote verification is mechanical, not manual** (`verify_substance`). Any model is capable of
  fluent-but-wrong, which is the one failure this app cannot absorb. The glance and camps are still
  only prompt-governed — read those by eye when tuning.
- Generation is server-side and each post is generated once; users read a static file. **Cost is
  constant at any number of users** — it scales with posts, not readers.
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
- **The threshold is also the maturity test.** No age delay: a post at 150 points has proven itself
  whether it took six hours or two days, and holding back an overnight story is the worse failure.
  The 3-day window catches late risers; `published.json` means a post is generated once, ever.
- 150 measured over 14 days: a median of 32 stories/day clear it (22-43), so the count floats with
  how busy the day was. **No cap.** Hacker News bounds this itself; a cap would silently drop real news on a
  busy day, and at 100 points that is exactly what happened — the cap, not the threshold, was doing
  the selecting on 12 of 13 days.
- `entities` is recorded on every card: the names the Korean pass must keep as written.

### Day file shape

```json
{
  "date": "2026-09-21",
  "cards": [{
    "id": 49792730,
    "url": "https://...",
    "hn": "https://news.ycombinator.com/item?id=49792730",
    "title": "original HN title",
    "time": 1790000000,
    "points": 412,
    "depth": [
      {"text": "...", "tier": "simple"},
      {"text": "...", "tier": "substance", "data": [["latency", "2.1s"]]}
    ],
    "camps": "Two camps: ...",
    "comment_count": 470,
    "terms": ["x.ai", "frontier model"],
    "entities": ["x.ai"],
    "comments": [{"by": "user", "text": "first 400 chars…"}],
    "image": "https://... or null"
  }],
  "glossary": {"x.ai": "one sentence…", "frontier model": "one sentence…"}
}
```

`glossary` holds only this day's terms. A visit downloads the index and one day, so its size does
not grow with history; `data/glossary.json` is the generator's store and readers never fetch it.
