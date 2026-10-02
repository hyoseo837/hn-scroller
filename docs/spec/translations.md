# Translations

## Translations

- **Korean first**, as a separate pass over the finished English after each run: one Luna medium
  call per card with no Korean yet (~$0.0013). A failed card ships English and the next run retries it. Past days are
  backfilled once. Another language later is another overlay file, prompt and UI string table.
- `data/<date>.ko.json` overlays the day: `{"date", "cards": {"<id>": {"simple", "substance",
  "data", "camps", "comments"}}, "glossary": {...}}`. `data/glossary.ko.json` is the generator's store.
- Translated: glance, detail, data rows, camps, glosses, comments, UI. As written: HN title, term
  headwords, commenter names, code, URLs, and names, except Korean companies (Samsung → 삼성).
- **Register:** the app's own text reads as a tech headline: noun endings, compact Sino-Korean
  (환승시, 취약점), tech words Koreans write in English kept English. Comments keep their own voice.
- **Checked per card:** every number and name in the English survives, or the card ships English.
- Viewer: the browser language picks; an ENG/KOR choice beside the date overrides it (`localStorage`).
