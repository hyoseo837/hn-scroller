// The back button. Installed on a home screen the app has no page history of its
// own, so Android's back closed it outright, even from an open sheet or a detail
// card. While there is something to back out of, one history entry sits on top
// for back to use up: a sheet closes first, then depth returns to the glance.
// With nothing open, back leaves as before.

let guarded = false; // our entry is on top of history
let leaving = false; // our own history.back() is still in flight

function syncBack() {
  if (sheet.classList.contains("open") || depth > 0) {
    if (guarded) return;
    guarded = true;
    // Mid-flight, the pop below re-adds it: pushing now would land under the pop.
    if (!leaving) history.pushState({ guard: true }, "");
  } else if (guarded) {
    // Closed from inside the app (scrim, Escape, a swipe): take the entry back
    // off, or the next real back press would appear to do nothing.
    guarded = false;
    leaving = true;
    history.back();
  }
}

addEventListener("popstate", () => {
  if (leaving) {
    leaving = false;
    if (guarded) history.pushState({ guard: true }, ""); // reopened while the pop was in flight
    return;
  }
  if (!guarded) return; // not ours: an ordinary navigation
  guarded = false; // the user's back used it up; undo one level
  if (sheet.classList.contains("open")) closeSheet();
  else if (depth > 0) goToDepth(0);
});
