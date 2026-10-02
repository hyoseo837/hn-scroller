# Decisions — Translations

## 2026-09-23 — Translations are a separate pass over the finished English, one overlay file per language per day

**Why:** the English detail is what was checked against quotes, and a failed pass costs no edition, only that card's Korean. An overlay keyed by card id leaves the English file, and every English reader's download, unchanged; a second language is another file. Every number and name must survive, per card, else English ships: a changed figure is the same failure as an invented one.
**Rejected:** Korean written in the main call (~free, but loses the English); translated fields inline in the day file (every reader downloads every language); Papago and other MT (they follow the English sentence, and the register is the product); Gemini Flash-Lite (wrote 오픈아이 for OpenAI, dropped Apache and Snap).

## 2026-09-23 — Korean register: a tech headline's; comments keep their commenter's voice

**Why:** the user's call, after reading Luna's Korean. The app's own lines end in nouns (~중, ~함) with a headline's compact Sino-Korean (환승시, 대기중, 취약점), and the tech words Korean developers write in English stay English (tool, glossary terms). Comments are people talking: turned into headlines they lose the sarcasm that is much of why the sheet gets opened. Whole-line prompt examples come from output the user approved.
**Rejected:** "-대" hearsay endings (the earlier "풀어버렸대" examples); plain native phrasing (갈아타면, 구멍: long and loose as a headline); noun endings for comments.

## 2026-09-23 — Names stay as the source writes them, except Korean companies

**Why:** the user's call. The reader meets these names in Latin letters in the title, the source line, the comments and a search, and exact spelling makes the name check mechanical. Korean companies read in Hangul (Samsung → 삼성) from a map in code. People's names are never transliterated: a romanized Korean name has several Hangul spellings, and a guessed one is a wrong fact.
**Rejected:** transliterating every name (구글, 오픈AI).

## 2026-09-23 — The Korean view translates comments too

**Why:** the user's call: a Korean reader wants the reactions, not only the camps line. Comments are ~1,550 characters a card against ~550 the model writes, so the pass's output roughly triples. The sheet says it is a translation and keeps the link to the originals on HN.
**Rejected:** English comments under a Korean camps line (cheaper, and verbatim).

## 2026-09-23 — Language: the browser's by default, a toggle to override, kept in `localStorage`

**Why:** many Korean developers run their phones in English, so the browser language alone would hide Korean from them. The toggle sits beside the date button; switching reloads, and resume restores the position. `localStorage` holds the resume position and the language.
**Rejected:** browser language only.

## 2026-09-23 — The Korean pass runs Luna at medium effort

**Why:** measured on the same 10 cards with the revised prompt: the user preferred medium's glance on 9 of 10, at $0.0013 a card and ~21 s against high's $0.0025 and ~36 s (~$1.25/mo against ~$2.40 at 32 cards a day). High also added a name its English did not mention. The effort level never fixed translationese: low, medium and high all wrote it under the first prompt, and the prompt's rewrite fixed it.
**Rejected:** high (twice the cost, and the user preferred medium's lines); low (list-like detail, and it dropped a "1:1" that failed the check, at $0.0006 a card).
