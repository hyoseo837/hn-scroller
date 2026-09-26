// Vertical touch: one swipe = one post, however hard. The browser's own glide can
// only be stopped by scroll-snap-stop, which cuts it off mid-flight and reads as
// the app cancelling your scroll. So vertical drags are driven here: the feed
// follows the finger, and on release glides to the next post, the previous one,
// or back. Horizontal swipes (depth) stay native.

let drag = null; // the touch being followed
let glide = 0; // rAF id of the running glide, 0 when idle
let base = 0; // the post a swipe moves one away from: where the last glide was headed

const FLICK = 0.3; // px/ms: faster than this, a short swipe still turns the page
const PULL = 0.2; // or dragged this share of the screen

function settle(target) {
  base = target;
  const from = feed.scrollTop;
  const to = target * feed.clientHeight;
  const start = performance.now();
  feed.classList.add("paging");
  const frame = (now) => {
    const t = Math.min(1, (now - start) / 320);
    feed.scrollTop = from + (to - from) * (1 - (1 - t) ** 3); // ease-out
    if (t < 1) {
      glide = requestAnimationFrame(frame);
    } else {
      glide = 0;
      feed.classList.remove("paging");
    }
  };
  glide = requestAnimationFrame(frame);
}

feed.addEventListener(
  "touchstart",
  (event) => {
    if (glide) cancelAnimationFrame(glide); // caught mid-glide: base stays its target
    else base = post;
    glide = 0;
    const t = event.touches[0];
    drag = event.touches.length > 1 ? null : { x: t.clientX, y: t.clientY, top: feed.scrollTop, axis: null, v: 0, at: event.timeStamp, lastY: t.clientY };
  },
  { passive: true },
);

feed.addEventListener(
  "touchmove",
  (event) => {
    if (!drag) return;
    const t = event.touches[0];
    const dy = t.clientY - drag.y;
    // Decided on the first move, as the browser does: later is too late to stop its scroll.
    if (!drag.axis) {
      drag.axis = Math.abs(dy) > Math.abs(t.clientX - drag.x) ? "y" : "x";
      if (drag.axis === "y" && feed.classList.contains("locked")) drag = null; // depth: swipe back first
    }
    if (drag?.axis !== "y") return;
    event.preventDefault();
    feed.classList.add("paging");
    // Never more than one post from base, however far the finger travels.
    const h = feed.clientHeight;
    feed.scrollTop = Math.max((base - 1) * h, Math.min(drag.top - dy, (base + 1) * h));
    const dt = event.timeStamp - drag.at;
    if (dt > 0) drag.v = 0.8 * ((t.clientY - drag.lastY) / dt) + 0.2 * drag.v;
    drag.at = event.timeStamp;
    drag.lastY = t.clientY;
  },
  { passive: false },
);

function release(event) {
  const vertical = drag?.axis === "y";
  const moved = vertical ? drag.lastY - drag.y : 0;
  const v = vertical && event.timeStamp - drag.at < 100 ? drag.v : 0; // held still before lifting: no flick
  drag = null;
  if (!vertical && !feed.classList.contains("paging")) return; // a tap or a depth swipe
  // Finger up (negative) = next post. A flick decides by speed, a slow drag by distance.
  const step = Math.abs(v) > FLICK ? -Math.sign(v) : Math.abs(moved) > PULL * feed.clientHeight ? -Math.sign(moved) : 0;
  settle(Math.max(0, Math.min(base + step, feed.children.length - 1)));
}
feed.addEventListener("touchend", release);
feed.addEventListener("touchcancel", release);
