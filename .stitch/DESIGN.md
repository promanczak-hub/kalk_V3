---
name: Material Business (Angular Material flavor)
project: Express Car Rental - LTR Calculator V3
version: 2.0
generated: 2026-04-29
note: Replaces v1 brutalist — user feedback "za bardzo kwadratowe", wants Angular Material aesthetic with elevation, rounded corners, accent colors, but keeps Geist font.

colors:
  surface: '#FFFFFF'
  surface-alt: '#F8FAFC'
  surface-hover: '#F1F5F9'
  divider: '#E2E8F0'
  outline: '#CBD5E1'
  text-primary: '#0F172A'
  text-secondary: '#475569'
  text-muted: '#94A3B8'
  primary: '#2563EB'        # Material Blue 600
  primary-hover: '#1D4ED8'  # Material Blue 700
  primary-pressed: '#1E40AF'
  primary-tint: '#EFF6FF'   # Material Blue 50 - acceptable pastel
  primary-tint-strong: '#DBEAFE'  # Material Blue 100
  on-primary: '#FFFFFF'
  semantic-loss: '#DC2626'      # red-600
  semantic-loss-tint: '#FEE2E2' # red-100 - acceptable pastel
  semantic-warning: '#EA580C'
  semantic-warning-tint: '#FFEDD5'
  semantic-good: '#16A34A'
  semantic-good-tint: '#DCFCE7'
  semantic-excellent: '#0891B2'
  semantic-excellent-tint: '#CFFAFE'

typography:
  font-family-sans: '"Geist", "Inter", system-ui, sans-serif'
  font-family-mono: '"Geist Mono", "Space Mono", monospace'
  scale:
    label-xs: 11px / 14px / 500
    label-sm: 12px / 16px / 500
    body-sm: 13px / 18px / 400
    body-md: 14px / 20px / 400
    title-sm: 14px / 20px / 600
    title-md: 16px / 24px / 600
    title-lg: 20px / 28px / 700
    headline: 24px / 32px / 700
    data-sm: 12px / 16px / 500 (mono)
    data-md: 14px / 20px / 600 (mono)
    data-lg: 24px / 32px / 700 (mono)

elevation:
  level-0: 'none'
  level-1: '0 1px 2px 0 rgb(0 0 0 / 0.05)'           # shadow-sm
  level-2: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)'  # shadow
  level-4: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)'  # shadow-md
  level-8: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)'  # shadow-lg

shape:
  small: '4px'   # rounded
  medium: '6px'  # rounded-md
  large: '8px'   # rounded-lg
  pill: '9999px' # rounded-full
---

## Brand & Style

Angular Material design system flavored for B2B fleet pricing. The interface should feel like a polished SaaS product — Stripe Dashboard, Linear, Notion — with subtle elevation, soft rounded corners, accent-blue primary actions, and clear visual hierarchy. Information density stays high (this is a power-user tool), but visual aggression is dialed down.

**Geist font is preserved** (user prefers it). Geist Mono for all numerical data — same as v1.

### Difference from v1 brutalist
- ❌ NO `border-2 border-slate-900` framing — use `border border-slate-200` + `shadow-sm` instead
- ❌ NO `rounded-none` — use `rounded-md` (6px) on containers, `rounded-lg` on cards, `rounded-full` on chips/pills
- ❌ NO `bg-slate-900` primary — use `bg-blue-600` (Material Blue)
- ❌ NO square slider thumbs — use round Material thumbs with shadow
- ❌ NO uppercase EVERYTHING — only top-level section titles
- ✅ Soft pastels ARE allowed for tinted backgrounds (bg-blue-50, bg-emerald-50) — they communicate state

## Colors

### Surfaces
- **`#FFFFFF` surface:** card backgrounds, primary inputs
- **`#F8FAFC` surface-alt:** alternating table rows, page background
- **`#F1F5F9` surface-hover:** hover state on rows/buttons

### Borders
- **`#E2E8F0` divider** (1px) — internal table dividers, subtle separators
- **`#CBD5E1` outline** (1px) — input field borders, button outlines

### Text
- **`#0F172A` text-primary:** body copy, headlines, button labels
- **`#475569` text-secondary:** captions, helper text, table headers
- **`#94A3B8` text-muted:** disabled state, placeholder text

### Primary (Material Blue)
- **`#2563EB` primary:** primary buttons, focus rings, active tabs, slider fills, links
- **`#1D4ED8` primary-hover:** primary button hover
- **`#EFF6FF` primary-tint:** subtle highlights, tab indicator backgrounds, badge backgrounds
- **`#DBEAFE` primary-tint-strong:** active state on selectable rows

### Semantic (margin tiers + status)
Used as **tinted chips** (bg-{color}-100 text-{color}-800) instead of border-only:
- **Red 600 + Red 100:** loss zone <8%, errors, destructive
- **Orange 600 + Orange 100:** warnings 8-12%
- **Emerald 600 + Emerald 100:** good 12-15% / 15-20%
- **Cyan 600 + Cyan 100:** excellent >20%

