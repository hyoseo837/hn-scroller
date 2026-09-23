// Viewer. Vertical = next post, horizontal = depth. State is three integers over
// a static JSON file: which post, which depth, and where you stopped today.

const feed = document.getElementById("feed");
const dots = document.getElementById("dots");
const sheet = document.getElementById("sheet");
const scrim = document.getElementById("scrim");
const btnCmt = document.getElementById("btn-cmt");
const btnGlo = document.getElementById("btn-glo");
const hint = document.getElementById("hint");

// feed.children and `slides` are parallel: a slide is a card, a day divider, or
// the caught-up marker. Day dividers mean the index is no longer a card index.
let slides = [];
let glossary = {};
let days = [];
let date = "";        // the newest day, the one resume belongs to
let todayCount = 0;   // slides belonging to `date`, so resume never points past it
let loadingMore = false;
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

// The link tier used to be a final card. It is a link now, not a destination —
// on the glance card's source line; older day files still carry it, hence the filter.
const tiersOf = (card) => (card?.depth || []).filter((tier) => !tier.link);

// No image? A colour from the post id. Deterministic, so a card looks the same
// every visit.
const hueOf = (id) => (Number(id) * 47) % 360;

const SVG = "http://www.w3.org/2000/svg";
const icon = (id) => {
  const svg = document.createElementNS(SVG, "svg");
  svg.setAttribute("class", "ico");
  svg.setAttribute("aria-hidden", "true");
  const use = document.createElementNS(SVG, "use");
  use.setAttribute("href", `#i-${id}`);
  svg.append(use);
  return svg;
};

// Self posts have no external url — the discussion is the article.
const sourceOf = (card) => card.url || card.hn;

const host = (url) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "news.ycombinator.com";
  }
};

// ------------------------------------------------------------------ render

// Narrower than this and an image is a logo or an icon, not a picture. Measured
// 2026-09-22: every image under it was 80-280px wide, and three were site logos.
const MIN_IMAGE_PX = 300;

// No usable image: the glance card gets a clipping — the original HN title as a
// newspaper headline where the image would be, over a glow in the post's colour.
// Called at render, or later when an image fails or is too small.
function cover(wrap, card) {
  wrap.querySelectorAll(".pic, .glow").forEach((node) => node.remove());
  const hue = hueOf(card.id);
  wrap.style.setProperty("--hue", hue);
  const glow = el("div", "glow");
  glow.style.background = `radial-gradient(70% 50% at 35% 35%, hsl(${hue} 80% 62%), transparent),
    radial-gradient(60% 45% at 75% 55%, hsl(${(hue + 50) % 360} 80% 62%), transparent)`;
  const pic = el("div", "pic");
  const clip = el("div", "clip");
  clip.style.setProperty("--tilt", `${((hue % 5) - 2) * 0.6}deg`); // a hand-cut look, stable per post
  clip.append(el("div", "mast", card.url ? host(card.url) : "Hacker News"));
  // Older day files predate `title`; the glance line, unmarked, stands in.
  clip.append(el("h2", null, card.title || (tiersOf(card)[0]?.text || "").replaceAll("**", "")));
  pic.append(clip);
  wrap.prepend(glow, pic);
  if (wrap.parentElement === feed.children[post]) syncChrome();
}

function renderCard(card) {
  const section = el("section", "post");

  tiersOf(card).forEach((tier, i) => {
    const wrap = el("article", "card");
    // `tier` names the layer; older cards without it fall back to position.
    const kind = tier.tier || (i === 0 ? "simple" : "substance");
    if (kind === "substance") wrap.append(el("div", "kicker", "Detail"));
    wrap.append(marked(tier.text, el("p", kind)));
    // Where it came from is context a beginner needs: a personal blog and a
    // vendor announcement read very differently. It is also the way out to the
    // article — the only one on a card whose detail tier failed verification.
    if (i === 0) {
      const from = el("a", "from", card.url ? host(card.url) : "Hacker News");
      from.href = sourceOf(card);
      from.target = "_blank";
      from.rel = "noopener";
      from.append(icon("out"));
      const meta = el("div", "meta");
      meta.append(from);
      // When it was posted, not when we picked it up: the 3-day window means
      // an edition can carry a story from two days back.
      if (card.time) meta.append(el("span", "sep", "|"), el("span", "when", posted(card.time)));
      wrap.append(meta);
    }
    if (i === 0) {
      wrap.classList.add("glance");
      if (card.image) {
        const pic = el("div", "pic");
        const glow = el("img", "glow"); // same URL, so the browser fetches it once
        glow.alt = "";
        glow.loading = "lazy";
        glow.src = card.image;
        const img = el("img", "shot");
        img.alt = "";
        img.loading = "lazy";
        // A dead hotlink, or a favicon-sized logo that would only blur when
        // scaled up, is no picture at all.
        img.addEventListener("error", () => cover(wrap, card));
        img.addEventListener("load", () => img.naturalWidth < MIN_IMAGE_PX && cover(wrap, card));
        img.src = card.image;
        pic.append(img);
        wrap.prepend(glow, pic);
      } else {
        cover(wrap, card);
      }
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
    // Having just read the detail, "read the whole thing" is the next move —
    // so the link sits where that thought happens, not only in the button bar.
    if (kind === "substance") {
      const more = el("a", "readon", card.url ? `Read it on ${host(card.url)} →` : "Open the discussion on HN →");
      more.href = sourceOf(card);
      more.target = "_blank";
      more.rel = "noopener";
      wrap.append(more);
    }
    section.append(wrap);
  });

  // depth is never remembered: leaving a post resets it
  section.addEventListener("scroll", onDepthScroll, { passive: true });
  return section;
}

// A boundary, not a dead end. Reaching it means you are done with today; older
// days sit below only if you choose to keep going, so nothing is ever a backlog.
function renderBoundary(count, when, older) {
  const section = el("section", "post");
  const wrap = el("article", "card end");
  wrap.append(el("h1", null, "You're caught up."));
  wrap.append(el("p", null, `${count} from ${when}.`));
  if (older) wrap.append(el("p", "older", `keep going for ${older} ↓`));
  section.append(wrap);
  return section;
}

function renderDivider(when) {
  const section = el("section", "post");
  const wrap = el("article", "card end");
  wrap.append(el("h1", null, when));
  section.append(wrap);
  return section;
}

const pretty = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(undefined, {
    weekday: "long", month: "long", day: "numeric", timeZone: "UTC",
  });
};

