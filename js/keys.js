// Keyboard: whole cards per key, because mandatory snap defeats native arrow scrolling.

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
