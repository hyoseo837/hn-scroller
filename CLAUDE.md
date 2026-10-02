# hn-scroller

<!-- WHAT THIS IS: the contract between me and any AI agent working here.
     Read top to bottom before touching code. Keep it under 100 lines. -->

## Stack

No framework, no build step, zero dependencies. One Pages Function, `functions/index.js`, fills a shared card link's
preview; it runs only on Cloudflare, so test it on a preview branch with `curl`.

| Part | Choice |
|---|---|
| Viewer | Vanilla HTML/CSS/JS. `scroll-snap-type` gives the 2D card grid; vertical touch is paged by `js/swipe.js`, one post per swipe. |
| Generator | `generate/`, a Python package run as `python3 -m generate`; stdlib only (`urllib`), OpenAI Responses REST (no SDK). No `requirements.txt`. |
| Data | Static JSON per day in `data/`, plus `data/index.json` so the calendar knows which days exist. |
| Host + cron | Cloudflare Pages on `hn.hyoseo.dev` (domain already in Cloudflare); GitHub Actions every 6h commits the day's JSON, and the push triggers the deploy. Web Analytics beacon is hand-added at the end of `index.html`. |
| Client state | `localStorage`: language and the last card viewed. `sessionStorage` keeps the place through a language switch's reload. |

- `index.html` is markup only; styles in `app.css`, behaviour in `js/` (classic scripts, one scope, base first, boot last).
- PWA manifest for the home-screen icon. No service worker until offline reading is actually wanted.
- Scheduled Actions started 3-5 h late on the hour (six runs; now minute 37, unmeasured) and get
  **disabled on repos with no recent activity** (~60 days) — verify the bot's commits count, or the app dies.
- Pages serves the repo root, so `generate/`, prompt included, is public. Nothing secret is in it (`.env` is gitignored).

## Commands

```sh
python3 -m generate --check    # offline, no network, no API key. Run before every commit.
python3 -m generate --dry 3    # live HN fetch, prints the model input, calls nothing
python3 -m generate --sample 1 # one real Luna call, prints the card, writes nothing
python3 -m generate --sample-ko 3  # newest 3 cards in Korean beside the English; --ko DATE writes a day's Korean
python3 -m generate            # full run with the Korean pass, needs OPENAI_API_KEY
python3 -m http.server 8000     # then open localhost:8000 — file:// blocks fetch()
```

**A full run spends real money (~$0.0024/post on Luna high + $0.0013 for its Korean). Never run one to test a change — ask first.**
Verify with `--check` (free), `--dry` (free), then `--sample 1-3` or `--sample-ko 1-3` (under a cent). A full run happens
only when the user asks for fresh content, never as a way of checking your own work.

While tuning `generate/prompt.md`, `rm data/published.json` to let already-seen posts be
regenerated. The glossary survives; only the dedup list resets.

The system prompt is `generate/prompt.md` (`prompt.ko.md` for the Korean pass), read at runtime — edit it without touching code. Iterate with
`--dry` (free) before spending calls.

## Docs

Split by area so a task reads only its own. Never read a whole folder.

| Working on | Read |
|---|---|
| What a card may say, the generation prompt | `docs/spec/content.md`, `docs/decisions/content.md` |
| The viewer: gestures, feed, sheets, share | `docs/spec/viewer.md`, `docs/decisions/viewer.md` |
| Selection, fetching, the model call, day files | `docs/spec/pipeline.md`, `docs/decisions/pipeline.md` |
| The Korean pass, the language choice | `docs/spec/translations.md`, `docs/decisions/translations.md` |
| Docs rules, hosting, cost, analytics | `docs/decisions/project.md` |
| Visual design (the impeccable skill reads these from the root) | `PRODUCT.md`, `DESIGN.md` |
| Work with no code yet | `docs/DIRECTION.md` |

| Kind | Holds | Lifetime |
|---|---|---|
| `docs/spec/` | What we're building and why: scope, non-goals, data shapes. | Current truth. Overwrite freely. |
| `docs/decisions/` | Choices with a "why" that outlives the code. | Append-only. Never edit past entries. ≤5 lines each. |
| `docs/DIRECTION.md` | Work with no code yet: what, why, and the **trigger** that would start it. | Prune freely. An untouched entry is a dead one. |
| `PRODUCT.md`, `DESIGN.md` | Product truth and the visual system, for the design skill. | Current truth. |

Rules:

1. **Current truth beats history.** `CLAUDE.md` and `docs/spec/` describe now. Delete stale lines, don't annotate them.
2. **Append-only means append-only.** A new decision supersedes an old one; the old one stays. Format: `## YYYY-MM-DD — <decision>` then two lines: **Why** and **Rejected**.
3. **The code is the documentation for _how_.** Docs cover only what code can't say: intent, tradeoffs, things tried and abandoned.
4. **No doc for speculative work** — except `DIRECTION.md`, and only with a trigger. An entry
   with no condition that would start it is a wish, so delete it.
5. **Agent must read before writing.** Any non-trivial change reads its area's spec first. Any change that contradicts a decision stops and asks.
6. **Doc edits are part of the diff.** Change behavior contradicting a doc → update the doc in the same commit. No follow-up doc commits.
7. **Comments over docs for local logic.** A tricky function gets a comment, not a paragraph in a spec.
8. **A file that outgrows its area splits** into narrower areas, and the table above gains a row. No line caps but this file's.

## Size

`CLAUDE.md` is the only file loaded into every session: **100 lines**, a hard budget, not a target.

1. **At cap, cut — don't extend.** Cut order: (a) anything the code already says, (b) anything true of
   every project, (c) history and rationale (that's `docs/decisions/`), (d) examples beyond the first.
2. **One line per rule.** If a rule needs explaining, it's not a rule yet — it's a decision, so log it.
3. **Prose is capped too:** tables and lists over paragraphs, sentence fragments over sentences.

Anti-rules — don't create: `README` sections duplicating a spec, per-feature design docs, `ARCHITECTURE.md`, changelogs (git log is the changelog), TODO lists (a deferral in code is a `ponytail:` comment; a direction with no code is a `DIRECTION.md` entry with a trigger).

## Conventions

- Pull before touching `data/`: the bot pushes it at 00/06/12/18:37 UTC (possibly hours late) with a plain `git push`, and a push mid-run makes its push fail.
- Viewer checks: headless Chromium at `~/.cache/ms-playwright/chromium_headless_shell-1148/chrome-linux/headless_shell` (`--screenshot`, `--dump-dom`) over `python3 -m http.server`. It renders no frames, so smooth scroll never runs: dispatch `scroll` events by hand.
- Gestures: `chromium-1148/chrome-linux/chrome --headless=new` over CDP runs rAF and takes `Input.dispatchTouchEvent`. Feel is judged on the user's phone: push a branch, Pages previews it at `<branch>.hn-scroller.pages.dev`.
- Pages answers any missing path with `index.html` and a 200, so a missing script shows up as a syntax error, not a 404.
