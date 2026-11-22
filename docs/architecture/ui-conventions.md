# Vue app: UI conventions

Every screen uses the same few building blocks (`frontend/educore-ui/src/core/ui`) and tokens
(`src/styles/main.css`), so the app looks and behaves as one product.

## Colour: 60 / 30 / 10

| Share | Role | EduCore default | Where |
|---|---|---|---|
| 60% | Main | warm light neutral (`--ec-bg`, white cards) | the working area |
| 30% | Second | the brand's dark and primary colours (`--ec-second`, `--ec-ink`, `--ec-accent`) | top bar, sidebar, headings, links, chart marks |
| 10% | Loud | the brand accent (`--ec-loud`, gold) | the solid primary button, the active menu item, the selected row; never text, never data |

The three brand colours come from the university's EduCore Branding at runtime (`core/branding.ts`), so a
university's own palette follows the same split. Charts use the second colour as one hue (a lighter step of it for
meter tracks); red only for a limit reached, always with a word ("Full").

## Building blocks

| Component | Use it for |
|---|---|
| `PageHeader` | Every screen's title, one line of context, actions on the right, tabs or filters below |
| `SplitView` | Every queue (admissions, enrolment, registrations): the list stays on the left, the selected record docks on the right; ↑/↓ move through the list; on narrow screens one pane at a time with Back. The route sets `meta.fill: true` so it fills the window |
| `DetailPane` | A record in a split view: header (title, context, status), what is outstanding in a notice, sections that scroll, and the actions pinned at the bottom |
| `DetailSection` | One part of a record: a label and a one-line summary always visible, details on request (`collapsible`) |
| `StatusTag` | Any stored status; label and colour come from `core/status.ts` (`statusTag(kind, value)`), the same everywhere |
| `EmptyState` | Nothing to show |
| `StatTile` | A headline number with its context and a link to act on it (dashboard) |
| `BarList` | Magnitudes or meters: one row per item, one hue, shared baseline (dashboard) |
| `EcButton` | Every button. `primary` (the loud accent; one per view or pane), `secondary`, `ghost` (Edit, Cancel, Add), `danger` (refuse, remove), `quiet-danger` (a refusal inside a row); `sm` inside sections; `loading` shows a small spinner in the button |
| `EcModal` | A small modal that asks one thing (a reason, a choice) and closes; records and editing never go in a modal |
| `EcField` | A form field: label, control, then a hint or the error |
| `EcTabs` | The views of one screen (a queue's statuses, a setup's sections), with counts; ← → move between tabs |
| `EcSkeleton` | Loading: grey shapes where the content will be (`list`, `pane`, `tiles`, `card`, `lines`), never a spinner in the page |
| `.card` / `.ec-card`, `.ec-muted` | A card; secondary text |

Icons: Lucide (`@lucide/vue`), 18 px in the menu, 15 to 16 px inline.

## Rules

- Show what must be seen; details one click away (sections, "View all", Edit). No explanatory text for the obvious.
- Status tags are one or two words; the sentence beside the tag says the rest.
- Formal wording; no long dashes (use commas or " · ").
- Actions that decide something sit in the pane's footer; a decision that needs a reason or a choice opens an
  `EcModal`.
- Editing a record happens in the docked side window, like an ERP: setup lists (pathways, documents, programmes)
  are split views too, never overlay drawers.
- Dates DD-MM-YYYY, money N$ (`core/format.ts`).
- Colours, radius, borders and shadows come from the `--ec-*` tokens, never hard-coded per screen.
