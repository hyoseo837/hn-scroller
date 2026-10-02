# Decisions — Content

## 2026-09-21 — Card facts come only from the source; definitions come only from the glossary

**Why:** the target user cannot tell a wrong number from a right one — that's why they're here — so every claim on a card must be checkable against the linked source. Background knowledge (what x.ai is) is unavoidable for de-jargoning but is quarantined in the reusable glossary, where one bad entry is fixable in one place instead of smeared across a day's cards.
**Rejected:** enrichment from model recall inside cards (dates, versions, benchmark scores); inventing a depth tier when the source has no substance for one — fewer cards beats a padded one.

## 2026-09-21 — Depth 2 requires verbatim source quotes, checked in code

**Why:** measured, not theorised. On the second live card the model invented "chat context caused hallucinated filler text to persist across later prompts" — absent from article and comments, and the one nearby comment said the opposite ("I can tell it's AI generated not from style, layout, or even hallucinations, but just the size"). The absolute rule was already in the prompt and did not hold. So the model now returns `support`: verbatim quotes, six words minimum, checked by normalised exact match; any miss drops `substance` and the card ships as 2 tiers. A fabricated claim has no real quote behind it, so it cannot pass.
**Rejected:** trusting the prompt (falsified above); checking only numbers (the fabrication contained none); rejecting the whole card (a shorter card is already specced as correct, and the headline was accurate); an LLM judge (a second model with the same weakness, at double the cost).
**Still unguarded:** `headline` and `camps` are prose with no mechanical check. Judge those by eye while tuning `prompt.md`.
