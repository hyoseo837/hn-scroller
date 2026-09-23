# hn-scroller

Hacker News as a vertical swipe feed, for people who want to know what happened in tech today
without reading forty comment threads to find out.

**[hn.hyoseo.dev](https://hn.hyoseo.dev)**

It is an *awareness* tool, not a learning tool. Open it without thinking, know what is going on,
close it. A day has a bottom and you reach it in about two minutes.

## How it reads

Two axes, both plain CSS scroll-snap — no framework, no gesture library.

- **Swipe up** for the next story. Each card is one plain sentence: *"someone found a way to make
  ChatGPT stop producing horrible event posters"*. No jargon, no version numbers.
- **Swipe right** for the detail — the names, figures and argument the glance line leaves out.
- Buttons for the discussion, a glossary of the jargon in that post, and the original article.

## How it is built

A Python script picks every Hacker News story above 200 points from the last three days that it has
not already covered, asks Gemini for the card text, and writes one JSON file per day. GitHub Actions
runs it every 6 hours and commits the result; the commit is what deploys the site.

No server, no database, no build step, and no dependencies — Python stdlib and vanilla JS. About
**$0.31 a day**, and that does not change with traffic, because readers fetch a static file.

The part that took the most care is keeping it honest. Cards state facts only from the fetched
source, never from the model's own knowledge, and the detail tier must return verbatim quotes that
the code checks by exact match — a claim with no real quote behind it is dropped rather than shipped.
That guard exists because an early test produced a fluent, entirely invented technical claim, and
the target reader is precisely the person who could not catch it.

## Running it

```sh
python3 -m generate --check      # offline self-check, no API key
python3 -m generate --dry 3      # live fetch, prints the model input, calls nothing
python3 -m generate --sample 1   # one real call, prints the card, writes nothing
python3 -m http.server 8000      # then open localhost:8000
```

A full run needs `GEMINI_API_KEY` in `.env`, costs real money, and is not how you test a change —
`--check`, `--dry` and `--sample` are. The system prompt is [`generate/prompt.md`](generate/prompt.md), read at
runtime, so wording changes need no code edit.

## Docs

Six files, deliberately, each with a line cap:

| | |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | how to work in this repo — stack, commands, conventions |
| [`docs/SPEC.md`](docs/SPEC.md) | what is being built and why — scope, non-goals, data shapes |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | append-only rationale, including the calls that were wrong first |
| [`docs/DIRECTION.md`](docs/DIRECTION.md) | work with no code yet, each with the trigger that would start it |
| [`PRODUCT.md`](PRODUCT.md) | product truth for the design skill — users, purpose, constraints |
| [`DESIGN.md`](DESIGN.md) | the visual system — type, palette, tokens, as shipped |