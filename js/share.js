// Share: a link that opens on this card. functions/index.js fills that link's preview
// with the story, in Korean when the card was read in Korean. The native share sheet
// on a phone; where there is none (most desktops), the link goes to the clipboard.

btnShare.addEventListener("click", async () => {
  const card = slides[post]?.card;
  if (!card) return;
  const lang = LANG === "ko" && card.translated ? "&lang=ko" : ""; // a Korean preview needs its Korean
  const url = `${location.origin}/?date=${slides[post].date}&post=${card.id}${lang}`;
  const text = (tiersOf(card)[0]?.text || "").replaceAll("**", "");
  if (navigator.share) {
    try {
      await navigator.share({ title: card.title, text, url });
      return;
    } catch (err) {
      if (err.name === "AbortError") return; // the reader closed the sheet
    }
  }
  try {
    await navigator.clipboard.writeText(url);
  } catch {
    prompt(T.share, url); // no clipboard (an old in-app browser): show it to copy by hand
    return;
  }
  hint.textContent = T.copied;
  setTimeout(syncChrome, 1800);
});
