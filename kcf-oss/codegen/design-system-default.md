# Default design system — a brand-neutral baseline

Design tokens are authorable (`design { design-system … }` → `ir.design`), but most
models don't declare them. **When a model declares no `design` block, apply this
neutral default** so every generated app gets a coherent, accessible baseline theme for
free — instead of unstyled markup or an ad-hoc per-project theme. If the model *does*
declare design tokens, those win; treat this only as the fallback.

Emit these as CSS custom properties (or the stack's token mechanism — Tailwind theme,
CSS-in-JS tokens, design-token JSON) and reference them everywhere; never hard-code
colors/spacing in components.

## Tokens

```css
:root {
  /* Color — neutral slate + a single calm accent; WCAG-AA text contrast */
  --color-bg: #ffffff;            --color-surface: #f8fafc;
  --color-border: #e2e8f0;        --color-text: #0f172a;
  --color-text-muted: #64748b;    --color-accent: #2563eb;
  --color-accent-text: #ffffff;
  --color-success: #16a34a;       --color-warning: #d97706;
  --color-danger: #dc2626;        --color-info: #0891b2;

  /* Typography — system stack (no external fonts; CSP-safe) */
  --font-sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  --text-xs: 0.75rem; --text-sm: 0.875rem; --text-base: 1rem;
  --text-lg: 1.125rem; --text-xl: 1.5rem; --text-2xl: 2rem;
  --font-weight-normal: 400; --font-weight-medium: 500; --font-weight-bold: 700;
  --line-height: 1.5;

  /* Spacing — 4px scale */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem; --space-4: 1rem;
  --space-6: 1.5rem;  --space-8: 2rem;   --space-12: 3rem;

  /* Radius, border, shadow, motion */
  --radius-sm: 4px; --radius-md: 8px; --radius-lg: 12px; --radius-full: 9999px;
  --border-width: 1px;
  --shadow-sm: 0 1px 2px rgba(15,23,42,0.06);
  --shadow-md: 0 4px 12px rgba(15,23,42,0.10);
  --transition: 150ms ease;

  /* Layout */
  --container-max: 1200px; --sidebar-width: 240px;
  --breakpoint-sm: 480px; --breakpoint-md: 768px; --breakpoint-lg: 1024px;
}

@media (prefers-color-scheme: dark) {
  :root {
    --color-bg: #0f172a;         --color-surface: #1e293b;
    --color-border: #334155;     --color-text: #f1f5f9;
    --color-text-muted: #94a3b8; --color-accent: #3b82f6;
  }
}
```

## Component conventions (baseline)

- **Density**: comfortable — `--space-3`/`--space-4` padding on controls and cells.
- **Buttons**: accent = filled (`--color-accent`/`--color-accent-text`); secondary =
  bordered; destructive = `--color-danger`. Radius `--radius-md`.
- **Forms**: label above input; `--color-danger` inline validation; required marked;
  `identity` fields read-only after create.
- **Tables/lists**: zebra via `--color-surface`; sticky header; row actions on the right.
- **Status/lifecycle**: badge tinted by semantic color (success/warning/danger/info).
- **Feedback**: toast for action results; skeleton loaders keyed to the query state.
- **Accessibility**: visible focus ring (`--color-accent`), AA contrast, keyboard-navigable
  controls, `aria` labels on icon-only buttons.

This baseline is deliberately generic — a team overrides it by authoring a `design`
block in the model (which then carries through as declared meaning) or via House
Conventions.
