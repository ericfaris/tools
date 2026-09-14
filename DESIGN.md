# Tools — Design System

**"Drafting Table"** — a calm, analog-precise engineer's drafting sheet, in
both daylight and lamp-lit night versions.

Live showcase: [`/design-system.html`](app/static/design-system.html) (served
statically at `/static/design-system.html` — no build step, open it straight
from the running app or the file itself).

---

## 1. Direction narrative

### Why "Drafting Table"

`SPEC.md` is explicit that this app's whole identity rests on two things
holding together at once: it has to feel **calm, precise, and trustworthy**
(a zero-retention, self-hosted privacy tool people share with family) *and*
it has to clear a real **delight bar** — "a fun, wow experience every single
time," with an explicit warning to avoid "the default-AI/template look."

The previous system (a dark `#0b0d12` background, a purple→teal
`#7c5cff`→`#2dd4bf` gradient, and a drifting blurred "aurora" blob) is almost
a textbook example of the generic-AI aesthetic the spec warns against — it's
the same violet/teal SaaS gradient this skill's own house style calls a
cliché. It also didn't say anything about what the app *is*: a workshop of
precise, single-purpose instruments (merge this, split that, convert this).

**Drafting Table** takes the name literally. The portal becomes a drafting
sheet: warm cream paper, a fine hairline grid, ink-navy type, and a warm
amber accent used the way a draftsman's red pencil marks up a page. The
signature control (the `Run` button) is treated as a rubber ink stamp —
double-outlined, tracked capitals, a thump-down press. Dark mode isn't a
separate palette bolted on; it's "the same sheet, lit at night" — the paper
becomes deep blueprint-navy and the grid glows cyan, same structure, same
proportions, same warm amber accent.

This reads as trustworthy (precision instruments, hand-drafted craft — the
opposite of a slick ad-tech SaaS) while still being distinctive and fun: the
grid, the stamp button, the pencil-draw underline on the brand hover, and the
corner-fold detail on every tile are all small, considered "wow" beats rather
than one big gimmick.

### Key moments this was designed around

1. **First load of the portal** — the grid of tiles staggers in (`rise`
   keyframe) over a visible drafting-grid backdrop; this is the first
   impression and has to read as "made with care," not template-generated.
2. **The drop-a-file moment** — the dropzone is dashed like a cut-line on a
   pattern, glows blueprint-blue on drag-over, and nudges an arrow icon
   (`bob` keyframe) to invite the action.
3. **Pressing Run** — the ink-stamp button thumps down with a slight
   overshoot (`--ease-stamp`) rather than a generic flat press.
4. **The done/download moment** — the existing confetti burst is retimed to
   the new palette (amber/blueprint/ink instead of purple/teal) so the
   celebration matches the rest of the system instead of clashing with it.
5. **Browsing the grid family-by-family** — each family heading gets a
   hairline rule (`.family-title::after`) like a ruled section break on a
   drafting sheet, reinforcing "instruments, organized" rather than "app
   nav."

### Mood-board directions considered

Three directions were generated via Ideogram (batch/autonomous run — no user
available to review, so all three were generated, compared, and one chosen
here rather than presented for a live pick). All three boards are saved to
`app/static/design/moodboards/` for reference.

| Direction | File | Verdict |
|---|---|---|
| **Drafting Table** (chosen) | `moodboards/drafting-table.webp` | Precise, warm, literal to the "Tools" name; reads as craft, not corporate SaaS; the stamp button and grid are strong, reusable motifs; scales well to both light and dark. |
| Vault Ledger | `moodboards/vault-ledger.webp` | Handsome, but the black/brass/engraved-serif register reads as *banking/security-product*, not "everyday utility tools." Heavier and more formal than the calm-but-fun brief calls for; would fight the "delight bar" (playful drop-zone, confetti) instead of supporting it. |
| Field Kit | `moodboards/field-kit.webp` | Rugged industrial/toolbox — fun, but the stencil display face and diamond-plate texture skew toward outdoor/hardware gear, and a condensed stencil face reads poorly at the small sizes this app actually needs (form labels, option text, file lists). |

**Drafting Table** wins on fit (privacy + craft + "your machine"), on
legibility at UI sizes, and on how naturally it extends to the small
functional details (dropzone as a cut-line, options as a spec sheet, tiles as
index cards) that make up most of the actual screen time — the mood board
moment is only the entry point, not the whole job.

---

## 2. Color

All tokens live in `app/static/styles.css` under `:root` (light) and the
`prefers-color-scheme: dark` block. Every screen respects the OS/browser
color-scheme automatically — there is no manual toggle (matches
`SPEC.md §6`: "Light/dark friendly").