## Typography

- **Geist** for all UI text (already loaded via Google Fonts)
- **Geist Mono** for all numerical data, codes, IDs (`font-mono` Tailwind class via `--font-mono` CSS var)
- **Sentence case** by default (NOT UPPERCASE EVERYTHING)
- Section labels: `text-xs font-semibold uppercase tracking-wider text-slate-600` — only for top-level dividers
- Numbers: always `font-mono tabular-nums`, right-aligned in tables
- Polish thousand separator: `249 748 PLN` (non-breaking space)

## Shape

| Element | Radius | Tailwind |
|---|---|---|
| Cards, containers | 6-8px | `rounded-md` or `rounded-lg` |
| Buttons | 6px | `rounded-md` |
| Inputs | 6px | `rounded-md` |
| Chips (pills) | 9999px | `rounded-full` |
| Status badges (rectangles) | 4px | `rounded` |
| Slider thumbs | 9999px (circle) | `rounded-full` |
| Image avatars | 9999px | `rounded-full` |

**No `rounded-none` anywhere.** No `rounded-2xl` or larger either (too soft for business apps).

## Elevation

| Level | Use | Tailwind |
|---|---|---|
| 0 (flat) | inline elements, default | (none) |
| 1 | cards at rest | `shadow-sm` |
| 2 | hovered cards, dropdowns | `shadow` |
| 4 | floating buttons, modals header | `shadow-md` |
| 8 | dialogs, popovers | `shadow-lg` |

**Combine elevation with subtle border** for definition: `bg-white border border-slate-200 shadow-sm rounded-lg`.

## Components

### Buttons (Material Variants)

```tsx
// Primary (filled) — main CTAs
<button className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white px-4 py-2 rounded-md text-sm font-medium shadow-sm hover:shadow transition-all disabled:opacity-50">
  Nowa Kalkulacja
</button>

// Secondary (outlined)
<button className="inline-flex items-center gap-2 bg-white border border-slate-300 hover:bg-slate-50 hover:border-slate-400 text-slate-900 px-4 py-2 rounded-md text-sm font-medium transition-colors">
  Draft Broszury
</button>

// Tertiary (text-only) — Material text button
<button className="inline-flex items-center gap-2 text-blue-600 hover:bg-blue-50 px-3 py-2 rounded-md text-sm font-medium transition-colors">
  Reset
</button>

// Destructive
<button className="inline-flex items-center gap-2 bg-white border border-red-300 hover:bg-red-50 hover:border-red-500 text-red-600 px-4 py-2 rounded-md text-sm font-medium transition-colors">
  Usuń
</button>
```

### Tables

```tsx
<div className="bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
  <table className="w-full">
    <thead className="bg-slate-50">
      <tr className="border-b border-slate-200">
        <th className="text-xs font-semibold text-slate-600 px-4 py-3 text-left">Marka</th>
        <th className="text-xs font-semibold text-slate-600 px-4 py-3 text-right">Rata Netto</th>
      </tr>
    </thead>
    <tbody>
      <tr className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
        <td className="px-4 py-3 text-sm text-slate-900">AUDI A5 Avant</td>
        <td className="px-4 py-3 text-sm font-mono tabular-nums text-right text-slate-900">3 078 PLN/mc</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Status Badges (Material Chips)

```tsx
// Tinted chips — tier indicators (Material standard)
<span className="inline-flex items-center gap-1 bg-red-100 text-red-800 px-2.5 py-0.5 rounded-full text-xs font-semibold font-mono">
  &lt; 8%
</span>

<span className="inline-flex items-center gap-1 bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full text-xs font-semibold font-mono">
  15-20%
</span>

// Filter chip (selectable)
<button className="inline-flex items-center gap-1.5 bg-white border border-slate-300 hover:border-blue-500 px-3 py-1 rounded-full text-xs font-medium text-slate-700 transition-colors">
  SKODA <span className="text-slate-400 font-mono">(23)</span>
</button>

// Filter chip (active)
<button className="inline-flex items-center gap-1.5 bg-blue-600 text-white border border-blue-600 px-3 py-1 rounded-full text-xs font-medium transition-colors">
  AUDI <span className="text-blue-100 font-mono">(3)</span>
</button>
```

### Sliders (Material round thumbs!)

```tsx
// Track
<div className="relative h-1 bg-slate-200 rounded-full">
  {/* Fill */}
  <div className="absolute inset-y-0 left-0 bg-blue-600 rounded-full" style={{ width: '60%' }} />
  {/* Round Material thumb with hover scale */}
  <div className="absolute top-1/2 -translate-y-1/2 w-4 h-4 rounded-full bg-blue-600 shadow-md hover:scale-110 transition-transform cursor-grab" style={{ left: 'calc(60% - 8px)' }} />
</div>

// Margin slider with 3 SOLID color zones (semantic) but ROUND thumb
<div className="relative h-2 rounded-full overflow-hidden">
  <div className="absolute inset-y-0 left-0 bg-red-500" style={{ width: '27%' }} />
  <div className="absolute inset-y-0 bg-orange-500" style={{ left: '27%', width: '13%' }} />
  <div className="absolute inset-y-0 right-0 bg-emerald-500" style={{ left: '40%' }} />
