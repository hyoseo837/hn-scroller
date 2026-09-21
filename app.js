// Viewer. Vertical = next post, horizontal = depth. State is three integers over
// a static JSON file: which post, which depth, and where you stopped today.

const feed = document.getElementById("feed");
const dots = document.getElementById("dots");
const sheet = document.getElementById("sheet");
const scrim = document.getElementById("scrim");
const btnCmt = document.getElementById("btn-cmt");
const btnGlo = document.getElementById("btn-glo");
const btnSrc = document.getElementById("btn-src");
const hint = document.getElementById("hint");

let cards = [];
let glossary = {};
let days = [];
let date = "";
// A real pointer means a keyboard is likely: hints and the depth lock differ.
const KEYBOARD = matchMedia("(hover: hover) and (pointer: fine)").matches;

let post = 0; // which post
let depth = 0; // how deep in it

const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};
// Render **key words** as highlights. Split-and-append with text nodes — never
// innerHTML: this text comes from a model and sits beside raw comment text.
const marked = (text, node) => {
  (text || "").split(/\*\*(.+?)\*\*/g).forEach((part, i) => {
    if (!part) return;
    node.append(i % 2 ? el("strong", null, part) : part);
  });
  return node;
};

// The link tier used to be a final card. It is an action now, not a destination,
// so it lives in the button bar; older day files still carry it, hence the filter.
const tiersOf = (card) => (card?.depth || []).filter((tier) => !tier.link);

// No image? Derive a field from the post id. Deterministic, so a card looks the
// same every visit, and dark enough that the caption stays legible over it.
const tint = (id) => {
  const hue = (Number(id) * 47) % 360;
  return `linear-gradient(155deg, hsl(${hue} 48% 30%), hsl(${(hue + 55) % 360} 55% 12%))`;
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

  tiersOf(card).forEach((tier, i) => {
    const wrap = el("article", "card");
    // `tier` names the layer; older cards without it fall back to position.
    const kind = tier.tier || (i === 0 ? "headline" : "substance");
    if (kind === "substance") wrap.append(el("div", "kicker", "Detail"));
    wrap.append(marked(tier.text, el("p", kind)));
    // Where it came from is context a beginner needs: a personal blog and a
    // vendor announcement read very differently.
    if (i === 0) wrap.append(el("div", "from", card.url ? host(card.url) : "Hacker News"));
    if (i === 0) {
      wrap.classList.add("glance");
      const field = el("div", "field");
      if (card.image) {
        const img = el("img");
        img.src = card.image;
        img.alt = "";
        img.loading = "lazy";
        // A dead hotlink falls back to the gradient rather than a white hole.
        img.addEventListener("error", () => {
          img.remove();
          field.style.background = tint(card.id);
        });
        field.append(img);
      } else {
        field.style.background = tint(card.id);
      }
      wrap.prepend(el("div", "scrim"));
      wrap.prepend(el("div", "frost"));
      wrap.prepend(field);
    }
    if (tier.data?.length) {
      const table = el("div", "data");
      for (const [label, value] of tier.data) {
        const row = el("div");
        row.append(el("span", null, label), el("span", null, value));
        table.append(row);
      }
      wrap.append(table);
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
    tiersOf(card).forEach((_, i) => {
      const dot = el("i");
      if (i === depth) dot.classList.add("on");
      dots.append(dot);
    });
  }

  // The chrome flips to light while it sits over a glance card's visual field.
  document.querySelector(".phone").classList.toggle("on-visual", depth === 0 && Boolean(card));

  const terms = card?.terms?.length ?? 0;
  btnCmt.disabled = !card || (!card.comments?.length && !card.camps);
  btnGlo.disabled = !terms;
  btnSrc.disabled = !card;
  btnSrc.title = card?.url ? `Read the original on ${host(card.url)}` : "Open the discussion on HN";
  btnCmt.textContent = card ? `💬 ${card.comment_count}` : "💬 —";
  btnGlo.textContent = `📖 ${terms}`;
  // A dead vertical gesture with no visible cause reads as broken, so say so.
  // On a keyboard the vertical axis is never locked, so the hint differs.
  const deeper = tiersOf(card).length > 1;
  if (KEYBOARD) hint.textContent = deeper ? "← → depth · ↑ ↓ posts" : "↑ ↓ posts";
  else hint.textContent = depth > 0 ? "← swipe back to continue" : deeper ? "swipe → for more" : "";
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

// One wheel gesture = one card. Mandatory snap turns a small delta into a
// snap-back, and trackpad momentum fires dozens of events per flick, so the
// cooldown is what stops a single swipe from flying past ten posts.
let wheelUntil = 0;
feed.addEventListener(
  "wheel",
  (event) => {
    if (!sheet.hidden) return;
    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return; // horizontal intent
    event.preventDefault();
    const now = Date.now();
    if (now < wheelUntil || Math.abs(event.deltaY) < 6) return;
    wheelUntil = now + 420;
    goToPost(post + (event.deltaY > 0 ? 1 : -1));
  },
  { passive: false },
);

// ---------------------------------------------------------------- keyboard

// Native arrow scrolling is useless here: mandatory snap drags the small
// increment straight back, so the key looks ignored. Move whole cards instead.
function goToPost(next) {
  next = Math.max(0, Math.min(next, feed.children.length - 1));
  const target = feed.children[next];
  if (!target || next === post) return;
  const current = feed.children[post];
  if (current) current.scrollLeft = 0; // depth is never remembered
  lockVertical(false); // a keypress is never an ambiguous diagonal
  target.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
}

function goToDepth(next) {
  const section = feed.children[post];
  if (!section) return;
  const last = Math.max(0, tiersOf(cards[post]).length - 1);
  next = Math.max(0, Math.min(next, last));
  section.scrollTo({ left: next * section.clientWidth, behavior: "smooth" });
}

const KEYS = {
  ArrowDown: () => goToPost(post + 1),
  ArrowUp: () => goToPost(post - 1),
  PageDown: () => goToPost(post + 1),
  PageUp: () => goToPost(post - 1),
  " ": () => goToPost(post + 1),
  j: () => goToPost(post + 1),
  k: () => goToPost(post - 1),
  ArrowRight: () => goToDepth(depth + 1),
  ArrowLeft: () => goToDepth(depth - 1),
  l: () => goToDepth(depth + 1),
  h: () => goToDepth(depth - 1),
  c: () => !btnCmt.disabled && btnCmt.click(),
  g: () => !btnGlo.disabled && btnGlo.click(),
  o: () => !btnSrc.disabled && btnSrc.click(),
};

document.addEventListener("keydown", (event) => {
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (!sheet.hidden) {
    // Let arrows scroll the open sheet; only Escape is ours.
    if (event.key === "Escape") {
      event.preventDefault();
      closeSheet();
    }
    return;
  }
  const act = KEYS[event.key];
  if (!act) return;
  event.preventDefault(); // stop Space and arrows scrolling the page instead
  act();
});

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
  const card = cards[post];
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

// Self posts have no external url — the discussion is the article.
btnSrc.addEventListener("click", () => {
  const card = cards[post];
  if (card) window.open(card.url || card.hn, "_blank", "noopener");
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
  // Start from a known-closed sheet: bfcache and soft reloads can restore live
  // DOM state, and a sheet that is open before anything is rendered is nonsense.
  sheet.hidden = true;
  sheet.classList.remove("open");
  scrim.classList.remove("open");

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