### Light ("daylight sheet")

| Token | Value | Role |
|---|---|---|
| `--paper` | `#f2ecdd` | Page background — cream drafting paper |
| `--paper-soft` | `#ece3cd` | Recessed surfaces (dropzone, inset areas) |
| `--panel` | `#faf6ea` | Card/panel surface, slightly brighter than paper |
| `--panel-hover` | `#fffdf5` | Card hover surface |
| `--line` | `#cdbe97` | Warm ruled hairline (borders, rules) |
| `--grid-line` | `rgba(47,111,158,.16)` | Faint blueprint grid ink on the page backdrop |
| `--ink` | `#1c2530` | Primary text — near-black ink navy |
| `--ink-soft` | `#5c6674` | Secondary text — graphite |
| `--ink-faint` | `#8b9099` | Tertiary/footer text |
| `--blueprint` | `#2f6f9e` | Secondary accent — links, grid, focus rings, dropzone active state |
| `--blueprint-soft` | `rgba(47,111,158,.12)` | Focus-ring halo, active dropzone wash |
| `--accent` | `#954e10` | Primary accent — the "red pencil" mark; Run button, tile-arrow, hero underline text |
| `--accent-strong` | `#7a3f0c` | Hover/press state for accent elements |
| `--accent-soft` | `rgba(149,78,16,.14)` | Ambient wash (hero corner glow) |
| `--on-accent` | `#faf6ea` | Solid, opaque text/border color for content sitting on `--accent` |
| `--good` | `#3f7d4a` | Success semantic (reserved for future use) |
| `--danger` | `#a8402f` | Error text |
| `--danger-soft` | `rgba(168,64,47,.12)` | Error background wash (reserved) |

### Dark ("the same sheet, lit at night")

| Token | Value | Role |
|---|---|---|
| `--paper` | `#101c27` | Page background — deep blueprint navy |
| `--paper-soft` | `#0c151e` | Recessed surfaces |
| `--panel` | `#17293780` | Card surface — intentionally translucent (50% alpha) so the grid backdrop shows faintly through cards, like a sheet of vellum over the blueprint |
| `--panel-hover` | `#1d3244` | Card hover surface (opaque) |
| `--line` | `#2c445a` | Hairline borders |
| `--grid-line` | `rgba(110,195,230,.14)` | Glowing cyan grid ink |
| `--ink` | `#ecf1f4` | Primary text |
| `--ink-soft` | `#9fb1c1` | Secondary text |
| `--ink-faint` | `#6d7f90` | Tertiary/footer text |
| `--blueprint` | `#6ec3e6` | Secondary accent — brighter cyan for legibility on dark |
| `--blueprint-soft` | `rgba(110,195,230,.14)` | Focus-ring halo |
| `--accent` | `#e0a53c` | Primary accent — warm gold, brighter than the light-mode rust so it still reads as "warm ink" against dark paper |
| `--accent-strong` | `#f2b957` | Hover/press state |
| `--accent-soft` | `rgba(224,165,60,.16)` | Ambient wash |
| `--on-accent` | `#101c27` | Solid dark ink — the light-gold accent needs dark text/border on it, not light |
| `--good` | `#74c684` | Success semantic |
| `--danger` | `#e2685a` | Error text |
| `--danger-soft` | `rgba(226,104,90,.16)` | Error background wash |

### Contrast ratios (WCAG relative luminance, checked pairs)

| Pair | Ratio | Passes |
|---|---|---|
| `--ink` on `--paper` (light) | 13.13:1 | AAA |
| `--ink-soft` on `--paper` (light) | 4.94:1 | AA (normal text) |
| `--ink` on `--panel` (light) | 14.33:1 | AAA |
| `--accent` on `--paper` (light, body text use) | 5.28:1 | AA |
| `--blueprint` on `--paper` (light, links/labels) | 4.58:1 | AA |
| `--on-accent` on `--accent` (light Run button) | 5.76:1 | AA |
| `--danger` on `--paper` (light) | 5.18:1 | AA |
| `--ink` on `--paper` (dark) | 15.16:1 | AAA |
| `--ink-soft` on `--paper` (dark) | 7.83:1 | AAA |
| `--blueprint` on `--paper` (dark) | 8.72:1 | AAA |
| `--on-accent` on `--accent` (dark Run button) | 7.90:1 | AAA |
| `--danger` on `--paper` (dark) | 5.23:1 | AA |

(`--accent-strong` is deliberately darker/lighter than `--accent` for
hover/press only — it is never used as a required-contrast text color by
itself.)

---

