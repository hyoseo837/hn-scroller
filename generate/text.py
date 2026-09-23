"""HTML to text, site chrome and paywall detection, the hero image, comment trimming."""

import re
import urllib.parse
from html import unescape


SHEET_COMMENT_CHARS = 400
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


def peek(text: str, limit: int = SHEET_COMMENT_CHARS) -> str:
    """Trim a comment without slicing through a word."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    space = cut.rfind(" ")
    return (cut[:space] if space > 0 else cut).rstrip(" ,;:.\u2014-") + "\u2026"


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
        # Attribute values are HTML-escaped: `&amp;` left in the URL 404s.
        url = urllib.parse.urljoin(base_url or "", unescape(found.group(1).strip()))
        if url.startswith(("http://", "https://")):
            return url
    return None
