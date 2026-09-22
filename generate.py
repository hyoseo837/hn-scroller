#!/usr/bin/env python3
"""Daily job: select HN posts, fetch their source, ask Gemini for card CONTENT only,
then assemble the JSON here. The model never sees or emits ids, urls or counts —
those are facts we already have from HN.

    python3 generate.py          write data/<today UTC>.json
    python3 generate.py --check  offline self-check, no network, no API key
    python3 generate.py --dry 3  fetch 3 posts, print the model input, call nothing
    python3 generate.py --sample 1  one real call, print the card, write nothing

The system prompt lives in prompt.md so it can be edited without touching code.
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

MODEL = "gemini-3.8-flash"
API = "https://generativelanguage.googleapis.com/v1beta/interactions"
MIN_POINTS = 200  # measured: ~24 stories/day clear this, range 15-32
WINDOW_DAYS = 3
MAX_COMMENTS = 20
SHEET_COMMENTS = 5  # how many go in the day file for the comment sheet
SHEET_COMMENT_CHARS = 400
# Measured over 210 top-level comments: median 304, p99 1,490, max 1,600. At 2,000
# nothing real is touched — it exists so one pathological thread cannot become an
# unbounded prompt. Comments were the only input with no ceiling.
MODEL_COMMENT_CHARS = 2_000
MAX_ARTICLE_CHARS = 24_000  # ~6k tokens
MIN_ARTICLE_CHARS = 500  # below this, fall back to title + comments
CALL_SPACING_S = 5  # free tier is 5-15 RPM; 35 posts ~= 3 min
PRICE_IN = 0.75   # USD per 1M input tokens
PRICE_OUT = 3.75  # USD per 1M output tokens; thinking bills as output

# Thinking is counted separately from total_output_tokens but billed as output,
# and it runs ~3x the visible answer — so it dominates both cost and wall time.
USAGE = {"calls": 0, "input": 0, "output": 0, "thought": 0}

ROOT = Path(__file__).parent
DATA = ROOT / "data"
PROMPT = ROOT / "prompt.md"

# The model may only write these. No id, no url, no counts — the code owns those.
SCHEMA = {
    "type": "object",
    "properties": {
        "simple": {"type": "string"},
        "substance": {"type": ["string", "null"]},
        "support": {"type": "array", "items": {"type": "string"}},
        "data": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
        "camps": {"type": ["string", "null"]},
        "terms": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"term": {"type": "string"}, "gloss": {"type": "string"}},
                "required": ["term", "gloss"],
            },
        },
        "entities": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["simple", "substance", "support", "camps", "terms", "entities"],
}

# ------------------------------------------------------------- pure helpers

_DROP_BLOCKS = re.compile(
    r"<(script|style|noscript|svg)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL
)
_ENTITIES = {
    "&nbsp;": " ",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&#x27;": "'",
    "&#39;": "'",
}


def strip_html(html: str) -> str:
    """Flatten to text, but keep the structure a reader would see.

    Collapsing everything to one line loses which number belongs to which label,
    so spec tables stop producing `data` rows. Cell and block boundaries survive;
    quote matching is unaffected because _normalize collapses whitespace anyway.
    """
    text = _DROP_BLOCKS.sub(" ", html)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"</(?:td|th)\s*>", " | ", text, flags=re.IGNORECASE)
    text = re.sub(r"</(?:tr|p|div|li|h[1-6]|section|article)\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    text = re.sub(r"[^\S\n]+", " ", text)  # collapse spaces, keep line breaks
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\s*\|\s*(?=\n|$)", "", text)  # last cell of a row needs no separator
    return re.sub(r"\n{3,}", "\n\n", text).strip(" \n|")


_NAV_GLYPH = "\u2630\u25be\u25b8\u00bb"
_PAYWALL = (
    "subscribe to", "subscriber", "sign in to", "log in to", "create an account",
    "enable javascript", "checking your browser", "verify you are human",
    "register to continue", "article limit", "already a member", "start your free trial",
)


def drop_boilerplate(text: str) -> str:
    """Strip nav-shaped lines from an ARTICLE. Not for comments.

    A site's chrome comes through the same as its prose, and a "Recent stories"
    block is a list of *other* articles' headlines — the model has no way to know
    those are not part of this post. Keeps table rows, which are short and
    unpunctuated but are exactly the figures `data` is built from.
    """
    keep = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        words = stripped.split()
        # Table rows and numbered list items are short and unpunctuated by nature,
        # and are often the substance itself — spec figures, a list of styles.
        if "|" in stripped or re.match(r"^\d+[.)]\s", stripped):
            keep.append(stripped)
            continue
        if any(ch in stripped for ch in _NAV_GLYPH) and len(words) < 14:
            continue
        # Only obvious chrome. A tighter rule (drop every unpunctuated line under
        # ~15 words) also deletes numbered lists and short spec lines, which are
        # often the substance — measured at 50% loss on a list-shaped article.
        # Separating nav from a list properly is what Readability is for.
        if len(words) < 6 and not re.search(r"[.!?:;\"')\u201d]$", stripped):
            continue
        keep.append(stripped)
    return "\n".join(keep)


def looks_gated(text: str) -> bool:
    """A short body carrying sign-in language is a stub, not an article.

    Long pieces mention subscriptions in a footer all the time, so length is what
    separates a paywall wall from a newsletter plug. Conservative on purpose: a
    wrong reject costs one article, a wrong accept puts a subscribe prompt on a card.
    """
    return len(text) < 1500 and any(m in text.lower() for m in _PAYWALL)


def select_posts(hits: list[dict], published: list) -> list[dict]:
    """Everything above the threshold that has not been published. No cap.

    Hacker News caps this by itself: ~24 stories/day clear 200 points, 32 on the
    busiest day measured. A cap here would silently drop real news on a big day,
    which is the failure an awareness app cannot afford.

    The threshold doubles as the maturity test: a post at 200 points has proven
    itself whether that took six hours or two days, so there is no age delay —
    holding back a story that broke overnight is the worse failure for an
    awareness app. The 3-day window catches late risers, and `published` means
    a post is generated once, ever.
    """
    seen = {str(p) for p in published}
    keep = [h for h in hits if h["points"] >= MIN_POINTS and str(h["objectID"]) not in seen]
    keep.sort(key=lambda h: -h["points"])
    return keep


def _normalize(text: str) -> str:
    """Punctuation out first, then collapse — the other order leaves a run of
    spaces where punctuation was, and a valid quote then fails to match."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def unsupported_quotes(support: list[str], source: str, min_words: int = 6) -> list[str]:
    """Which of the model's claimed source quotes are not actually in the source.

    Prose claims cannot be verified mechanically in general, but a quote can be.
    Requiring receipts for the substance tier turns "trust the prompt" into a check:
    a fabricated claim has no real quote behind it, so the quote fails to match.
    """
    haystack = _normalize(source)
    bad = []
    for quote in support or []:
        needle = _normalize(quote)
        if len(needle.split()) < min_words or needle not in haystack:
            bad.append(quote)
    return bad


