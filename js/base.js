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
