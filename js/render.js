// Rendering: cards, the caught-up boundary, day dividers, and loading older days.

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
  Object.assign(glossary, day.glossary);
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
