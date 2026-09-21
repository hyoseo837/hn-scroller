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
MIN_POINTS = 100
WINDOW_DAYS = 3
CAP = 35
MAX_COMMENTS = 20
SHEET_COMMENTS = 5  # how many go in the day file for the comment sheet
SHEET_COMMENT_CHARS = 400
MAX_ARTICLE_CHARS = 24_000  # ~6k tokens
MIN_ARTICLE_CHARS = 500  # below this, fall back to title + comments
CALL_SPACING_S = 5  # free tier is 5-15 RPM; 35 posts ~= 3 min

ROOT = Path(__file__).parent
DATA = ROOT / "data"
PROMPT = ROOT / "prompt.md"

# The model may only write these. No id, no url, no counts — the code owns those.
SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
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
    "required": ["headline", "substance", "support", "camps", "terms", "entities"],
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
    text = _DROP_BLOCKS.sub(" ", html)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    for entity, char in _ENTITIES.items():
        text = text.replace(entity, char)
    return re.sub(r"\s+", " ", text).strip()


def select_posts(hits: list[dict], published: list, cap: int = CAP) -> list[dict]:
    """Points threshold does the filtering; the count floats with how busy the day was."""
    seen = {str(p) for p in published}
    keep = [h for h in hits if h["points"] >= MIN_POINTS and str(h["objectID"]) not in seen]
    keep.sort(key=lambda h: -h["points"])
    return keep[:cap]


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", re.sub(r"\s+", " ", text.lower())).strip()


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


def assemble_card(post: dict, content: dict, comment_count: int, comments: list[str] | None = None) -> dict:
    """Code owns the envelope. `content` carries only what the model wrote."""
    depth: list[dict] = [{"text": content["headline"]}]
    if content.get("substance"):
        tier = {"text": content["substance"]}
        if content.get("data"):
            tier["data"] = content["data"]
        depth.append(tier)
    depth.append({"link": True})

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
        "comments": [c[:SHEET_COMMENT_CHARS] for c in (comments or [])[:SHEET_COMMENTS]],
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
        "\nTOP-LEVEL COMMENTS:\n" + "\n".join(f"- {c}" for c in comments)
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
        strip_html(k["text"])
        for k in kids
        if k and k.get("text") and not k.get("dead") and not k.get("deleted")
    ]


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
    """Everything the model is allowed to see for one post."""
    item = hn_item(item_id)
    with ThreadPoolExecutor(max_workers=2) as pool:
        article_future = pool.submit(article_text, item)
        comments = top_comments(item)
        raw = article_future.result()
    article = raw if len(raw) >= MIN_ARTICLE_CHARS else ""  # too thin -> comments carry it
    return {
        "item": item,
        "article": article,
        "comments": comments,
        "source": article + "\n" + "\n".join(comments),  # what claims are checked against
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
    return json.loads(output_text(body))


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

    write_json(f"{date}.json", {"date": date, "cards": cards})
    write_json("glossary.json", glossary)
    write_json("published.json", published)
    write_json("index.json", sorted({date, *index}, reverse=True))
    print(f"wrote data/{date}.json ({len(cards)} cards)")


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
        )
        print(json.dumps(card, indent=2, ensure_ascii=False))
        # the card keeps only term names; show the glosses so they can be judged too
        for term in content.get("terms") or []:
            print(f"  glossary[{term['term']}] = {term['gloss']}")
        print()


# -------------------------------------------------------------------- check


def check() -> None:
    assert strip_html("<p>hi <b>there</b></p>") == "hi there"
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
        {"objectID": "2", "points": 99},  # under threshold
        {"objectID": "3", "points": 300},
        {"objectID": "4", "points": 800},  # already published
    ]
    picked = select_posts(hits, ["4"])
    assert [h["objectID"] for h in picked] == ["1", "3"], "filters, dedupes, sorts by points"
    assert len(select_posts(hits, [], cap=1)) == 1, "respects the cap"

    post = {"id": 7, "url": "https://x.test", "title": "Raw HN Title"}
    full = assemble_card(
        post,
        {
            "headline": "h",
            "substance": "s",
            "data": [["latency", "2.1s"]],
            "camps": "two camps",
            "terms": [{"term": "wasm", "gloss": "..."}],
            "entities": ["x.ai"],
        },
        470,
    )
    assert len(full["depth"]) == 3, "headline + substance + link"
    assert full["depth"][1]["data"] == [["latency", "2.1s"]]
    assert full["terms"] == ["wasm"], "card carries term names, glosses live in the glossary"
    assert full["comments"] == [], "no comments passed means no peek"
    peek = assemble_card(post, {"headline": "h"}, 9, ["x" * 999, "b", "c", "d", "e", "f"])
    assert len(peek["comments"]) == SHEET_COMMENTS, "sheet peek is capped"
    assert len(peek["comments"][0]) == SHEET_COMMENT_CHARS, "long comments are truncated"
    assert full["id"] == 7 and full["comment_count"] == 470

    thin = assemble_card(post, {"headline": "h", "substance": None, "camps": None}, 0)
    assert len(thin["depth"]) == 2, "no substance means a 2-card stack, never a padded one"
    assert thin["depth"][1]["link"] is True
    assert thin["camps"] is None and thin["terms"] == []

    # the model must never be able to set these
    for forbidden in ("id", "url", "comment_count", "hn"):
        assert forbidden not in SCHEMA["properties"], f"schema exposes {forbidden}"

    # Receipts. A fabricated claim has no real quote behind it.
    src = "The author made a catalogue of one hundred poster styles, with ready-to-paste prompts."
    assert unsupported_quotes(["a catalogue of one hundred poster styles"], src) == []
    assert unsupported_quotes(["A CATALOGUE  of one-hundred!! poster styles"], src) == [
        "A CATALOGUE  of one-hundred!! poster styles"
    ], "normalising must not let a changed number through"
    assert unsupported_quotes(["chat context caused hallucinated filler text"], src), "fabrication"
    assert unsupported_quotes(["poster styles"], src), "too short to prove anything"

    good = {"headline": "h", "substance": "s", "support": ["catalogue of one hundred poster styles"]}
    assert verify_substance(good, src) == [] and good["substance"] == "s", "supported tier survives"

    faked = {"headline": "h", "substance": "invented", "support": ["context caused hallucinated text"]}
    assert verify_substance(faked, src), "must report the bad quote"
    assert faked["substance"] is None, "unsupported substance must be dropped"
    assert len(assemble_card({"id": 1, "url": None, "title": "t"}, faked, 0)["depth"]) == 2

    naked = {"headline": "h", "substance": "no receipts", "support": []}
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
