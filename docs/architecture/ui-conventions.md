# Vue app: UI conventions

Every screen uses the same few building blocks (`frontend/educore-ui/src/core/ui`) and tokens
(`src/styles/main.css`), so the app looks and behaves as one product.

## Building blocks

| Component | Use it for |
|---|---|
| `PageHeader` | Every screen's title, one line of context, actions on the right, tabs or filters below |
| `SplitView` | Every queue (admissions, enrolment, registrations): the list stays on the left, the selected record docks on the right; ↑/↓ move through the list; on narrow screens one pane at a time with Back. The route sets `meta.fill: true` so it fills the window |
| `DetailPane` | A record in a split view: header (title, context, status), what is outstanding in a notice, sections that scroll, and the actions pinned at the bottom |
| `DetailSection` | One part of a record: a label and a one-line summary always visible, details on request (`collapsible`) |
| `StatusTag` | Any stored status; label and colour come from `core/status.ts` (`statusTag(kind, value)`), the same everywhere |
| `EmptyState` | Nothing to show |
| `.card` / `.ec-card`, `.ec-muted` | A card; secondary text |

Icons: Lucide (`@lucide/vue`), 18 px in the menu, 15 to 16 px inline.

## Rules

- Show what must be seen; details one click away (sections, "View all", Edit). No explanatory text for the obvious.
- Status tags are one or two words; the sentence beside the tag says the rest.
- Formal wording; no long dashes (use commas or " · ").
- Actions that decide something sit in the pane's footer; a decision that needs a reason or a choice opens a small
  dialog.
- Dates DD-MM-YYYY, money N$ (`core/format.ts`).
- Colours, radius, borders and shadows come from the `--ec-*` tokens, never hard-coded per screen.
