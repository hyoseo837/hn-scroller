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
  syncBack();
}
function closeSheet() {
  sheet.classList.remove("open");
  scrim.classList.remove("open");
  syncBack();
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

// Swipe down closes a sheet, from its top: the sheet follows the finger, and on
// release closes on a flick or a long enough pull, or springs back. Mid-list, a
// swipe down is the sheet's own scroll. FLICK and PULL are js/swipe.js's.
let pull = null; // the touch dragging the sheet down
sheet.addEventListener(
  "touchstart",
  (event) => {
    const t = event.touches[0];
    pull = event.touches.length > 1 || sheet.scrollTop > 0 ? null : { y: t.clientY, dy: 0, v: 0, at: event.timeStamp, on: false };
  },
  { passive: true },
);
sheet.addEventListener(
  "touchmove",
  (event) => {
    if (!pull) return;
    const t = event.touches[0];
    const dy = t.clientY - pull.y;
    if (!pull.on && dy <= 0) {
      pull = null; // up first: scrolling the sheet
      return;
    }
    pull.on = true;
    event.preventDefault();
    const dt = event.timeStamp - pull.at;
    if (dt > 0) pull.v = 0.8 * ((dy - pull.dy) / dt) + 0.2 * pull.v;
    pull.at = event.timeStamp;
    pull.dy = dy;
    sheet.style.transition = "none";
    sheet.style.transform = `translateY(${Math.max(0, dy)}px)`;
  },
  { passive: false },
);
function letGo(event) {
  const done = pull?.on && (pull.v > FLICK && event.timeStamp - pull.at < 100 || pull.dy > PULL * sheet.offsetHeight);
  if (pull?.on) sheet.style.transition = sheet.style.transform = ""; // the CSS transition takes it from here
  pull = null;
  if (done) closeSheet();
}
sheet.addEventListener("touchend", letGo);
sheet.addEventListener("touchcancel", letGo);

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
// One month at a time, so a year of editions still fits the sheet. Days are UTC dates.
document.getElementById("cal").addEventListener("click", () => {
  const reading = slides[post]?.date || date; // below today's cards, that is an older day
  const have = new Set(days);
  const months = [...new Set(days.map((day) => day.slice(0, 7)))]; // newest first, like `days`
  let shown = Math.max(0, months.indexOf(reading.slice(0, 7)));
  openSheet(T.pastDays, (box) => {
    if (!months.length) return;
    const head = el("div", "month");
    const older = el("button", null, "‹");
    const newer = el("button", null, "›");
    const label = el("span");
    older.setAttribute("aria-label", T.olderMonth);
    newer.setAttribute("aria-label", T.newerMonth);
    older.addEventListener("click", () => draw(shown + 1));
    newer.addEventListener("click", () => draw(shown - 1));
    head.append(older, label, newer);
    const grid = el("div", "days");
    box.append(head, grid);

    function draw(at) {
      shown = at;
      const [y, m] = months[at].split("-").map(Number);
      label.textContent = new Date(Date.UTC(y, m - 1)).toLocaleDateString(LOCALE, {
        year: "numeric", month: "long", timeZone: "UTC",
      });
      older.disabled = at >= months.length - 1;
      newer.disabled = at <= 0;
      grid.textContent = "";
      for (let i = 0; i < 7; i++) {
        // 2026-01-04 is a Sunday: the grid starts its weeks there.
        const name = new Date(Date.UTC(2026, 0, 4 + i)).toLocaleDateString(LOCALE, { weekday: "narrow", timeZone: "UTC" });
        grid.append(el("span", "wd", name));
      }
      for (let i = new Date(Date.UTC(y, m - 1, 1)).getUTCDay(); i > 0; i--) grid.append(el("span"));
      const count = new Date(Date.UTC(y, m, 0)).getUTCDate();
      for (let d = 1; d <= count; d++) {
        const iso = `${months[at]}-${String(d).padStart(2, "0")}`;
        if (!have.has(iso)) {
          grid.append(el("span", "off", d)); // no edition that day
          continue;
        }
        const a = el("a", iso === reading ? "now" : null, d);
        a.href = `?date=${iso}`; // a real link still works; a tap jumps in place
        a.addEventListener("click", (event) => {
          event.preventDefault();
          closeSheet();
          if (iso !== reading) offerHere(); // a detour you may want to come back from
          jumpTo({ date: iso });
        });
        a.setAttribute("aria-label", pretty(iso));
        grid.append(a);
      }
    }
    draw(shown);
  });
});