</div>
{/* Round thumb above */}
<div className="absolute w-5 h-5 rounded-full bg-white border-2 shadow-md" style={{ borderColor: tierColor, left: 'calc(50% - 10px)', top: '4px' }} />
```

### Inputs

```tsx
<input
  type="text"
  className="w-full bg-white border border-slate-300 hover:border-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-100 text-slate-900 px-3 py-2 text-sm rounded-md outline-none transition-colors"
/>

// With wrapper label
<div className="flex items-center gap-2 bg-white border border-slate-300 hover:border-slate-400 focus-within:border-blue-600 focus-within:ring-2 focus-within:ring-blue-100 rounded-md px-3 py-1.5 transition-colors">
  <label className="text-xs text-slate-500 font-medium">Okres (mc):</label>
  <input className="w-12 text-sm font-mono font-semibold text-slate-900 bg-transparent outline-none tabular-nums" />
</div>
```

### Cards / Containers (Material elevation)

```tsx
// Standard card
<div className="bg-white border border-slate-200 rounded-lg shadow-sm hover:shadow transition-shadow p-6">
  ...
</div>

// Featured/elevated card
<div className="bg-white border border-blue-200 rounded-lg shadow-md p-6">
  ...
</div>

// Section container (no shadow, subtle)
<section className="bg-white border border-slate-200 rounded-md p-4">
  ...
</section>
```

### Navigation Tabs (Material indicator)

```tsx
<nav className="bg-white border-b border-slate-200 px-6 flex items-center gap-0">
  <button className="px-4 py-3 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 border-b-2 border-transparent transition-colors">
    Ekstrakcja AI
  </button>
  <button className="px-4 py-3 text-sm font-semibold text-blue-600 border-b-2 border-blue-600 transition-colors">
    Wyszukiwarka
  </button>
</nav>
```

### Sidebar (filter panel)

```tsx
<aside className="bg-white border border-slate-200 rounded-lg shadow-sm w-80">
  <div className="px-4 py-3 border-b border-slate-200">
    <h2 className="text-base font-semibold text-slate-900">Wyszukiwarka Ofert</h2>
    <p className="text-xs text-slate-500 mt-0.5">Zbuduj profil idealnego auta</p>
  </div>
  <div className="p-4 space-y-4">
    <div>
      <label className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2 block">
        Marka
      </label>
      {/* chips */}
    </div>
  </div>
</aside>
```

## Interactions

- **Hover:** subtle background shift (`bg-slate-50`) + shadow elevation increase
- **Focus:** `focus:ring-2 focus:ring-blue-100 focus:border-blue-600` (Material focus ring)
- **Active/pressed:** background darkens one step
- **Loading:** spinner is `text-blue-600` (Lucide `Loader2 animate-spin`), Material progress
- **Disabled:** `opacity-50 cursor-not-allowed`

## Tabular Number Doctrine (preserved from v1)

- Geist Mono / `font-mono tabular-nums`
- Right-align in tables
- Polish thousand separators (`249 748 PLN`)
- Single space before unit (`6 888 PLN/mc`)

## Migration: v1 Brutalist → v2 Material

Refactor agents follow this swap table:

| v1 Brutalist | v2 Material |
|---|---|
| `border-2 border-slate-900` | `border border-slate-200 shadow-sm` |
| `rounded-none` (containers) | `rounded-md` or `rounded-lg` |
| `rounded-sm` (buttons) | `rounded-md` |
| `bg-slate-900` (primary button) | `bg-blue-600` |
| `hover:bg-slate-800` | `hover:bg-blue-700` |
| `bg-white border border-slate-900` (secondary) | `bg-white border border-slate-300` |
| `w-4 h-4 rounded-none` (slider thumb) | `w-4 h-4 rounded-full bg-blue-600 shadow-md` |
| `bg-white border border-{color}-600 text-{color}-700` (badges) | `bg-{color}-100 text-{color}-800 rounded-full` |
| `font-mono uppercase tracking-wider` (chips) | `font-medium` (sentence case) |
| `text-[10px] font-bold uppercase` (everything) | `text-sm font-medium` (only top labels uppercase) |

## The Material Test

Before shipping any component, ask:

1. ✅ Does it have **elevation hierarchy**? (shadow OR border, not both aggressively)
2. ✅ Are **corners rounded** (4-8px)? Not square, not 16px+.
3. ✅ Are **primary actions blue** (Material Blue)? Not black.
4. ✅ Are **slider thumbs round**? With shadow for grip affordance.
5. ✅ Are **status indicators tinted chips** (bg-{color}-100)? Or solid pills with white text.
6. ✅ Does it use **Geist** for text and **Geist Mono** for numbers?
7. ✅ Is **density preserved** (table rows, button padding)? Material doesn't mean wasteful whitespace.

All 7 pass = Material business badge.
