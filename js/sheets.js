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
  openSheet(`${card.comment_count} comments`, (box) => {
    if (card.camps) {
      const callout = el("div", "camps");
      callout.append(el("div", "camps-label", "The split"));
      callout.append(marked(card.camps, el("p")));
      box.append(callout);
    }
    // Verbatim and unprocessed. Top-level only — the tree is deliberately flattened.
    (card.comments || []).forEach((raw) => {
      const { by, text } = typeof raw === "string" ? { by: "", text: raw } : raw;
      const row = el("article", "cmt");
      if (by) row.append(el("div", "who", by));
      row.append(el("p", null, text));
      box.append(row);
    });
    const more = el("a", null, "Read the full thread on HN →");
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
  openSheet("In this post", (box) => {
    const list = el("dl");
    card.terms.forEach((term) => {
      // One sentence is the glossary's limit; the word itself leads to more.
      const dt = el("dt");
      const more = el("a", null, term);
      more.href = "https://www.google.com/search?q=" + encodeURIComponent(term);
      more.target = "_blank";
      more.rel = "noopener";
      more.setAttribute("aria-label", `Search Google for ${term}`);
      dt.append(more);
      list.append(dt);
      list.append(el("dd", null, glossary[term] || "No definition yet."));
    });
    box.append(list);
  });
});

// Calendar is pull, not push: no badge, nothing accumulating against you.
document.getElementById("cal").addEventListener("click", () => {
  openSheet("Past days", (box) => {
    const wrap = el("div", "days");
    days.forEach((day) => {
      const a = el("a", day === date ? "now" : null, day);
      a.href = `?date=${day}`;
      wrap.append(a);
    });
    box.append(wrap);
  });
});
