// Link previews for a shared card. A chat app's crawler runs no JS, so the preview
// tags in index.html can only ever describe the app. For a card link
// (`/?date=…&post=<id>[&lang=ko]`, what the share button sends) they are filled
// from that card on the way out. Every other request passes through untouched.
// Cloudflare Pages runs this for `/` only; the rest of the site stays static files.

const SITE = "https://hn.hyoseo.dev";
const plain = (text) => (text || "").replaceAll("**", "").trim(); // highlights are for the app
const clip = (text, n) => (text.length <= n ? text : `${text.slice(0, n - 1).trimEnd()}…`);

export async function onRequest({ request, next, env }) {
  const page = await next();
  const url = new URL(request.url);
  const date = url.searchParams.get("date") || "";
  const id = Number(url.searchParams.get("post"));
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !Number.isSafeInteger(id) || id <= 0) return page;

  // A missing day file comes back as index.html with a 200 (Pages' fallback), so a
  // parse failure is the "no such day" case, not an error.
  const read = async (path) => (await env.ASSETS.fetch(new URL(path, url))).json();
  const day = await read(`/data/${date}.json`).catch(() => null);
  const card = day?.cards?.find((c) => c.id === id);
  if (!card) return page;
  const ko = url.searchParams.get("lang") === "ko";
  const tr = ko ? (await read(`/data/${date}.ko.json`).catch(() => null))?.cards?.[id] : null;

  const tiers = Object.fromEntries((card.depth || []).map((tier) => [tier.tier, tier.text]));
  const simple = plain(tr?.simple || tiers.simple);
  // English previews lead with HN's own title; Korean has none, so its glance line leads.
  const title = clip(tr ? simple : card.title || simple, 90);
  const description = clip(plain(tr ? tr.substance : simple) || simple, 160);
  const tags = {
    description,
    "og:type": "article",
    "og:title": title,
    "og:description": description,
    "og:url": `${SITE}/?date=${date}&post=${id}${tr ? "&lang=ko" : ""}`,
    "og:locale": tr ? "ko_KR" : "en_US",
    "og:image": card.image || `${SITE}/icons/og-${tr ? "ko" : "en"}.png`,
    "og:image:alt": title,
  };
  return new HTMLRewriter()
    .on("title", { element: (el) => el.setInnerContent(`${title} · HN Scroller`) }) // escaped by default
    .on("meta", {
      element(el) {
        const key = el.getAttribute("property") || el.getAttribute("name");
        if (key in tags) el.setAttribute("content", tags[key]);
        // The declared size is the app image's; a story's own image has its own.
        else if (card.image && (key === "og:image:width" || key === "og:image:height")) el.remove();
      },
    })
    .transform(page);
}
