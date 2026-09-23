"""Offline self-check. No network, no API key: `python3 -m generate --check`."""

from . import PROMPT
from .cards import (
    MODEL_COMMENT_CHARS,
    SCHEMA,
    SHEET_COMMENTS,
    assemble_card,
    model_input,
    unsupported_quotes,
    verify_substance,
)
from .hn import MAX_COMMENTS, select_posts
from .models import USAGE, luna_text, strict, usage_line
from .text import SHEET_COMMENT_CHARS, drop_boilerplate, hero_image, looks_gated, peek, strip_html


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
    # HN writes "/" as &#x2F;. Undecoded, it showed raw in 58 of 77 comment sheets
    # and failed a real quote the model had copied faithfully.
    assert strip_html("crashes&#x2F;hangs") == "crashes/hangs", "every entity decodes"
    thread = strip_html("<p>causing crashes&#x2F;hangs to really slow down the process</p>")
    assert unsupported_quotes(["causing crashes/hangs to really slow down the process"], thread) == []
    assert strip_html("use &lt;b&gt; for bold") == "use <b> for bold", "an escaped tag stays text"

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

    post = {"id": 7, "url": "https://x.test", "title": "Raw HN Title", "time": 1790000000}
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
    assert full["time"] == 1790000000, "the post's own date travels with the card"
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
    amp = '<meta property="og:image" content="https://ex.test/i?format=webp&amp;name=large">'
    assert hero_image(amp, "") == "https://ex.test/i?format=webp&name=large", "entities are decoded"
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

    # OpenAI /v1/responses: a textless reasoning item, then the message. No top-level
    # output_text over raw HTTP — that field is SDK-only.
    msg = {"type": "message", "content": [{"type": "output_text", "text": '{"ok": true}'}]}
    assert luna_text({"status": "completed", "output": [{"type": "reasoning", "summary": []}, msg]}) == '{"ok": true}'
    for bad in (
        {"status": "completed", "output": [{"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}]},
        {"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}, "output": [msg]},
        {"status": "completed", "output": [{"type": "reasoning"}]},
    ):
        try:
            luna_text(bad)
        except RuntimeError:
            pass
        else:
            raise AssertionError(f"luna_text should raise on {bad}")

    # Strict mode wants every object closed and fully required — on a copy, never ours.
    closed = strict(SCHEMA)
    assert closed["additionalProperties"] is False and "data" in closed["required"]
    assert closed["properties"]["terms"]["items"]["additionalProperties"] is False
    assert "additionalProperties" not in SCHEMA and "data" not in SCHEMA["required"], "ours untouched"

    USAGE.update(calls=2, input=11_850, output=650, thought=1_760)
    line = usage_line()
    assert "2 calls" in line and "73%" in line, line  # thinking dominates output
    USAGE.update(calls=1)
    assert "1 call |" in usage_line(), "no stray plural"
    USAGE.update(calls=2)
    assert "$0.002" in line, line  # 11850*0.10 + 2410*0.50, per 1M
    USAGE.update(calls=0, input=0, output=0, thought=0)
    assert "$0.000" in usage_line(), "no calls must not divide by zero"

    assert PROMPT.exists(), "prompt.md is missing"
    assert "Absolute rule" in PROMPT.read_text(encoding="utf-8")

    print("all checks passed")
