// Boot: load the index and today's edition, render it. Loaded last.

const json = async (path) => {
  const res = await fetch(path, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
};

(async () => {
  // Start from a known-closed sheet: bfcache and soft reloads can restore live
  // DOM state, and a sheet that is open before anything is rendered is nonsense.
  sheet.hidden = true;
  sheet.classList.remove("open");
  scrim.classList.remove("open");

  days = await json("data/index.json").catch(() => []);
  const wanted = new URLSearchParams(location.search).get("date");
  date = days.includes(wanted) ? wanted : days[0] || "";
  nextDay = days.indexOf(date) + 1;

  feed.textContent = "";
  slides = [];
  const day = date ? await json(`data/${date}.json`).catch(() => null) : null;
  await localize(day, date);
  // Each day file carries the glosses for its own terms, so a visit downloads one
  // day's worth, not every term ever written.
  Object.assign(glossary, day?.glossary);
  const cards = day?.cards ?? [];
  if (!cards.length) {
    feed.append(el("div", "empty", T.noCards(date || "today")));
    return;
  }

  cards.forEach((card, i) => push({ card, date, n: i + 1, of: cards.length }, renderCard(card)));
  todayCount = slides.length;

  restore();
  if (post >= slides.length - 3) loadMore(); // a short day may give no scroll to trigger it
})();
