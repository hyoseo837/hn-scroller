---
name: HN Scroller
description: Hacker News as a light, readable swipe feed. Readability first.
colors:
  paper: "#fbfaf8"
  ink: "#16161a"
  dim: "#6b6b76"
  line: "#e2e0da"
  sheet: "#ffffff"
  outside: "#d9d7d1"
  hn-orange: "#ff6600"
  link-light: "#b34700"
  mark: "rgba(255, 138, 51, .42)"
  tint: "rgba(255, 102, 0, .07)"
  paper-dark: "#0f0f10"
  ink-dark: "#f2f1ee"
  dim-dark: "#9a9aa4"
  line-dark: "#2a2a2e"
  sheet-dark: "#17171a"
  clipping-paper: "#fbf9f3"
  clipping-ink: "#141414"
  masthead: "#5a5a5a"
  black: "#000"
  shadow-image: "rgba(0, 0, 0, .18)"
  shadow-clipping: "rgba(0, 0, 0, .2)"
  shadow-frame: "rgba(0, 0, 0, .34)"
  frame-edge: "rgba(0, 0, 0, .06)"
typography:
  glance:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "clamp(25px, 6.5vw, 32px)"
    fontWeight: 680
    lineHeight: 1.2
    letterSpacing: "-0.022em"
  glance-desktop:
    fontSize: "29px"
    fontWeight: 680
    lineHeight: 1.2
    letterSpacing: "-0.022em"
  body:
    fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "16px"
    lineHeight: 1.62
  comment:
    fontSize: "14.5px"
    lineHeight: 1.62
  meta:
    fontSize: "13px"
  hint:
    fontSize: "12px"
  label:
    fontSize: "11px"
    fontWeight: 700
    letterSpacing: ".1em"
  clipping-headline:
    fontFamily: "Georgia, Times New Roman, Noto Serif, serif"
    fontSize: "25px"
    fontWeight: 700
    lineHeight: 1.14
rounded:
  clipping: "2px"
  focus: "4px"
  day-chip: "8px"
  callout: "10px"
  image: "12px"
  sheet: "18px"
  frame: "30px"
  pill: "999px"
spacing:
  card-x: "36px"
  card-top: "84px"
  card-bottom: "132px"
  glance-bottom: "92px"
  chrome-x: "20px"
components:
  action-button:
    backgroundColor: "{colors.sheet}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "44px"
    padding: "0 15px"
  clipping:
    backgroundColor: "{colors.clipping-paper}"
    textColor: "{colors.clipping-ink}"
    rounded: "{rounded.clipping}"
    padding: "16px 20px 22px"
  camps-callout:
    backgroundColor: "{colors.tint}"
    rounded: "{rounded.callout}"
    padding: "13px 15px"
---

# Design

Derived from the shipped viewer (`index.html`, `app.js`) on 2026-09-23. Current truth: when the CSS
changes, this file changes in the same commit. No sidecar file — the doc rule caps files at six.

## Overview

**North star: the morning paper, one story at a time.** A phone-shaped column that shows one
sentence per screen, in plain words, for someone reading lightly. The type is the design;
everything else gets out of its way.

- Readability outranks everything, including atmosphere. When a visual idea costs line length or
  contrast, the idea loses (a Reels-style side rail was rejected for exactly that).
- Confirmed by the user and kept: the fonts, the glance text size, the orange marker highlight,
  the phone frame on desktop.
- One rhythm: every glance card is the same plain card in the current theme. Images and clippings
  sit *on* it as objects; nothing turns a card dark or light on its own.

## Colors

| Role | Light | Dark | Use |
|---|---|---|---|
| paper / ink | `#fbfaf8` / `#16161a` | `#0f0f10` / `#f2f1ee` | card background and text |
| dim | `#6b6b76` | `#9a9aa4` | meta, hints, labels |
| line | `#e2e0da` | `#2a2a2e` | rules, inactive dots, button borders |
| hn-orange | `#ff6600` | same | fills only: active dot, focus ring, day-chip border |
| link | `#b34700` | `#ff6600` | orange *text*: links, "The split" label |
| mark | orange .42 | orange .34 | marker highlight under key words |

- HN orange is 2.8:1 on the light paper, so it never carries text in light mode. `--link` is 5.3:1.
- Glance glow: a blurred copy of the card's image, or for clipping cards two radial gradients in a
  hue derived from the post id (`id * 47 mod 360`). Deterministic: a card looks the same every visit.

## Typography

- One family, `system-ui`. The only other face is Georgia, and only inside a newspaper clipping.
- Scale: glance 25–32px (29px in the desktop frame) → body 16px → comments 14.5px → meta 13px →
  hint 12px → labels 11px uppercase. Nothing smaller.
- Key words are marked `**like this**` and render as a marker highlight (bottom 42% of the line
  box), never bold-inside-bold. Rendered with text nodes, never `innerHTML`.
- The glance line is lowercase with no full stop, by content rule (`docs/SPEC.md`).

## Layout

- Frame: 390×844 centred column on desktop (≥481px wide), full-bleed on a phone.
- Vertical scroll-snap = next post; horizontal = depth. `scroll-snap-stop: always` on both, so a
  flick moves exactly one card.
- Card padding 84 / 36 / 132px; the glance card's bottom is 92px so the sentence sits low, just clear
  of the buttons. Chrome (header, buttons) sits at 20px from the edge, text at 36px.
- Header: name · date (opens calendar) · position `3/24` · depth dots. Transparent over a glow.
- Buttons: comments and glossary bottom-right, where a right thumb rests; the hint sits left.
- Glance card, top to bottom: image or clipping (fills the space above the text, centred) → the
  sentence → `source ↗ | Sep 20, 2026`.

## Elevation & Depth

- Flat cards. Depth comes from objects on them: images `0 8px 28px rgba(0,0,0,.18)`, clippings
  `0 10px 30px rgba(0,0,0,.2)`, the desktop frame `0 24px 70px rgba(0,0,0,.34)`.
- Glow layer: `blur(48px) saturate(1.4)`, opacity .7, scaled 1.25, masked to fade out from 50% to
  82% of the card height so the caption sits on plain paper.
- Sheets rise from the bottom over a 45% black scrim.

## Shapes

- Images 12px radius; clippings nearly square (2px) and tilted between −1.2° and +1.2° per post.
- Pills for actions, 8px chips for days, 10px for the camps callout, 18px sheet top corners.
- No coloured side borders on callouts; emphasis is the tint and the label.

## Components

- **Image**: shown whole, never cropped (`max-width/max-height: 100%`). Under 300px wide, or failing
  to load, it is dropped and the card gets a clipping instead.
- **Clipping**: off-white paper, masthead (site name, 10.5px spaced caps) over a double rule, then
  the original HN title in Georgia. Paper and ink stay the same in dark mode — it is an object.
- **Action button**: 44px tall pill, SVG icon (18px, 1.8 stroke, round caps) + tabular count.
- **Icons**: one inline SVG sprite in `index.html`, one stroke weight. No emoji, no glyph icons.
- **Camps callout**: tint background, "The split" label in `--link`, then the line.
- **Caught-up card**: the only card between two days; it names the next day.

## Do's and Don'ts

- Do keep a text column at full width; put controls where they cost no line length.
- Do test both themes and a phone-width frame (390px) for every change.
- Don't crop an image to fill a frame, stretch a small one, or fake one.
- Don't use HN orange as light-mode text; use `--link`.
- Don't add a webfont without asking — no dependencies is a project rule.
