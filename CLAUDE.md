# hn-scroller

<!-- WHAT THIS IS: the contract between me and any AI agent working here.
     Read top to bottom before touching code. Keep it under 100 lines. -->

## Stack

No framework, no build step, no server, zero dependencies.

| Part | Choice |
|---|---|
| Viewer | Vanilla HTML/CSS/JS. `scroll-snap-type` gives the 2D card grid natively. |
| Generator | One Python script, stdlib only (`urllib`), Gemini REST (no SDK). No `requirements.txt`. |
| Data | Static JSON per day in `data/`, plus `data/index.json` so the calendar knows which days exist. |
| Host + cron | GitHub Pages; GitHub Actions at 00:00 UTC commits the day's JSON. Host and cron are the same free thing. |
| Client state | `localStorage`, resume position only. |

- Inline CSS/JS in `index.html`; split out `app.js` past ~200 lines.
- PWA manifest for the home-screen icon. No service worker until offline reading is actually wanted.
- Scheduled Actions run 10-30 min late (harmless here) and get **disabled on repos with no recent
  activity** (~60 days) — verify the bot's own commits count, or the app silently dies in two months.

## Commands

```sh
python3 generate.py --check    # offline, no network, no API key. Run before every commit.
python3 generate.py --dry 3    # live HN fetch, prints the model input, calls nothing
python3 generate.py --sample 1 # one real Gemini call, prints the card, writes nothing
python3 generate.py            # full run, needs GEMINI_API_KEY
python3 -m http.server 8000     # then open localhost:8000 — file:// blocks fetch()
```

While tuning `prompt.md`, `rm data/published.json` to let already-seen posts be
regenerated. The glossary survives; only the dedup list resets.

The system prompt is `prompt.md`, read at runtime — edit it without touching code. Iterate with
`--dry` (free) before spending calls.

## Documentation rule

Three files. No others. If a doc doesn't fit one of these, it doesn't exist.

| File | Holds | Lifetime | Cap | Loaded |
|---|---|---|---|---|
| `CLAUDE.md` | How to work here: stack, commands, conventions, invariants. | Current truth. Overwrite freely. | **100 lines** | every session |
| `docs/SPEC.md` | What we're building and why. Scope, non-goals, data shapes. | Current truth. Overwrite freely. | **200 lines** | on demand |
| `docs/DECISIONS.md` | Choices with a "why" that outlives the code. | Append-only. Never edit past entries. | **5 lines/entry** | on demand |

Rules:

1. **Current truth beats history.** `CLAUDE.md` and `SPEC.md` describe now. Delete stale lines, don't annotate them.
2. **Append-only means append-only.** New `DECISIONS.md` entry supersedes an old one; the old one stays. Format: `## YYYY-MM-DD — <decision>` then two lines: **Why** and **Rejected**.
3. **The code is the documentation for _how_.** Docs cover only what code can't say: intent, tradeoffs, things tried and abandoned.
4. **No doc for speculative work.** Write it when the work starts, not when it's imagined.
5. **Agent must read before writing.** Any non-trivial change reads `SPEC.md` first. Any change that contradicts a decision stops and asks.
6. **Doc edits are part of the diff.** Change behavior contradicting a doc → update the doc in the same commit. No follow-up doc commits.
7. **Comments over docs for local logic.** A tricky function gets a comment, not a paragraph in `SPEC.md`.

## Size

`CLAUDE.md` is the only file loaded into every session. Every line in it is rent paid on all future
context windows. Treat the cap as a hard budget, not a target.

1. **At cap, cut — don't extend.** Hitting a cap means something in the file has earned deletion, not
   that the cap is wrong. Raise a cap only by editing this line and saying why in `DECISIONS.md`.
2. **Cut order when over:** (a) anything the code already says, (b) anything true of every project
   (`use git`, `write tests`), (c) history and rationale — that's `DECISIONS.md`'s job, (d) examples
   beyond the first, (e) prose restating the line above it.
3. **One line per rule.** No rule gets a supporting paragraph. If a rule needs explaining, it's not a
   rule yet — it's a decision, so log it.
4. **`DECISIONS.md` grows forever, and that's fine** — it's never auto-loaded. Read specific entries
   by grep, never the whole file. Cap is per entry: heading + `Why` + `Rejected`, nothing else.
5. **No file over 200 lines, ever.** Past that, split by shipping less, not by adding a fourth file.
6. **Prose is capped too:** tables and lists over paragraphs, sentence fragments over sentences.

Check before committing a doc change:

```sh
wc -l CLAUDE.md docs/*.md   # 100 / 200 / 200
```

Anti-rules — don't create: `README` sections duplicating `SPEC.md`, per-feature design docs, `ARCHITECTURE.md`, a `docs/` tree, changelogs (git log is the changelog), TODO files (issues or `ponytail:` comments instead).

## Conventions

TBD after first code lands.
