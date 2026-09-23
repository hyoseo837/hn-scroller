"""Selection and fetching: Algolia, the HN Firebase API, and the article page."""

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from .text import drop_boilerplate, hero_image, looks_gated, strip_html


MIN_POINTS = 150  # measured over 14 days: a median of 32 stories/day clear this, range 22-43
WINDOW_DAYS = 3
MAX_COMMENTS = 20
MAX_ARTICLE_CHARS = 24_000  # ~6k tokens
MIN_ARTICLE_CHARS = 500  # below this, fall back to title + comments


def select_posts(hits: list[dict], published: list) -> list[dict]:
    """Everything above the threshold that has not been published. No cap.

    Hacker News caps this by itself: a median of 32 stories/day clear 150 points,
    43 on the busiest day measured. A cap here would silently drop real news on a big day,
    which is the failure an awareness app cannot afford.

    The threshold doubles as the maturity test: a post at 150 points has proven
    itself whether that took six hours or two days, so there is no age delay —
    holding back a story that broke overnight is the worse failure for an
    awareness app. The 3-day window catches late risers, and `published` means
    a post is generated once, ever.
    """
    seen = {str(p) for p in published}
    keep = [h for h in hits if h["points"] >= MIN_POINTS and str(h["objectID"]) not in seen]
    keep.sort(key=lambda h: -h["points"])
    return keep


def _get(url: str, timeout: int = 15, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers=headers or {"user-agent": "hn-scroller/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read()


def select_from_algolia(published: list) -> list[dict]:
    since = int(time.time()) - WINDOW_DAYS * 86_400
    query = urllib.parse.urlencode(
        {
            "tags": "story",
            # >=, not >: select_posts lets a post exactly at the bar in, so the query must too.
            "numericFilters": f"created_at_i>{since},points>={MIN_POINTS}",
            # Newest first and no paging, so a short page silently drops the oldest
            # qualifiers, the late risers the window exists for. At 150 the 3-day
            # window held 84; 1000 is Algolia's page maximum.
            "hitsPerPage": "1000",
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
