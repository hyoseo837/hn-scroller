// Where you are: header and dots, scroll and wheel navigation, and keeping your place across a language switch.

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

// No resume: the feed opens at the top, the latest run first, and you scroll down
// until you meet what you read before. The one exception is a language switch,
// which reloads the page: it keeps your place for that one reload.
function save() {
  try {
    sessionStorage.setItem("at", String(Math.min(post, Math.max(0, todayCount - 1))));
  } catch {
    /* blocked storage: the switch lands at the top, which is where a visit starts anyway */
  }
}
function restore() {
  let at = 0;
  try {
    at = Number(sessionStorage.getItem("at")) || 0;
    sessionStorage.removeItem("at");
  } catch {
    at = 0;
  }
  post = Math.min(at, Math.max(0, todayCount - 1));
  depth = 0;
  feed.scrollTop = post * feed.clientHeight;
  syncChrome();
}
