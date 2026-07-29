# `dense-enterprise` preset — a dense, data-first skin

A second preset in the same shape as [`../design-system-default.md`](../design-system-default.md),
demonstrating that **only the skin swaps** — the structure (screens, nav, subtabs, portlets,
controls) stays IR-derived and identical to every other preset. This one targets the dense,
information-first look of enterprise back-office suites: hairline-bordered grid list views,
underlined record subtabs, portlet dashboards, compact spacing, squared corners.

Select it as a generation setting (`generate-frontend.md` → *Design system: `dense-enterprise`*);
model `design` tokens still override brand values on top of it.

## Tokens

```css
:root[data-design="dense-enterprise"] {
  /* Color — cooler neutrals + a corporate blue accent; WCAG-AA text contrast */
  --color-bg: #ffffff;            --color-surface: #f1f4f8;
  --color-border: #c8d0da;        --color-text: #1a2330;
  --color-text-muted: #5a6675;    --color-accent: #1f5c99;
  --color-accent-text: #ffffff;
  --color-success: #197a3d;       --color-warning: #a8620a;
  --color-danger: #b3261e;        --color-info: #0b6b83;

  /* Typography — system stack, one step smaller for density */
  --font-sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  --text-xs: 0.6875rem; --text-sm: 0.8125rem; --text-base: 0.875rem;
  --text-lg: 1rem; --text-xl: 1.25rem; --text-2xl: 1.625rem;
  --font-weight-normal: 400; --font-weight-medium: 600; --font-weight-bold: 700;
  --line-height: 1.35;

  /* Spacing — tighter 4px scale (compact density) */
  --space-1: 0.125rem; --space-2: 0.25rem; --space-3: 0.5rem; --space-4: 0.75rem;
  --space-6: 1rem;     --space-8: 1.5rem;  --space-12: 2rem;

  /* Radius, border, shadow, motion — squared corners, hairline borders, flat */
  --radius-sm: 0; --radius-md: 2px; --radius-lg: 3px; --radius-full: 9999px;
  --border-width: 1px;
  --shadow-sm: none;
  --shadow-md: 0 1px 3px rgba(26,35,48,0.12);
  --transition: 100ms ease;

  /* Layout — wider content, denser sidebar */
  --container-max: 1440px; --sidebar-width: 216px;
  --breakpoint-sm: 480px; --breakpoint-md: 768px; --breakpoint-lg: 1024px;
}

@media (prefers-color-scheme: dark) {
  :root[data-design="dense-enterprise"] {
    --color-bg: #0d1521;         --color-surface: #16202e;
    --color-border: #2b3a4d;     --color-text: #e8edf3;
    --color-text-muted: #93a1b3; --color-accent: #4a90d9;
  }
}
```

## Component & layout conventions (the skin)

- **Density**: compact — `--space-2`/`--space-3` padding on controls and cells; a taller
  information density than the comfortable baseline.
- **List views**: **hairline-bordered grid** (every cell bordered with `--color-border`),
  not zebra; sticky header row; right-aligned numeric/money columns. The data-grid
  conventions (system-prompt rule 13) are unchanged — drop identity/UUID columns, sortable
  headers, filter bar with facets, pagination — only the chrome is denser and gridded.
- **Record layout**: field-groups rendered as **underlined subtabs** across the top of the
  record (COMPOSITION subtabs and by-role field groups become tab strips), not stacked
  cards. Which groups exist stays IR-derived (or the by-role heuristic).
- **Dashboards**: MEASURE/analytics render as **portlets** — bordered, titled tiles on a
  multi-column grid — rather than the baseline's card row.
- **Buttons**: squared (`--radius-md: 2px`); primary = filled accent, secondary = bordered,
  destructive = `--color-danger`. Flat (no drop shadow) except menus/popovers.
- **Labels / status / accessibility**: identical to the baseline — humanized labels
  (rule 12), semantic-color status badges, visible focus ring, AA contrast, keyboard-nav.

Everything above is presentation. If you find yourself wanting a preset to add or remove a
screen, field, or control, that belongs in the model/IR, not here.