def peek(text: str, limit: int = SHEET_COMMENT_CHARS) -> str:
    """Trim a comment without slicing through a word."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).rstrip(" ,;:.\u2014-") + "\u2026"


def assemble_card(
    post: dict,
    content: dict,
    comment_count: int,
    comments: list[dict] | None = None,
    image: str | None = None,
) -> dict:
    """Code owns the envelope. `content` carries only what the model wrote."""
    # Two rungs only: the glance, then the detail. A middle "headline" tier just
    # restated the glance in longer words, and cost more to generate than it added.
    depth: list[dict] = [{"text": content["simple"], "tier": "simple"}]
    if content.get("substance"):
        tier = {"text": content["substance"], "tier": "substance"}
        if content.get("data"):
            tier["data"] = content["data"]
        depth.append(tier)

    return {
        "id": post["id"],
        "url": post.get("url"),
        "hn": f"https://news.ycombinator.com/item?id={post['id']}",
        "title": post["title"],  # original HN title, kept verbatim for reference
        "depth": depth,
        "camps": content.get("camps") or None,
        "comment_count": comment_count,
        "terms": [t["term"] for t in content.get("terms") or []],
        "entities": content.get("entities") or [],
        # A peek for the sheet, verbatim and unprocessed. The full thread is on HN.
        "comments": [
            {"by": c["by"], "text": peek(c["text"])} for c in (comments or [])[:SHEET_COMMENTS]
        ],
        "image": image,
    }


def verify_substance(content: dict, source: str) -> list[str]:
    """Substance that cannot show a real quote behind it does not ship.

    Mutates `content` to drop the tier, leaving a 2-card stack — which the spec
    already treats as correct. A missing tier is a shrug; an invented one is the
    app doing the opposite of its job.
    """
    if not content.get("substance"):
        return []
    bad = unsupported_quotes(content.get("support"), source)
    if bad or not content.get("support"):
        content["substance"] = None
        content["data"] = []
    return bad


def model_input(title: str, article: str, comments: list[str]) -> str:
    parts = [f"HACKER NEWS TITLE: {title}"]
    parts.append(
        f"\nARTICLE TEXT:\n{article}"
        if article
        else "\n(No article text available — work from the title and comments only.)"
    )
    parts.append(
        "\nTOP-LEVEL COMMENTS:\n"
        + "\n".join(f"- {c['by']}: {peek(c['text'], MODEL_COMMENT_CHARS)}" for c in comments)
        if comments
        else "\n(No comments yet.)"
    )
    return "\n".join(parts)


def output_text(body: dict) -> str:
    """Pull the answer out of an /interactions response.

    `steps` holds the run in order. Reasoning steps are `type: "thought"` and carry
    no `content` at all, so skipping them is not optional — the answer is in the
    content blocks of a later step. Last text block wins, matching the SDK's
    `output_text`, which is documented as the last text blocks in the response.
    """
    texts = [
        block["text"]
        for step in body.get("steps") or []
        if isinstance(step, dict)
        for block in step.get("content") or []
        if isinstance(block, dict) and isinstance(block.get("text"), str)
    ]
    if texts:
        return texts[-1]
    raise RuntimeError(
        f"no text block in Gemini response (status={body.get('status')!r}, "
        f"keys={sorted(body)}):\n{json.dumps(body)[:1500]}"
    )


# ------------------------------------------------------------------ sources


def _get(url: str, timeout: int = 15, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {"user-agent": "hn-scroller/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def select_from_algolia(published: list) -> list[dict]:
    since = int(time.time()) - WINDOW_DAYS * 86_400
    query = urllib.parse.urlencode(
        {
            "tags": "story",
            "numericFilters": f"created_at_i>{since},points>{MIN_POINTS}",
            "hitsPerPage": "100",
        }
    )
    body = _get(f"https://hn.algolia.com/api/v1/search_by_date?{query}")
    return select_posts(json.loads(body)["hits"], published)


def hn_item(item_id) -> dict:
    return json.loads(_get(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json"))


def top_comments(item: dict) -> list[str]:
    """Top-level only. Flattening the tree is deliberate — see SPEC.md."""
    kid_ids = (item.get("kids") or [])[:MAX_COMMENTS]
    if not kid_ids:
        return []

    def fetch(kid_id):
        try:
            return hn_item(kid_id)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=8) as pool:
        kids = list(pool.map(fetch, kid_ids))
    return [
        {"by": k.get("by") or "anon", "text": strip_html(k["text"])}
        for k in kids
        if k and k.get("text") and not k.get("dead") and not k.get("deleted")
    ]


_META_IMAGE = re.compile(
    r"<meta[^>]+(?:property|name)=[\"'](?:og:image(?::secure_url)?|twitter:image(?::src)?)[\"'][^>]*>",
    re.IGNORECASE,
)
_CONTENT = re.compile(r"content=[\"']([^\"']+)[\"']", re.IGNORECASE)


def hero_image(html: str, base_url: str) -> str | None:
    """The article's own social image. og:image is what the author chose to
    represent the piece, which beats guessing at the first <img> in the body.

    ponytail: og:image only. It is chosen for social cards, so it is often a
    site banner, a logo or an author headshot rather than anything about this
    post, and only ~45% of articles declare one at all. Upgrade path, in order
    of effort: fall back to the largest in-body <img> when no og:image exists;
    then score candidates by dimensions, position and alt text. Both need the
    raw HTML, which fetch_page already returns.
    """
    for tag in _META_IMAGE.findall(html or ""):
        found = _CONTENT.search(tag)
        if not found:
            continue
        url = urllib.parse.urljoin(base_url or "", found.group(1).strip())
        if url.startswith(("http://", "https://")):
            return url
    return None


def fetch_page(url: str) -> str:
    """Raw HTML, fetched once — text and image both come out of it."""
    try:
        req = urllib.request.Request(url, headers={"user-agent": "hn-scroller/1.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            if "text/html" not in res.headers.get("content-type", ""):
                return ""
            return res.read(4_000_000).decode(res.headers.get_content_charset() or "utf-8", "replace")
    except Exception:
        return ""  # paywall, PDF, JS-rendered, dead link — fall back to comments


def article_text(item: dict) -> str:
    if item.get("text"):
        return strip_html(item["text"])  # Ask HN / self post
    if not item.get("url"):
        return ""
    try:
        req = urllib.request.Request(item["url"], headers={"user-agent": "hn-scroller/1.0"})
        with urllib.request.urlopen(req, timeout=15) as res:
            if "text/html" not in res.headers.get("content-type", ""):
                return ""
            raw = res.read(4_000_000).decode(res.headers.get_content_charset() or "utf-8", "replace")
    except Exception:
        return ""  # paywall, PDF, JS-rendered, dead link — fall back to comments
    return strip_html(raw)[:MAX_ARTICLE_CHARS]


def sources(item_id) -> dict:
    """Everything the model is allowed to see for one post, fetched once."""
    item = hn_item(item_id)
    url = item.get("url") or ""
    with ThreadPoolExecutor(max_workers=2) as pool:
        page_future = pool.submit(fetch_page, url) if url and not item.get("text") else None
        comments = top_comments(item)
        html = page_future.result() if page_future else ""
    if item.get("text"):
        raw = strip_html(item["text"])  # Ask HN / self post: no site chrome to strip
    else:
        raw = drop_boilerplate(strip_html(html))[:MAX_ARTICLE_CHARS]
    # Too thin, or a sign-in stub that returned 200 like a real page -> comments carry it
    article = "" if len(raw) < MIN_ARTICLE_CHARS or looks_gated(raw) else raw
    bodies = [c["text"] for c in comments]
    return {
        "item": item,
        "article": article,
        "comments": comments,
        "image": hero_image(html, url),
        "source": article + "\n" + "\n".join(bodies),  # what claims are checked against
        "usable": bool(article) or bool(comments),
    }


# ------------------------------------------------------------------- gemini


def card_content(title: str, article: str, comments: list[str]) -> dict:
    payload = json.dumps(
        {
            "model": MODEL,
            "system_instruction": PROMPT.read_text(encoding="utf-8"),
            "input": model_input(title, article, comments),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": SCHEMA,
            },
        }
    ).encode()
    req = urllib.request.Request(
        API,
        data=payload,
        headers={
            "x-goog-api-key": os.environ["GEMINI_API_KEY"],
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            body = json.loads(res.read())
    except urllib.error.HTTPError as err:
        raise RuntimeError(f"gemini {err.code}: {err.read()[:300].decode('utf-8', 'replace')}")

    used = body.get("usage") or {}
    USAGE["calls"] += 1
    USAGE["input"] += used.get("total_input_tokens") or 0
    USAGE["output"] += used.get("total_output_tokens") or 0
    USAGE["thought"] += used.get("total_thought_tokens") or 0
    return json.loads(output_text(body))


def usage_line() -> str:
    billed_out = USAGE["output"] + USAGE["thought"]
    cost = USAGE["input"] / 1e6 * PRICE_IN + billed_out / 1e6 * PRICE_OUT
    share = USAGE["thought"] / billed_out * 100 if billed_out else 0
    return (
        f"{USAGE['calls']} call{'s' if USAGE['calls'] != 1 else ''} | in {USAGE['input']:,} | out {billed_out:,} "
        f"({USAGE['thought']:,} thinking, {share:.0f}%) | ${cost:.3f}"
    )


# --------------------------------------------------------------------- main


def load_env() -> None:
    """Read .env (gitignored) so the key doesn't have to be exported every shell.
    A real environment variable always wins, which is how CI passes it in."""
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def read_json(name: str, fallback):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def write_json(name: str, value) -> None:
    (DATA / name).write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    # Unbuffered progress: piped to a file or an Actions log, buffering hides every
    # line until the run ends, which is exactly when you no longer need them.
    sys.stdout.reconfigure(line_buffering=True)
    load_env()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set (put it in .env, or export it)")

    # Newspaper convention: the edition is dated by its run date and holds the
    # preceding 24h, so the freshest file is always "today".
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    DATA.mkdir(exist_ok=True)
    published = read_json("published.json", [])
    glossary = read_json("glossary.json", {})
    index = read_json("index.json", [])

    selected = select_from_algolia(published)
    print(f"selected {len(selected)} posts")

    cards = []
    for i, hit in enumerate(selected):
        try:
            got = sources(hit["objectID"])
            item = got["item"]
            if not got["usable"]:
                print(f"  skip {hit['objectID']}: no article text and no comments")
                continue

            content = card_content(item["title"], got["article"], got["comments"])
            bad = verify_substance(content, got["source"])
            if bad:
                print(f"    dropped substance, {len(bad)} quote(s) not in source")
            cards.append(
                assemble_card(
                    {"id": item["id"], "url": item.get("url"), "title": item["title"]},
                    content,
                    item.get("descendants") or 0,
                    got["comments"],
                    got["image"],
                )
            )
            # ponytail: re-glosses terms we already know and drops the result. One wasted
            # field per post beats a second API call; split it out if the bill ever shows.
            for term in content.get("terms") or []:
                glossary.setdefault(term["term"], term["gloss"])
            published.append(hit["objectID"])
            print(f"  {i + 1}/{len(selected)} {item['title'][:60]}")
        except Exception as err:  # one bad post must not lose the day
            print(f"  fail {hit['objectID']}: {err}", file=sys.stderr)
        if i < len(selected) - 1:
            time.sleep(CALL_SPACING_S)

    if not cards:
        sys.exit("no cards generated — leaving yesterday's file in place")

    # Merge, never replace: a re-run on the same day (a retry after a crash, or a
    # second pass picking up what a guard cut) must not delete the earlier batch.
    # Existing first: each run takes the highest-scoring posts left, so the earlier
    # batch outranks this one. Prepending would put the weakest cards on top.
    existing = read_json(f"{date}.json", {}).get("cards", [])
    already = {c["id"] for c in existing}
    merged = existing + [c for c in cards if c["id"] not in already]
    write_json(f"{date}.json", {"date": date, "cards": merged})
    if existing:
        print(f"merged: {len(existing)} already in today's file + {len(merged) - len(existing)} new")
    write_json("glossary.json", glossary)
    write_json("published.json", published)
    write_json("index.json", sorted({date, *index}, reverse=True))
    print(f"wrote data/{date}.json ({len(merged)} cards)")
    print(usage_line())


# ------------------------------------------------------------------ dry run


def dry(n: int) -> None:
    """Selection + fetch + extraction against live HN, stopping before the model.
    This is the loop to iterate extraction and prompt wording in — it costs nothing."""
    selected = select_from_algolia(read_json("published.json", []))
    print(f"selected {len(selected)} posts, showing {min(n, len(selected))}\n")
    for hit in selected[:n]:
        got = sources(hit["objectID"])
        item = got["item"]
        print("=" * 78)
        print(f"{hit['points']}pts {item.get('descendants') or 0}c  {item['title']}")
        article = got["article"]
        print("article:", f"{len(article)} chars" if article else "NONE (comments only)")
        print(f"comments: {len(got['comments'])}  usable: {got['usable']}")
        print("-" * 78)
        print(model_input(item["title"], got["article"], got["comments"])[:1200])
        print()


# ------------------------------------------------------------------- sample


def sample(n: int) -> None:
    """Real Gemini calls, assembled cards printed, nothing written and nothing
    marked published. The smallest thing that proves the whole chain: response
    shape, schema adherence, and whether the cards are any good."""
    load_env()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set (put it in .env, or export it)")

    selected = select_from_algolia(read_json("published.json", []))
    print(f"selected {len(selected)} posts, sampling {min(n, len(selected))}\n")
    for hit in selected[:n]:
        got = sources(hit["objectID"])
        item = got["item"]
        if not got["usable"]:
            print(f"skip {hit['objectID']}: no article text and no comments\n")
            continue

        basis = f"{len(got['article'])} chars" if got["article"] else "COMMENTS ONLY"
        print("=" * 78)
        print(f"{hit['points']}pts  {item['title']}")
        print(f"basis: article {basis}, {len(got['comments'])} comments")
        print("-" * 78)

        content = card_content(item["title"], got["article"], got["comments"])
        for quote in verify_substance(content, got["source"]):
            print(f"  UNSUPPORTED QUOTE, substance dropped: {quote!r}")
        card = assemble_card(
            {"id": item["id"], "url": item.get("url"), "title": item["title"]},
            content,
            item.get("descendants") or 0,
            got["comments"],
            got["image"],
        )
        print(json.dumps(card, indent=2, ensure_ascii=False))
        print(f"  usage: {usage_line()}")
        # the card keeps only term names; show the glosses so they can be judged too
        for term in content.get("terms") or []:
            print(f"  glossary[{term['term']}] = {term['gloss']}")
        print()


# -------------------------------------------------------------------- check


def check() -> None:
    assert strip_html("<p>hi <b>there</b></p>") == "hi there"
    # a spec table must keep label-to-number pairing, or `data` rows go missing
    table = "<table><tr><td>Latency P50</td><td>32.8 ms</td></tr><tr><td>ECE</td><td>0.081</td></tr></table>"
    assert strip_html(table) == "Latency P50 | 32.8 ms\nECE | 0.081", strip_html(table)
    assert strip_html("<p>one</p><p>two</p>") == "one\ntwo", "blocks stay apart"
    assert strip_html("a<br>b") == "a\nb"

    # Boilerplate stripping: site chrome goes, prose and figures stay.
    page = "\n".join([
        "\u2630 latest speech privacy tools \u25be recommended tools",
        "Recent stories",
        "The UK's Online Censorship Law Has Entered Its Litigation Era",
        "Spain ordered blocks on Archive.today after a complaint was filed.",
        "Latency P50 | 32.8 ms",
        "Sign in",
    ])
    kept = drop_boilerplate(page)
    assert "Spain ordered blocks" in kept, "prose survives"
    assert "Latency P50 | 32.8 ms" in kept, "table rows survive — they are what `data` is built from"
    assert "latest speech privacy" not in kept, "nav glyphs go"
    assert "Recent stories" not in kept and "Sign in" not in kept, "short unpunctuated fragments go"
    # Known limit: a linked headline is as long as a sentence, so it survives. A
    # rule tight enough to catch it deletes numbered lists and spec lines too.
    assert "9. Memphis Design" in drop_boilerplate("9. Memphis Design"), "list items must survive"

    # Soft failures: HTTP 200, but the body is a sign-in wall.
    assert looks_gated("Subscribe to read the rest. Already a member? Sign in to continue.")
    assert looks_gated("Please enable JavaScript to continue.")
    long_piece = "Real reporting. " * 120 + "Subscribe to our newsletter."
    assert not looks_gated(long_piece), "a long article with a footer plug is not a paywall"
    assert not looks_gated("A short post with no gate at all.")
    # quote checking must survive the line breaks
    # a quote must still match across the cell separators we just introduced
    assert unsupported_quotes(["Latency P50 | 32.8 ms | ECE"], strip_html(table)) == []
    # punctuation between words must not defeat a real quote
    assert unsupported_quotes(["one hundred poster styles, with prompts"],
                              "a catalogue of one hundred poster styles - with prompts") == []
    assert strip_html("<script>evil()</script>ok") == "ok"
    assert strip_html("a &amp; b&#x27;s") == "a & b's"

    # A page shaped like a real article: the junk must go, the prose must survive.
    # Live fetching can't be exercised in CI, so the parser is pinned here instead.
    page = """<!doctype html><html><head><title>T</title>
      <style>.a{color:red}</style>
      <script type="application/ld+json">{"@type":"Article"}</script>
      </head><body>
      <nav><a href="/">Home</a><a href="/about">About</a></nav>
      <!-- tracking comment -->
      <article><h1>Zig 0.14 Released</h1>
      <p>Incremental compilation landed, cutting rebuild times to <b>0.3s</b>.</p>
      <p>The compiler now caches&nbsp;per-function.</p></article>
      <svg viewBox="0 0 1 1"><path d="M0 0"/></svg>
      <noscript>Enable JS</noscript>
      <footer>&copy; 2026</footer></body></html>"""
    text = strip_html(page)
    assert "Incremental compilation landed" in text
    assert "0.3s" in text, "figures must survive — they are what data cards cite"
    assert "caches per-function" in text, "&nbsp; becomes a real space"
    assert "color:red" not in text and "@type" not in text, "style/script dropped"
    assert "Enable JS" not in text and "M0 0" not in text, "noscript/svg dropped"
    assert "tracking comment" not in text, "comments dropped"
    assert "  " not in text, "whitespace collapsed"

    hits = [
        {"objectID": "1", "points": 500},
        {"objectID": "2", "points": 199},  # under threshold
        {"objectID": "3", "points": 300},
        {"objectID": "4", "points": 800},  # already published
        {"objectID": "5", "points": 200},  # exactly at the bar gets in
    ]
    picked = select_posts(hits, ["4"])
    assert [h["objectID"] for h in picked] == ["1", "3", "5"], "filters, dedupes, sorts by points"
    assert len(select_posts([{"objectID": str(i), "points": 900} for i in range(400)], [])) == 400, (
        "no cap: every post above the threshold runs, however busy the day"
    )

    # Same-day merge keeps the stronger earlier batch on top and drops repeats.
    prior = [{"id": 1}, {"id": 2}]
    fresh = [{"id": 2}, {"id": 3}]
    already = {c["id"] for c in prior}
    assert [c["id"] for c in prior + [c for c in fresh if c["id"] not in already]] == [1, 2, 3]

    post = {"id": 7, "url": "https://x.test", "title": "Raw HN Title"}
    full = assemble_card(
        post,
        {
            "simple": "s",
            "substance": "s",
            "data": [["latency", "2.1s"]],
            "camps": "two camps",
            "terms": [{"term": "wasm", "gloss": "..."}],
            "entities": ["x.ai"],
        },
        470,
    )
    assert len(full["depth"]) == 2, "glance + detail; link is a button, headline is gone"
    assert [d.get("tier") for d in full["depth"]] == ["simple", "substance"]
    assert full["depth"][1]["data"] == [["latency", "2.1s"]]  # substance tier
    assert full["terms"] == ["wasm"], "card carries term names, glosses live in the glossary"
    assert full["comments"] == [], "no comments passed means no peek"
    many = [{"by": f"u{i}", "text": "long word " * 90} for i in range(6)]
    peek_card = assemble_card(post, {"simple": "s"}, 9, many)
    assert len(peek_card["comments"]) == SHEET_COMMENTS, "sheet peek is capped"
    assert peek_card["comments"][0]["by"] == "u0", "the author is kept — attribution is readability"
    assert peek_card["comments"][0]["text"].endswith("\u2026"), "long comments are truncated"
    assert len(peek_card["comments"][0]["text"]) <= SHEET_COMMENT_CHARS + 1
    assert peek_card["image"] is None, "no image unless the page offered one"

    # og:image, with a relative URL resolved against the article
    page = '''<meta property="og:image" content="/img/hero.png"><meta name="twitter:image" content="x.png">'''
    assert hero_image(page, "https://ex.test/a/b.html") == "https://ex.test/img/hero.png"
    assert hero_image("<p>no meta here</p>", "https://ex.test/") is None
    assert hero_image("", "") is None
    assert peek("short one") == "short one", "short comments are left alone"
    # the model's ceiling is separate from the sheet's, and far looser
    assert len(peek("w " * 3000, MODEL_COMMENT_CHARS)) <= MODEL_COMMENT_CHARS + 1
    assert peek("x " * 300, MODEL_COMMENT_CHARS) == "x " * 300, "a normal comment is untouched"
    long_thread = [{"by": "u", "text": "word " * 2000} for _ in range(MAX_COMMENTS)]
    sent = model_input("t", "", long_thread)
    assert len(sent) < MAX_COMMENTS * (MODEL_COMMENT_CHARS + 120), "worst-case prompt is bounded"
    assert not peek("word " * 200).rstrip("\u2026").endswith(" "), "no dangling space"
    assert " ".join(peek("alpha beta " * 90).rstrip("\u2026").split()[-1:]) in ("alpha", "beta"), (
        "must cut on a word boundary, never mid-word"
    )
    assert full["id"] == 7 and full["comment_count"] == 470

    thin = assemble_card(post, {"simple": "s", "substance": None, "camps": None}, 0)
    assert len(thin["depth"]) == 1, "unsupported substance leaves the glance alone, never a pad"
    assert not any("link" in d for d in thin["depth"]), "the link is a button, not a card"
    assert thin["camps"] is None and thin["terms"] == []

    # the model must never be able to set these
    for forbidden in ("id", "url", "comment_count", "hn"):
        assert forbidden not in SCHEMA["properties"], f"schema exposes {forbidden}"

    # Receipts. A fabricated claim has no real quote behind it.
    src = "The author made a catalogue of one hundred poster styles, with ready-to-paste prompts."
    assert unsupported_quotes(["a catalogue of one hundred poster styles"], src) == []
    # Normalising tolerates formatting, never facts.
    assert unsupported_quotes(["A CATALOGUE  of one-hundred!! poster styles"], src) == [], (
        "case, spacing and hyphenation are not changes to the quote"
    )
    assert unsupported_quotes(["a catalogue of two hundred poster styles"], src), (
        "a different number is a different claim and must be rejected"
    )
    assert unsupported_quotes(["chat context caused hallucinated filler text"], src), "fabrication"
    assert unsupported_quotes(["poster styles"], src), "too short to prove anything"

    good = {"simple": "s", "substance": "s", "support": ["catalogue of one hundred poster styles"]}
    assert verify_substance(good, src) == [] and good["substance"] == "s", "supported tier survives"

    faked = {"simple": "s", "substance": "invented", "support": ["context caused hallucinated text"]}
    assert verify_substance(faked, src), "must report the bad quote"
    assert faked["substance"] is None, "unsupported substance must be dropped"
    assert len(assemble_card({"id": 1, "url": None, "title": "t"}, faked, 0)["depth"]) == 1

    naked = {"simple": "s", "substance": "no receipts", "support": []}
    assert verify_substance(naked, src) == [] and naked["substance"] is None, "no quotes, no tier"

    # Real /interactions shape: a contentless thought step, then the answer.
    assert (
        output_text(
            {
                "status": "completed",
                "steps": [
                    {"type": "thought", "signature": "..."},
                    {"content": [{"text": '{"ok": true}'}]},
                ],
            }
        )
        == '{"ok": true}'
    ), "thought steps carry no content and must be skipped"
    assert output_text({"steps": [{"content": [{"text": "a"}, {"text": "b"}]}]}) == "b", "last wins"
    for bad in ({"nope": 1}, {"steps": [{"type": "thought", "signature": "x"}]}):
        try:
            output_text(bad)
        except RuntimeError as err:
            assert "no text block" in str(err)
        else:
            raise AssertionError(f"output_text should raise on {bad}")

    USAGE.update(calls=2, input=11_850, output=650, thought=1_760)
    line = usage_line()
    assert "2 calls" in line and "73%" in line, line  # thinking dominates output
    USAGE.update(calls=1)
    assert "1 call |" in usage_line(), "no stray plural"
    USAGE.update(calls=2)
    assert "$0.018" in line, line  # 11850*0.75 + 2410*3.75, per 1M
    USAGE.update(calls=0, input=0, output=0, thought=0)
    assert "$0.000" in usage_line(), "no calls must not divide by zero"

    assert PROMPT.exists(), "prompt.md is missing"
    assert "Absolute rule" in PROMPT.read_text(encoding="utf-8")

    print("all checks passed")


def dispatch() -> None:
    if "--check" in sys.argv:
        check()
    elif "--dry" in sys.argv:
        at = sys.argv.index("--dry")
        dry(int(sys.argv[at + 1]) if len(sys.argv) > at + 1 else 3)
    elif "--sample" in sys.argv:
        at = sys.argv.index("--sample")
        sample(int(sys.argv[at + 1]) if len(sys.argv) > at + 1 else 1)
    else:
        main()


if __name__ == "__main__":
    try:
        dispatch()
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        # A cron log should say "the network died", not print 40 lines of urllib.
        sys.exit(f"network error reaching a source: {err}")
