# TriaVoice brand

The public-facing product name is **TriaVoice** (always one word, capital V). Repository/package
names keep the historical `triavoz`/`TriaVoz` spelling; only user-visible copy uses TriaVoice.

## Identity

- Voice: warm, precise, calm. Portuguese first; English at parity.
- Promise: the front desk that listens, understands and books by voice — with a human handoff and
  SAMU 192 guidance for emergencies.
- Avoid: clinical coldness, alarmism, invented metrics, "AI magic" language, emojis in product UI.

## Logo

Official author-provided assets (2026-10):

- `Triavoice_logo.png` — full lockup (mark + wordmark), source of truth.
- `Triavoice_favicon.png` — mark only; background flood-filled to transparent, exported as:
  - `apps/web/src/app/icon.png` (512 px, favicon)
  - `apps/web/src/app/apple-icon.png` (180 px)
  - `apps/web/public/triavoice-mark.png` (256 px, used by `Logo.tsx` inside an `<Image>`)

The wordmark is typeset in HTML (`Tria` in `--heading`, `Voice` in `--primary`) so it adapts to
light/dark; never reintroduce the old speech-bubble placeholder.

## Color tokens (source: `apps/web/src/app/globals.css`)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--background` | `#edf1f7` | `#0a1524` | page |
| `--surface` | `#ffffff` | `#0e2033` | cards, panels |
| `--surface-2` | `#f5f8fc` | `#132842` | subtle fills, inputs |
| `--border` | `#dbe3ed` | `#1d3252` | borders |
| `--text` | `#22344f` | `#dde7f4` | body copy |
| `--heading` | `#132e5e` | `#f2f6fc` | display headings, wordmark |
| `--text-muted` | `#5d6c81` | `#8ea2bd` | secondary copy |
| `--primary` | `#2563eb` | `#2dd4bf` | actions |
| `--primary-strong` | `#1d4ed8` | `#5eead4` | hover/small text |
| `--primary-soft` | `#e4edff` | `rgba(45,212,191,.12)` | selected states |
| `--primary-contrast` | `#ffffff` | `#05202b` | text on primary |
| `--grad-a` → `--grad-b` | `#10b981` → `#2563eb` | `#34d399` → `#38bdf8` | gradient text (`.text-grad`) |
| `--orb-a` / `--orb-b` | `#34d399` / `#0ea5e9` | same | voice orb gradient + halo |
| `--eyebrow` | `#2563eb` | `#2dd4bf` | `.eyebrow` labels |
| `--navlink` | `#1c3a7a` | `#5eead4` | public header links |
| `--navy` | `#10294f` | `#0d1f36` | stats band background |
| `--band-*` | blue gradient set | dark teal set | bottom CTA band |

Contrast rules:

- Never use `--voice`/`--orb-b` for small text on light surfaces. Use `--primary-strong`.
- On the navy stats band, use `--grad-a` (teal/emerald) for numbers and `white/60` for labels.
- Status colors are semantic (`--st-urgent`, `--st-pending`, `--st-progress`, `--st-done`,
  `--st-cancelled`, `--st-spam`) and always paired with an icon + label.

## Type

- **Inter** (`--font-inter`) — body copy, 400–700.
- **Archivo** (`--font-archivo`) — display headings and wordmark, weight 800 (`display-title`),
  tracking −0.02em, line-height 1.04–1.15, `text-balance`.
- **JetBrains Mono** (`--font-jetmono`) — eyebrows (`.eyebrow`, uppercase, +0.22em tracking),
  timestamps, tool names, phone numbers, small labels; numbers use `tabular-nums`.
- Body: 14–16 px, 1.55–1.7 line-height.

## Shape and motion

- Radius: cards 16–24 px (`rounded-2xl`/`rounded-3xl`), controls and inputs `rounded-lg`, pills
  999 px.
- Shadows: one soft card shadow (light); flat in dark. The only glow is the orb/halo and the hero
  orb.
- Motion: 150–250 ms ease-out for UI; orb halo 3–5 s; floating hero pills 6 s; waveform bars 0.7–1.3
  s. Respect `prefers-reduced-motion`.
- Orb states are communicated by label, animation and color (not color alone).

## Iconography

Lucide line icons, 3.5–5 px stroke at 16–20 px. Icons are decorative unless they are the only label;
then the control gets an `aria-label`.
