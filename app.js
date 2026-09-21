// Viewer. Vertical = next post, horizontal = depth. State is three integers over
// a static JSON file: which post, which depth, and where you stopped today.

const feed = document.getElementById("feed");
const dots = document.getElementById("dots");
const sheet = document.getElementById("sheet");
const scrim = document.getElementById("scrim");
const btnCmt = document.getElementById("btn-cmt");
const btnGlo = document.getElementById("btn-glo");
const hint = document.getElementById("hint");

let cards = [];
let glossary = {};
let days = [];
let date = "";
let post = 0; // which post
let depth = 0; // how deep in it

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};
const host = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "news.ycombinator.com";
  }
};

// ------------------------------------------------------------------ render

function renderCard(card) {
  const section = el("section", "post");

  card.depth.forEach((tier, i) => {
    const wrap = el("article", "card");
    if (tier.link) {
      const box = el("div", "src");
      box.append(el("span", "host", card.url ? host(card.url) : "discussion on Hacker News"));
      if (card.url) {
        const a = el("a", null, "Read the original →");
        a.href = card.url;
        a.target = "_blank";
        a.rel = "noopener";
        box.append(a, el("div", null, " "));
      }
      const hn = el("a", null, `All ${card.comment_count} comments on HN →`);
      hn.href = card.hn;
      hn.target = "_blank";
      hn.rel = "noopener";
      box.append(hn);
      wrap.append(box);
    } else {
      if (i > 0) wrap.append(el("div", "kicker", "Detail"));
      wrap.append(el("p", i === 0 ? "headline" : "substance", tier.text));
      if (tier.data?.length) {
        const table = el("div", "data");
        for (const [label, value] of tier.data) {
          const row = el("div");
          row.append(el("span", null, label), el("span", null, value));
          table.append(row);
        }
        wrap.append(table);
      }
    }
    section.append(wrap);
  });

  // depth is never remembered: leaving a post resets it
  section.addEventListener("scroll", onDepthScroll, { passive: true });
  return section;
}

function renderEnd() {
  const section = el("section", "post");
  const wrap = el("article", "card end");
  wrap.append(el("h1", null, "You're caught up."));
  wrap.append(el("p", null, `${cards.length} from ${date}. Nothing else to read.`));
  section.append(wrap);
  return section;
}

function render() {
  feed.textContent = "";
  if (!cards.length) {
    feed.append(el("div", "empty", `No cards for ${date || "today"}. Run generate.py.`));
    return;
  }
  cards.forEach((card) => feed.append(renderCard(card)));
  feed.append(renderEnd());
}

// ------------------------------------------------------------------- state

function syncChrome() {
  const card = cards[post];
  document.getElementById("date").textContent = date || "—";

  dots.textContent = "";
  if (card) {
    card.depth.forEach((_, i) => {
      const dot = el("i");
      if (i === depth) dot.classList.add("on");
      dots.append(dot);
    });
  }

  const terms = card?.terms?.length ?? 0;
  btnCmt.disabled = !card || (!card.comments?.length && !card.camps);
  btnGlo.disabled = !terms;
  btnCmt.textContent = card ? `💬 ${card.comment_count}` : "💬 —";
  btnGlo.textContent = `📖 ${terms}`;
  // A dead vertical gesture with no visible cause reads as broken, so say so.
  hint.textContent = depth > 0 ? "← swipe back to continue" : card?.depth.length > 1 ? "swipe → for more" : "";
}

// Depth locks the vertical axis (SPEC: swipe left before swipe up).
function lockVertical(on) {
  if (feed.classList.contains("locked") === on) return;
  const y = feed.scrollTop;
  feed.classList.toggle("locked", on);
  feed.scrollTop = y; // toggling overflow can reset it
}

function onDepthScroll(event) {
  const section = event.currentTarget;
  if (section !== feed.children[post]) return;
  const next = Math.round(section.scrollLeft / section.clientWidth);
  lockVertical(section.scrollLeft > 4);
  if (next !== depth) {
    depth = next;
    syncChrome();
  }
}

let saveTimer;
feed.addEventListener(
  "scroll",
  () => {
    const next = Math.round(feed.scrollTop / feed.clientHeight);
    if (next === post) return;
    const left = feed.children[post];
    if (left) left.scrollLeft = 0; // next post always opens at depth 1
    post = next;
    depth = 0;
    syncChrome();
    clearTimeout(saveTimer);
    saveTimer = setTimeout(save, 400);
  },
  { passive: true },
);

// Resume is per-device and only ever within one day — a day has a bottom, so
// there is no backlog to feel guilty about.
const key = () => `pos:${date}`;
function save() {
  try {
    localStorage.setItem(key(), String(post));
  } catch {
    /* private window, blocked storage — resume is a convenience, not state */
  }
}
function restore() {
  let at = 0;
  try {
    at = Number(localStorage.getItem(key())) || 0;
  } catch {
    at = 0;
  }
  post = Math.min(at, feed.children.length - 1);
  depth = 0;
  feed.scrollTop = post * feed.clientHeight;
  syncChrome();
}

// ------------------------------------------------------------------- sheet

function openSheet(title, build) {
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

btnCmt.addEventListener("click", () => {
  const card = cards[post];
  openSheet(`${card.comment_count} comments`, (box) => {
    if (card.camps) box.append(el("p", null, card.camps));
    // Verbatim and unprocessed. Top-level only — the tree is deliberately flattened.
    (card.comments || []).forEach((text) => box.append(el("div", "cmt", text)));
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
  const card = cards[post];
  openSheet("In this post", (box) => {
    const list = el("dl");
    card.terms.forEach((term) => {
      list.append(el("dt", null, term));
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

// --------------------------------------------------------------------- boot

const json = async (path) => {
  const res = await fetch(path, { cache: "no-cache" });
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json();
};

(async () => {
  days = await json("data/index.json").catch(() => []);
  glossary = await json("data/glossary.json").catch(() => ({}));
  const wanted = new URLSearchParams(location.search).get("date");
  date = days.includes(wanted) ? wanted : days[0] || "";
  if (date) {
    const day = await json(`data/${date}.json`).catch(() => null);
    cards = day?.cards ?? [];
  }
  render();
  restore();
})();
