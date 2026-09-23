// Language: the browser's by default, the <select> beside the date to override it.
// A translation arrives per day as an overlay (data/<date>.<code>.json) laid over the English.

const langPick = document.getElementById("lang");
const LANGS = [...langPick.options].map((option) => option.value);
const LANG = (() => {
  try {
    const saved = localStorage.getItem("lang");
    if (LANGS.includes(saved)) return saved;
  } catch {
    /* blocked storage: the browser's language still works, the choice will not stick */
  }
  const browser = navigator.language?.toLowerCase().split("-")[0];
  return LANGS.includes(browser) ? browser : "en";
})();
document.documentElement.lang = LANG;
// English keeps the browser's own date format, as before; others ask for their own.
const LOCALE = LANG === "en" ? undefined : LANG;

const T = {
  en: {
    loading: "Loading…",
    language: "Language",
    pastDays: "Past days",
    noCards: (when) => `No cards for ${when}. Run python3 -m generate.`,
    detail: "Detail",
    readOn: (site) => `Read it on ${site} →`,
    openHN: "Open the discussion on HN →",
    caughtUp: "You're caught up.",
    dayCount: (n, when) => `${n} from ${when}.`,
    keepGoing: (older) => `keep going for ${older} ↓`,
    comments: (n) => `${n} comments`,
    commentsBtn: "Comments",
    terms: (n) => `${n} terms explained`,
    split: "The split",
    thread: "Read the full thread on HN →",
    translated: "",
    inThisPost: "In this post",
    search: (term) => `Search Google for ${term}`,
    noGloss: "No definition yet.",
    hintKeysDeep: "← → depth · ↑ ↓ posts",
    hintKeys: "↑ ↓ posts",
    hintBack: "← swipe back to continue",
    hintMore: "swipe → for more",
  },
  // The app's own voice in Korean: short, noun endings (SPEC "Translations").
  ko: {
    loading: "불러오는 중…",
    language: "언어",
    pastDays: "지난 날짜",
    noCards: (when) => `${when} 카드 없음`,
    detail: "자세히",
    readOn: (site) => `${site}에서 원문 보기 →`,
    openHN: "HN에서 토론 보기 →",
    caughtUp: "오늘은 여기까지",
    dayCount: (n, when) => `${when} 소식 ${n}개`,
    keepGoing: (older) => `${older} 소식 계속 ↓`,
    comments: (n) => `댓글 ${n}개`,
    commentsBtn: "댓글",
    terms: (n) => `용어 설명 ${n}개`,
    split: "의견 대립",
    thread: "HN에서 전체 스레드 보기 →",
    translated: "댓글은 자동 번역, 원문은 HN에서",
    inThisPost: "이 글의 용어",
    search: (term) => `Google에서 ${term} 검색`,
    noGloss: "아직 설명 없음",
    hintKeysDeep: "← → 자세히 · ↑ ↓ 다음 글",
    hintKeys: "↑ ↓ 다음 글",
    hintBack: "← 밀어서 돌아가기",
    hintMore: "밀어서 더 보기 →",
  },
}[LANG];

// Lay one day's translation over its English, in place. A card or comment with no
// translation keeps its English and stays unmarked, so it can be tagged lang="en".
async function localize(day, when) {
  if (LANG === "en" || !day?.cards) return;
  // An untranslated day 404s, or on Pages gets index.html with a 200 and fails
  // to parse. Either way the day stays English.
  const tr = await json(`data/${when}.${LANG}.json`).catch(() => null);
  if (!tr?.cards) return;
  for (const card of day.cards) {
    const k = tr.cards[card.id];
    if (!k) continue;
    card.translated = true;
    for (const tier of card.depth || []) {
      if (tier.tier === "simple") tier.text = k.simple;
      if (tier.tier === "substance" && k.substance) {
        tier.text = k.substance;
        if (tier.data) tier.data = k.data;
      }
    }
    card.camps = k.camps;
    (card.comments || []).forEach((comment, i) => {
      if (typeof comment === "object" && k.comments?.[i]) {
        comment.text = k.comments[i];
        comment.translated = true;
      }
    });
  }
  day.glossary = { ...day.glossary, ...tr.glossary };
}

langPick.value = LANG;
langPick.setAttribute("aria-label", T.language);
langPick.addEventListener("change", () => {
  save(); // keep today's place: the scroll save is debounced and a reload would drop it
  try {
    localStorage.setItem("lang", langPick.value);
  } catch {
    langPick.value = LANG; // nowhere to keep the choice, so a reload would only land back here
    return;
  }
  location.reload();
});
document.getElementById("cal").setAttribute("aria-label", T.pastDays);
document.querySelector("#feed .empty").textContent = T.loading;
