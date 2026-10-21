# TriaVoz brand

## Identity

- Product name: **TriaVoz** (always one word, capital V).
- Voice: warm, precise, calm. Portuguese first; English at parity.
- Promise: the front desk that answers, understands and books by voice — with a human handoff and
  SAMU 192 guidance for emergencies.
- Avoid: clinical coldness, alarmism, invented metrics, "AI magic" language, emojis in product UI.

## Logo

The repository did **not** contain the author's official logo/favicon files. P06 ships an original
placeholder mark (speech bubble + five-bar waveform) in `apps/web/src/components/Logo.tsx`, plus
`src/app/icon.svg`, `apple-icon.tsx` and `opengraph-image.tsx`. When the official assets arrive,
replace those files and keep the same sizing/contrast contract; do not reintroduce a text-only
placeholder.

## Color tokens (source: `apps/web/src/app/globals.css`)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--background` | `#f4f8fa` | `#071923` | page |
| `--surface` | `#ffffff` | `#0d2431` | cards, panels |
| `--surface-2` | `#eef4f7` | `#12303f` | subtle fills |
| `--border` | `#dbe5ec` | `#1d3d4f` | borders |
| `--text` | `#0a2736` | `#e8f1f5` | body copy |
| `--text-muted` | `#526472` | `#9db2c0` | secondary copy |
| `--primary` | `#0e7c86` | `#2dd4bf` | brand actions |
| `--primary-strong` | `#0a5e66` | `#7ee8db` | small text/links (AA) |
| `--primary-soft` | `#d9f0f1` | `#133a40` | selected states |
| `--voice` | `#38bdf8` | `#38bdf8` | orb/accents only |
| `--voice-deep` | `#0369a1` | `#7dd3fc` | orb gradient |

Contrast rules:

- Never use `--voice` (`#38bdf8`) for small text on light surfaces. Use `--primary-strong` or
  `--text`.
- Never use brand teal/green as small text on white without checking the pair; `#0e7c86` on white is
  the reference AA pair, `#0a5e66` is safer for links.
- **`#0186E4` is not a text color** in this system. It may appear only as a large decorative accent
  after a contrast check.
- Status colors are semantic (`--st-urgent`, `--st-pending`, `--st-progress`, `--st-done`,
  `--st-cancelled`, `--st-spam`) and always paired with an icon + label.

## Type

- **Inter** via `next/font/google` (`--font-inter`), weights 400–700, `display: swap`.
- Headline: tight tracking, 1.05–1.15 line-height, `text-balance`.
- Body: 14–16 px, 1.55–1.7 line-height. Small labels: 11–12 px, uppercase only for eyebrows.
- Numbers in tables/metrics use `tabular-nums`.

## Shape and motion

- Radius: cards 16 px (`rounded-2xl`), controls 8–10 px, pills 999 px.
- Shadows: one soft card shadow; no neon glows except the orb halo.
- Motion: 150–250 ms ease-out for UI; orb halo 3–5 s. Respect `prefers-reduced-motion`.
- Orb states are communicated by label, animation and color (not color alone).

## Iconography

Lucide line icons, 3.5–5 px stroke at 16–20 px. Icons are decorative unless they are the only label;
then the control gets an `aria-label`.
