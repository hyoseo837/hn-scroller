"""The three ways to run: full generation, --dry, --sample."""

import json
import os
import sys
from datetime import datetime, timezone

from . import DATA, ROOT
from .cards import assemble_card, day_glossary, model_input, verify_substance
from .hn import select_from_algolia, sources
from .models import luna_content, usage_line


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
    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set (put it in .env, or export it)")

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

            content = luna_content(item["title"], got["article"], got["comments"])
            bad = verify_substance(content, got["source"])
            if bad:
                print(f"    dropped substance, {len(bad)} quote(s) not in source")
            cards.append(
                assemble_card(
                    {"id": item["id"], "url": item.get("url"), "title": item["title"], "time": item.get("time")},
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

    if not cards:
        sys.exit("no cards generated — leaving yesterday's file in place")

    # Merge, never replace: a re-run on the same day (a retry after a crash, or a
    # second pass picking up what a guard cut) must not delete the earlier batch.
    # Existing first: each run takes the highest-scoring posts left, so the earlier
    # batch outranks this one. Prepending would put the weakest cards on top.
    existing = read_json(f"{date}.json", {}).get("cards", [])
    already = {c["id"] for c in existing}
    merged = existing + [c for c in cards if c["id"] not in already]
    write_json(f"{date}.json", {"date": date, "cards": merged, "glossary": day_glossary(merged, glossary)})
    if existing:
        print(f"merged: {len(existing)} already in today's file + {len(merged) - len(existing)} new")
    write_json("glossary.json", glossary)
    write_json("published.json", published)
    write_json("index.json", sorted({date, *index}, reverse=True))
    print(f"wrote data/{date}.json ({len(merged)} cards)")
    print(usage_line())


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


def sample(n: int) -> None:
    """Real model calls, assembled cards printed, nothing written and nothing
    marked published. The smallest thing that proves the whole chain: response
    shape, schema adherence, and whether the cards are any good."""
    load_env()
    if not os.environ.get("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY is not set (put it in .env, or export it)")

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

        content = luna_content(item["title"], got["article"], got["comments"])
        for quote in verify_substance(content, got["source"]):
            print(f"  UNSUPPORTED QUOTE, substance dropped: {quote!r}")
        card = assemble_card(
            {"id": item["id"], "url": item.get("url"), "title": item["title"], "time": item.get("time")},
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