## 3. Type

Both faces are **self-hosted** (`app/static/fonts/*.woff2`), not loaded from
a CDN — the app's CSP has no external `font-src` exception, and self-hosting
also matches the "no third-party calls, ever" privacy posture the whole app
is built around (`SPEC.md §8`: "No analytics, no third-party calls, no
telemetry").

- **Display / technical face — JetBrains Mono** (weights 400/500/600/700,
  `app/static/fonts/jbmono-{weight}.woff2`). Used for anything that reads as
  an instrument label or technical furniture: the brand mark, all headings,
  tool names, option labels, buttons, the footer, file-list chips, swatch
  hex codes. A monospace face reinforces "precision tool," and doubles as
  the numeric/code-like register the app needs for hex codes and filenames.
- **Body face — Archivo** (weights 400/500/600/700,
  `app/static/fonts/archivo-{weight}.woff2`). Used for actual reading copy:
  tile descriptions, tool descriptions, help text, result notes. A clean
  grotesk keeps longer copy comfortable — the mono face is never used for
  paragraph-length text.
- Fallback stacks: `var(--font-display)` → `ui-monospace, "SFMono-Regular",
  Menlo, Consolas, monospace`; `var(--font-body)` → `ui-sans-serif,
  system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`.
- Both `@font-face` blocks use `font-display: swap`. The two heaviest-use
  files (`jbmono-700`, `archivo-400`) are preloaded in `base.html`.

### Type scale

| Token | Size | Line-height | Used for |
|---|---|---|---|
| `--text-xs` | 12px (`.75rem`) | `--lh-tight`/`--lh-snug` per use | Labels, footer, badges, hex codes |
| `--text-sm` | 14px (`.875rem`) | `--lh-snug` | Tile/tool descriptions, help text, Run button label |
| `--text-base` | 16px (`1rem`) | `--lh-normal` | Body copy, form inputs |
| `--text-md` | 18px (`1.125rem`) | `--lh-normal` | Hero paragraph, tool-page lede |
| `--text-lg` | 22px (`1.375rem`) | `--lh-snug` | Tool-page `h1` |
| `--text-xl` | 30px (`1.875rem`) | `--lh-snug` | Reserved for section headings (showcase page uses it) |
| `--text-2xl` | `clamp(2rem, 5vw, 2.75rem)` | `--lh-tight` | Reserved for a smaller hero variant |
| `--text-3xl` | `clamp(2.5rem, 7vw, 3.75rem)` | `--lh-tight` | Portal hero `h1` |

Line-height tokens: `--lh-tight` 1.1 (display headlines), `--lh-snug` 1.3
(sub-headings, short labels), `--lh-normal` 1.5 (body/UI text — the default),
`--lh-relaxed` 1.65 (reserved for long-form copy if it's ever needed).

---

## 4. Spacing, radius, shadow, motion

### Spacing (4px base)

`--space-1` 4px · `--space-2` 8px · `--space-3` 12px · `--space-4` 16px ·
`--space-5` 20px · `--space-6` 24px · `--space-8` 32px · `--space-10` 40px ·
`--space-12` 48px · `--space-16` 64px.

### Radius — deliberately crisp, never bubbly

`--radius-sm` 4px (the Run button — a stamp has a hard edge) · `--radius-md`
8px (inputs, chips, the tool icon badge) · `--radius-lg` 12px (cards/tiles,
the dropzone) · `--radius-pill` 999px (the footer version badge, file-list
chips, the toast).

### Shadow

`--shadow-sm` — `0 1px 2px rgba(28,37,48,.08)` (light) /
`rgba(0,0,0,.35)` (dark) — resting state, e.g. the Run button.
`--shadow-md` — `0 6px 20px …/.10` / `.4` — hover lift (tiles, Run button
hover, result reveal).
`--shadow-lg` — `0 16px 40px …/.16` / `.5` — the toast, the deepest
elevation in the system.

### Motion

| Token | Value | Meant for |
|---|---|---|
| `--ease-standard` | `cubic-bezier(.4,0,.2,1)` | General-purpose easing |
| `--ease-out` | `cubic-bezier(0,0,.2,1)` | Reveals (tile rise, result panel) |
| `--ease-stamp` | `cubic-bezier(.34,1.56,.64,1)` | The Run button press — a slight overshoot so it "thumps" like a stamp hitting paper |
| `--duration-fast` | 120ms | Hovers, focus-ring transitions |
| `--duration-base` | 200ms | Tile lift, input/dropzone state changes |
| `--duration-slow` | 420ms | Page-level reveals, the brand pencil-underline draw-in |

`prefers-reduced-motion: reduce` disables all animation/transition globally
(unchanged behavior from the previous system, still respected).

---

## 5. Components

- **Topbar / brand** — sticky, blurred cream/navy glass over the grid
  backdrop. The brand mark (◆) sits in `--accent`; the wordmark gets a
  hidden blueprint-colored underline that draws in left→right on hover
  (`.brand-name::after`), evoking a ruler stroke rather than a color swap.
- **Filter input** — a plain bordered field with a blueprint focus ring
  (`--blueprint-soft` halo). No placeholder trickery; states are default,
  focus-visible only (no separate hover state — inputs don't need one).
- **Portal tile** — the primary content card. States: default (panel
  surface, hairline border, small folded-corner triangle in `.tile::before`
  suggesting a dog-eared index card); hover (lifts 3px, border turns
  blueprint, corner-fold disappears as if the page were flattened, shadow
  grows to `--shadow-md`, the arrow glyph slides in); active (settles back
  down with a slight scale). Staggered entrance via the `rise` keyframe with
  a per-tile `--i` delay multiplier.
- **Family heading** — uppercase, tracked, blueprint-colored, with a
  hairline rule filling the remaining width (`.family-title::after`) so
  families read as ruled sections of one sheet rather than app-nav
  categories.
- **Dropzone** — the signature "drop a file" moment. Default: dashed
  hairline border over `--paper-soft` (a cut-line on a pattern). Hover/focus:
  border turns blueprint. Drag-over: border + wash turn blueprint and the
  zone scales up 1% (`.dragover`). The down-arrow glyph bobs continuously to
  invite the action, and pauses under `prefers-reduced-motion`.
- **Options** — label in the display face, uppercase, tracked, muted;
  control (`select`/`text`/`number`/`checkbox`) styled as a plain bordered
  field with the same blueprint focus ring as the filter input, so every
  focusable control in the app shares one focus language.
- **Run button (signature control)** — the ink-stamp. Two-tone border
  (`--accent` outer + a semi-transparent inset ring via `.run::after`) with
  tracked uppercase text in the display face on `--on-accent` (never on
  `--panel`, which is translucent in dark mode and would fail contrast — see
  §2). States: default (`--shadow-sm`); hover (lifts 2px, `--shadow-md`);
  active/press (`--ease-stamp` thump — translates down and scales to 98%);
  disabled (45% opacity, shadow removed); busy (label fades to 25% opacity,
  a spinner ring in `--on-accent` fades in and spins).
- **Error text** — `--danger`, sits inline below the form, no icon (kept
  plain per `SPEC.md §6`: "plain-language messages... never raw stack
  traces").
- **Result note / swatches (Color Picker tool)** — swatch cards are
  panel-surfaced buttons; the chip shows the actual color, the hex renders in
  the display face (it's effectively a code value), and the card's hover
  border recolors to the swatch's own hue via the existing `--c` custom
  property pattern.
- **Toast** — solid `--ink`-on-`--paper` (inverted from the rest of the UI on
  purpose, so it reads as a stamped notice rather than another card),
  pill-radius, `--shadow-lg`.
- **Footer** — display-face, tertiary-colored, with the version number in a
  pill badge (`--panel` on `--paper` with a hairline border) rather than
  plain text, so it reads as a small metadata tag.
- **Confetti** (JS, `tool.js`) — recolored from the old purple/teal set to
  the system palette: `#954e10` (accent), `#2f6f9e` (blueprint), `#3f7d4a`
  (good), `#cdbe97` (line/paper-tan), `#1c2530` (ink) — so the celebratory
  moment matches the rest of the system instead of clashing with it.

---

## 6. Backgrounds, texture, and generated art

- **Page backdrop (`.aurora`, kept as the existing hook name to avoid
  touching template markup)** — replaced the old purple/teal radial-gradient
  blob with a genuine drafting-grid texture: two repeating linear gradients
  (28px cells) in `--grid-line`, plus one soft `--accent-soft` radial wash in
  the top-right corner so the sheet isn't perfectly flat. This is real CSS,
  not an image, so it stays crisp at any size/zoom and costs nothing to
  load.
- **Mood boards** (`app/static/design/moodboards/`) — three Ideogram
  generations from the direction-selection pass (see §1), kept in the repo
  as the design record:
  - `drafting-table.webp` — chosen direction. Ideogram prompt direction:
    "cream/graph-paper background, fine blueprint-blue grid, palette chips
    (cream/ink-navy/blueprint-cyan/amber/graphite), display type spelling
    TOOLS as hand-drafted compass-and-ruler lettering, a rubber-stamp
    primary button, graph-paper + linen + pencil-sketch textures; precise,
    calm, analog-trustworthy, craftsman mood."
  - `vault-ledger.webp` — rejected alternate (private-vault/banknote
    direction).
  - `field-kit.webp` — rejected alternate (industrial toolbox/stencil
    direction).
- **Favicon** (`app/static/favicon.svg`, rasterized to
  `app/static/favicon-32.png` and `app/static/favicon.ico`) — redesigned
  from the old purple/teal gradient diamond to a hand-authored SVG drafting
  compass/divider: ink-navy legs open over an amber pivot point, with a
  blueprint dashed baseline rule, on the cream paper token color. Drawn as
  crisp geometry (not a raster illustration) because a technical instrument
  mark reads better at 16px than a photorealistic icon would. Rasterized via
  Pillow (supersampled 8x, then downscaled) since no SVG rasterizer was
  available in the environment; ICO built with 16/32/48/64px frames.

---

## 7. Accessibility notes

- Every text/background pair actually used for UI copy meets WCAG AA at
  minimum (see the contrast table in §2); most exceed it (AAA) in dark mode.
- Focus states: every interactive control (filter input, tool-page inputs,
  the dropzone) shares one focus language — a 3px `--blueprint-soft` halo
  plus a `--blueprint` border — so focus is always visible and always the
  same color regardless of what's focused.
- `prefers-reduced-motion: reduce` disables all animation and transition
  globally (`.aurora`, `.dz-icon`, tile rise, button press, confetti timing
  loop still runs its physics but the confetti effect itself is skipped
  entirely when reduced motion is set, per `tool.js`).
- No color-only signal: the error state is text (not just red), and the
  disabled Run button drops opacity *and* sets `cursor: not-allowed` *and*
  is a real `disabled` attribute (keyboard/AT correctly skip it).
- Dark mode's `--on-accent` was specifically introduced because the naive
  choice (reusing `--panel`, which is a 50%-alpha color in dark mode) would
  have rendered semi-transparent button text — see §2 for the fix and the
  contrast numbers it produces.

---

## 8. Asset inventory

| File | Role |
|---|---|
| `app/static/styles.css` | Full token set + every component style (rewritten) |
| `app/static/tool.js` | Confetti palette updated to system colors (1-line change) |
| `app/templates/base.html` | Font preloads + favicon `<link>` tags added |
| `app/static/fonts/jbmono-{400,500,600,700}.woff2` | Self-hosted JetBrains Mono, static per-weight files |
| `app/static/fonts/archivo-{400,500,600,700}.woff2` | Self-hosted Archivo, static per-weight files |
| `app/static/favicon.svg` | Redesigned drafting-compass mark (source of truth) |
| `app/static/favicon-32.png` | Rasterized 32px PNG icon (new `<link>`) |
| `app/static/favicon.ico` | Rasterized multi-size ICO (16/32/48/64px), regenerated |
| `app/static/design/moodboards/drafting-table.webp` | Chosen direction's mood board |
| `app/static/design/moodboards/vault-ledger.webp` | Rejected alternate |
| `app/static/design/moodboards/field-kit.webp` | Rejected alternate |
| `app/static/design-system.html` | The live showcase page (§9) |
| `DESIGN.md` | This document |

No sound identity — out of scope for this app (a silent, ambient utility
portal; the existing confetti is a visual-only flourish and stays that way).

---

## 9. The showcase page

`app/static/design-system.html` — reachable at `/static/design-system.html`
with zero build step. It loads the app's real `app/static/styles.css` and
fonts (not a copy), and renders:

- every color token as a labeled swatch, light and dark side-by-side info,
- the full type scale at real sizes/weights in the real faces,
- the spacing and radius scales as visual boxes,
- every shadow token applied to a card, and every motion token as a
  hoverable element that actually triggers that transition,
- every component (tile, dropzone, options, Run button in all its states,
  swatches, toast, footer badge) rendered with real markup/classes,
- the three mood boards side by side with the decision noted inline.

Open it directly in a browser (light/dark follows your OS setting, same as
the app) to audit the system, or keep it open next to `styles.css` while
extending the system later.

---

## Changelog

- **2026-09-14** — Initial design system pass ("Drafting Table"). Replaced
  the undocumented purple/teal "aurora" look with a documented, tokenized
  system; added self-hosted type, a redesigned favicon, `DESIGN.md`, and the
  `/static/design-system.html` showcase. No template markup or app logic was
  changed — this pass touched only `styles.css`, `tool.js`'s confetti
  palette, and `base.html`'s `<head>` (font preloads + icon links).