function push(slide, node) {
  slides.push(slide);
  feed.append(node);
}

// Append one older day below what is already there. Returns false when that day
// has nothing, so the caller can stop asking.
async function appendDay(when) {
  const day = await json(`data/${when}.json`).catch(() => null);
  if (!day?.cards?.length) return false;
  // The caught-up card already names the next day ("keep going for …"), so a
  // divider straight after it would be two cards between the same two dates.
  if (!slides.at(-1)?.boundary) push({ divider: true, date: when }, renderDivider(pretty(when)));
  day.cards.forEach((card, i) => push({ card, date: when, n: i + 1, of: day.cards.length }, renderCard(card)));
  return true;
}

let nextDay = 1; // index into `days` of the next older edition to load

async function loadMore() {
  if (loadingMore || nextDay >= days.length) return;
  loadingMore = true;
  try {
    while (nextDay < days.length && !(await appendDay(days[nextDay++]))) {
      /* skip empty days */
    }
  } finally {
    loadingMore = false;
  }
}

// ------------------------------------------------------------------- state

const posted = (unix) =>
  new Date(unix * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

const short = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(undefined, {
    weekday: "short", month: "short", day: "numeric", timeZone: "UTC",
  });
};

function syncChrome() {
  const slide = slides[post];
  const card = slide?.card;
  const when = slide?.date || date;
  document.getElementById("date").textContent = when ? short(when) : "—";
  // Where you are in the day, not what is left unread: a day has a bottom.
  document.getElementById("pos").textContent = card ? `${slide.n}/${slide.of}` : "";

  dots.textContent = "";
  if (card) {
    tiersOf(card).forEach((_, i) => {
      const dot = el("i");
      if (i === depth) dot.classList.add("on");
      dots.append(dot);
    });
  }

  const onGlow = depth === 0 && Boolean(feed.children[post]?.querySelector(".glow"));
  document.querySelector(".phone").classList.toggle("on-glow", onGlow);

  const terms = card?.terms?.length ?? 0;
  btnCmt.disabled = !card || (!card.comments?.length && !card.camps);
  btnGlo.disabled = !terms;
  btnCmt.lastChild.textContent = card ? card.comment_count : "—";
  btnGlo.lastChild.textContent = terms;
  btnCmt.setAttribute("aria-label", card ? `${card.comment_count} comments` : "Comments");
  btnGlo.setAttribute("aria-label", `${terms} terms explained`);
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
    if (post >= slides.length - 3) loadMore(); // older editions, below the boundary
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
  const last = Math.max(0, tiersOf(slides[post]?.card).length - 1);
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
  o: () => slides[post]?.card && window.open(sourceOf(slides[post].card), "_blank", "noopener"),
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
    // Resume belongs to today only. Scrolling into older editions is a detour,
    // not progress — a day has a bottom, and that is what makes it feel light.
    localStorage.setItem(key(), String(Math.min(post, Math.max(0, todayCount - 1))));
  } catch {
    /* private window, blocked storage — resume is a convenience, not state */
  }
}
function restore() {
  let at = 0;
  // A day picked from the calendar opens at its first card: that is a choice to
  // read that day, not to resume it.
  if (!new URLSearchParams(location.search).has("date")) {
    try {
      at = Number(localStorage.getItem(key())) || 0;
    } catch {
      at = 0;
    }
  }
  post = Math.min(at, Math.max(0, todayCount - 1));
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
  nextDay = days.indexOf(date) + 1;

  feed.textContent = "";
  slides = [];
  const day = date ? await json(`data/${date}.json`).catch(() => null) : null;
  const cards = day?.cards ?? [];
  if (!cards.length) {
    feed.append(el("div", "empty", `No cards for ${date || "today"}. Run python3 -m generate.`));
    return;
  }

  cards.forEach((card, i) => push({ card, date, n: i + 1, of: cards.length }, renderCard(card)));
  const older = nextDay < days.length ? pretty(days[nextDay]) : null;
  push({ boundary: true, date }, renderBoundary(cards.length, pretty(date), older));
  todayCount = slides.length;

  restore();
})();
