// Where you are: header and dots, scroll and wheel navigation, the card you left, and your place across a language switch.

const posted = (unix) =>
  new Date(unix * 1000).toLocaleDateString(LOCALE, { month: "short", day: "numeric", year: "numeric" });

const short = (iso) => {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, d)).toLocaleDateString(LOCALE, {
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
  btnShare.disabled = !card;
  btnCmt.lastChild.textContent = card ? card.comment_count : "—";
  btnGlo.lastChild.textContent = terms;
  btnCmt.setAttribute("aria-label", card ? T.comments(card.comment_count) : T.commentsBtn);
  btnGlo.setAttribute("aria-label", T.terms(terms));
  // A dead vertical gesture with no visible cause reads as broken, so say so.
  // On a keyboard the vertical axis is never locked, so the hint differs.
  const deeper = tiersOf(card).length > 1;
  if (KEYBOARD) hint.textContent = deeper ? T.hintKeysDeep : T.hintKeys;
  else hint.textContent = depth > 0 ? T.hintBack : deeper ? T.hintMore : "";
  syncBack();
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
    if (post >= slides.length - 3) loadMore(); // older editions, below today
    clearTimeout(rememberTimer);
    rememberTimer = setTimeout(remember, 400);
    if (lastSeen && slides[post]?.card?.id === lastSeen.id) offerContinue(false); // got there by scrolling
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

// The feed opens at the top, the latest run first. The card you left is offered,
// not forced: new cards sit above it, and a forgotten date is a long scroll.
let lastSeen = null; // { date, id } of the last card viewed, from the previous visit
let rememberTimer;
function remember() {
  const slide = slides[post];
  if (!slide?.card) return;
  try {
    localStorage.setItem("lastSeen", JSON.stringify({ date: slide.date, id: slide.card.id }));
  } catch {
    /* blocked storage: no continue offer next time */
  }
}
const resume = document.getElementById("resume");
const resumeGo = document.getElementById("resume-go");
function offerContinue(on) {
  resume.hidden = !on;
  if (!on) lastSeen = null;
}
function offer(seen) {
  lastSeen = seen;
  resumeGo.textContent = T.continueFrom(short(seen.date));
  offerContinue(true);
}
function readLastSeen() {
  let seen = null;
  try {
    seen = JSON.parse(localStorage.getItem("lastSeen"));
  } catch {
    seen = null;
  }
  // Nothing to offer when the card left is the one on top.
  if (seen?.id && slides[0]?.card?.id !== seen.id) offer(seen);
}
// Before a jump away (a calendar pick), the card being read is the way back.
function offerHere() {
  const slide = slides[post];
  if (slide?.card) offer({ date: slide.date, id: slide.card.id });
}
resumeGo.addEventListener("click", () => {
  const want = lastSeen;
  offerContinue(false);
  jumpTo(want);
});
// There is one feed, today on top: a card (`id`) or a day's first card (no `id`) is
// reached the way scrolling would reach it, so newer days stay above it.
// ponytail: loads every day in between; a pick from months back means months of JSON.
// Load upward on demand instead if the calendar ever reaches that far back.
async function jumpTo(want) {
  const find = () =>
    slides.findIndex((slide) => (want.id ? slide.card?.id === want.id : slide.card && slide.date === want.date));
  // Older days load only on the way down: load them until the card's day is in.
  // A load in flight has already claimed its day, so wait for it before judging.
  while (find() < 0 && (loadingMore || (nextDay < days.length && days[nextDay] >= want.date))) await loadMore();
  const at = find();
  if (at < 0) return; // that day is gone from the index
  if (feed.children[post]) feed.children[post].scrollLeft = 0;
  feed.scrollTop = at * feed.clientHeight; // a jump, not a glide past every card between
}
document.getElementById("resume-x").addEventListener("click", () => offerContinue(false));

// Switching apps does not close the page: coming back finds it alive, on an old
// feed, and no load ever offers to continue. Save the card on the way out; on the
// way back, reload only if a new run has landed (runs go on top, so the top card
// changes). Otherwise the page is already where you left it.
async function checkForNewRun() {
  const newest = (await json("data/index.json").catch(() => []))[0];
  const day = newest && (await json(`data/${newest}.json`).catch(() => null));
  if (day?.cards?.length && day.cards[0].id !== slides[0]?.card?.id) location.reload();
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) remember();
  else checkForNewRun();
});
addEventListener("pageshow", (event) => event.persisted && checkForNewRun());

// A language switch reloads the page: it keeps your place for that one reload.
function save() {
  try {
    sessionStorage.setItem("at", String(post));
  } catch {
    /* blocked storage: the switch lands at the top, which is where a visit starts anyway */
  }
}
async function restore() {
  let at = null;
  try {
    at = sessionStorage.getItem("at");
    sessionStorage.removeItem("at");
  } catch {
    at = null;
  }
  // A shared card (`?date=…&post=<id>`) or a day (`?date=…`, an old calendar link):
  // go straight there. The address then goes back to the app's own, so a reload,
  // a language switch or a home-screen install does not land there again.
  const params = new URLSearchParams(location.search);
  const linked = { date: params.get("date") || "", id: Number(params.get("post")) || null };
  if (linked.date || linked.id) history.replaceState(null, "", location.pathname);
  if (at === null && days.includes(linked.date)) {
    syncChrome();
    if (!linked.id) readLastSeen(); // a day is a detour you may want to come back from
    return jumpTo(linked);
  }
  if (at === null) {
    // A fresh visit: open at the top, and offer the card left last time.
    at = 0;
    readLastSeen();
  }
  at = Number(at) || 0;
  // The place may be in an older day, which only loads on the way down.
  while (slides.length <= at && nextDay < days.length) await loadMore();
  post = Math.min(at, slides.length - 1);
  depth = 0;
  feed.scrollTop = post * feed.clientHeight;
  syncChrome();
}
