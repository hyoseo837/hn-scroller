// Bottom sheets: comments, glossary, calendar.

function openSheet(title, build) {
  // A button keeps focus after a click, so a later Enter would re-fire it.
  document.activeElement?.blur?.();
  sheet.textContent = "";
  sheet.append(el("h2", null, title));
  build(sheet);
  sheet.hidden = false;
  void sheet.offsetHeight; // reflow gives the transition a start state to animate from
  sheet.classList.add("open");
  scrim.classList.add("open");
}
function closeSheet() {
  sheet.classList.remove("open");
  scrim.classList.remove("open");
  setTimeout(() => {
    sheet.hidden = true;
  }, 240);
}
scrim.addEventListener("click", closeSheet);
// A bfcache restore replays the DOM exactly as it was, boot code included — so
// a sheet left open when you navigated away comes back open. Close it.
addEventListener("pageshow", (event) => {
  if (event.persisted && !sheet.hidden) closeSheet();
});

btnCmt.addEventListener("click", () => {
  const card = slides[post]?.card;
  openSheet(T.comments(card.comment_count), (box) => {
    // Translated comments are not what anyone wrote: say so, and the link below has the originals.
    if (card.comments?.some((c) => c.translated)) box.append(el("p", "note", T.translated));
    if (card.camps) {
      const callout = el("div", "camps");
      callout.append(el("div", "camps-label", T.split));
      callout.append(marked(card.camps, el("p")));
      box.append(callout);
    }
    // Verbatim and unprocessed, or translated. Top-level only — the tree is deliberately flattened.
    (card.comments || []).forEach((raw) => {
      const { by, text, translated } = typeof raw === "string" ? { by: "", text: raw } : raw;
      const row = el("article", "cmt");
      if (by) row.append(el("div", "who", by));
      const p = el("p", null, text);
      if (LANG !== "en" && !translated) p.lang = "en";
      row.append(p);
      box.append(row);
    });
    const more = el("a", null, T.thread);
    more.href = card.hn;
    more.target = "_blank";
    more.rel = "noopener";
    const row = el("div", "cmt");
    row.append(more);
    box.append(row);
  });
});

btnGlo.addEventListener("click", () => {
  const card = slides[post]?.card;
  openSheet(T.inThisPost, (box) => {
    const list = el("dl");
    card.terms.forEach((term) => {
      // One sentence is the glossary's limit; the word itself leads to more.
      const dt = el("dt");
      const more = el("a", null, term);
      more.href = "https://www.google.com/search?q=" + encodeURIComponent(term);
      more.target = "_blank";
      more.rel = "noopener";
      more.setAttribute("aria-label", T.search(term));
      dt.append(more);
      list.append(dt);
      list.append(el("dd", null, glossary[term] || T.noGloss));
    });
    box.append(list);
  });
});

// Calendar is pull, not push: no badge, nothing accumulating against you.
document.getElementById("cal").addEventListener("click", () => {
  openSheet(T.pastDays, (box) => {
    const wrap = el("div", "days");
    days.forEach((day) => {
      const a = el("a", day === date ? "now" : null, day);
      a.href = `?date=${day}`;
      wrap.append(a);
    });
    box.append(wrap);
  });
});
