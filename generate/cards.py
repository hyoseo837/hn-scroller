"""What the model may write, what it is given, and how its answer is checked and assembled."""

import re

from .text import peek


SHEET_COMMENTS = 5  # how many go in the day file for the comment sheet
# Measured over 210 top-level comments: median 304, p99 1,490, max 1,600. At 2,000
# nothing real is touched — it exists so one pathological thread cannot become an
# unbounded prompt. Comments were the only input with no ceiling.
MODEL_COMMENT_CHARS = 2_000
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
        "time": post.get("time"),  # HN submission time, unix seconds
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


def day_glossary(cards: list[dict], glossary: dict) -> dict:
    """The glosses one day's cards use, shipped inside that day's file.

    The full glossary grows with every term ever written, and the viewer used to
    download all of it on every visit. glossary.json stays the generator's memory,
    so a known term keeps its gloss rather than being re-glossed each day.
    """
    return {term: glossary[term] for card in cards for term in card["terms"] if term in glossary}


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
