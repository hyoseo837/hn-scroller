"""The Korean pass: a finished English card, rewritten in Korean, then checked."""

import json
import re
from pathlib import Path

from .models import luna


PROMPT_KO = Path(__file__).resolve().parent / "prompt.ko.md"
# Korean companies read in Hangul; every other name stays as the source writes it.
# One missing here fails the name check, so its card ships English and the check
# names it: add it then. Measured 2026-09-23: 1 Korean name among 227 on 86 cards.
KOREAN_NAMES = {"Samsung": "삼성"}
# Measured on the same 10 cards: the user preferred medium's glance on 9 of 10, at
# $0.0013 a card against high's $0.0025. Low wrote list-like detail for $0.0006.
KO_EFFORT = "medium"
# Exactly the fields the Korean view replaces. No id, no names, no counts: the code owns those.
SCHEMA_KO = {
    "type": "object",
    "properties": {
        "simple": {"type": "string"},
        "substance": {"type": ["string", "null"]},
        "data": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
        "camps": {"type": ["string", "null"]},
        "glossary": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"term": {"type": "string"}, "gloss": {"type": "string"}},
                "required": ["term", "gloss"],
            },
        },
        # Last: the model writes in schema order, and glosses written after the comments
        # took on their register (~있어요) instead of noun endings.
        "comments": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["simple", "substance", "data", "camps", "glossary", "comments"],
}
# Digits with their separators: "1,000", "2.1", "5.5". Commas are dropped before
# comparing, so "1,000" and "1000" are the same number.
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")


def english(card: dict, glossary: dict) -> dict:
    """The card's English, flattened into exactly the fields the Korean pass writes."""
    tiers = {t["tier"]: t for t in card["depth"]}
    detail = tiers.get("substance") or {}
    return {
        "simple": tiers["simple"]["text"],
        "substance": detail.get("text"),
        "data": detail.get("data") or [],
        "camps": card.get("camps"),
        "glossary": [{"term": t, "gloss": glossary[t]} for t in card["terms"] if t in glossary],
        "comments": [c["text"] for c in card.get("comments") or []],
    }


def korean(card: dict, glossary: dict, effort: str) -> tuple[dict, dict]:
    """(English, Korean) for one card: one Luna call, unchecked.

    ponytail: one call per card. Batching a day was 3.7x cheaper per card on Flash,
    where re-sending the instructions cost more; unmeasured on Luna, whose input is
    $0.10/1M. Batch if the bill shows it — per card, one failure costs one card.
    """
    en = english(card, glossary)
    # The title is context, never translated; `names` is what must survive as written.
    given = {"title": card["title"], "names": card.get("entities") or [], **en}
    text = json.dumps(given, ensure_ascii=False, indent=1)
    return en, luna(PROMPT_KO.read_text(encoding="utf-8"), text, SCHEMA_KO, "korean", effort)


def lost(en: str | None, ko: str | None, names: list[str]) -> list[str]:
    """Numbers and names the English has and the Korean lost. Either one is a changed fact."""
    en, ko = en or "", ko or ""
    have = {n.replace(",", "") for n in NUMBER.findall(ko)}
    gone = [n for n in NUMBER.findall(en) if n.replace(",", "") not in have]
    return gone + [n for n in names if n in en and KOREAN_NAMES.get(n, n) not in ko]


def problems(en: dict, ko: dict, names: list[str]) -> list[str]:
    """Why this Korean card must not ship. Empty means it can. Comments are judged
    one by one in `comments_ko`, so an idiom in one reply cannot sink the card."""
    if (
        any((en[f] is None) != (ko[f] is None) for f in ("substance", "camps"))
        or len(ko["data"]) != len(en["data"])
        or len(ko["comments"]) != len(en["comments"])
    ):
        return ["the card's shape changed: a field, data row or comment appeared or went missing"]
    pairs = [(en[f], ko[f]) for f in ("simple", "substance", "camps")]
    pairs += [(" ".join(e), " ".join(k)) for e, k in zip(en["data"], ko["data"])]
    return [gone for e, k in pairs for gone in lost(e, k, names)]


def comments_ko(en: dict, ko: dict, names: list[str]) -> list:
    """Each comment's Korean, or None where it lost a number or a name: that one stays English."""
    return [None if lost(e, k, names) else k for e, k in zip(en["comments"], ko["comments"])]


def glosses(en: dict, ko: dict, names: list[str]) -> dict:
    """The Korean glosses that pass the same check; a failing one stays English."""
    written = {g["term"]: g["gloss"] for g in ko["glossary"]}
    return {
        g["term"]: written[g["term"]]
        for g in en["glossary"]
        if g["term"] in written and not lost(g["gloss"], written[g["term"]], names)
    }
