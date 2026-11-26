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
meter tracks); a limit reached is said in words ("Full"), not in red.

## Type

Two typefaces: **Inter** for text, figures and labels; **Source Serif 4** (`--font-serif`) for page, record and panel
titles (`h1`, `h2`). Both are served by `educore_theme` (`/assets/educore_theme/fonts`).

## Screens

- **Home** (every member of staff): first "Waiting for you", a list of what is waiting from every queue the person's
  positions work on (how many, what, a link to act; nothing waiting is not listed), beside "Today" for a lecturer
  (their lessons and registers); then, for the offices that need them, a campus picker (in the address), headline
  numbers (`StatTile`, each linking to where to act), the year in charts and the work waiting as short tables. A
  student's My studies opens on "Coming up" (today's classes, assessments due, examinations ahead).
- **Menu**: an operation people do often has its own menu item, not a tab of another screen (a lecturer's
  Attendance, Gradebook and Marks; Approvals; Workload; Studies requests; Transcripts; Rooms; Examination timetable
  and rules; a student's Assessments, Timetable, Fees and Requests). Items sit in sections (Teaching, Academic,
  Examinations, Finance, Setup), headed when a person sees more than one. A record opened from a list keeps that
  list's item marked (`?from=` in its address).
- **List page**: `PageHeader` with tabs and the year, then a `DataTable` (search in its toolbar). A row opens the
  record's own page; the tab and year stay in the address, so going back returns to the same list.
- **Record page**: `RecordPage`: a link back to the list, the title with its status, the decisions top right, the
  record in `EcPanel`s, and a summary column beside it. What is still to be done is listed in words
  (`outstanding`), never as a coloured banner.

## Building blocks

| Component | Use it for |
|---|---|
| `PageHeader` | Every screen's title, one line of context, actions on the right, tabs or filters below |
| `DataTable` | Every list of records (admissions; registration of first-year and senior students): a table or a grid of cards (the viewer switches; remembered per list), `cell-<key>` slots shared by both, `wide` columns hidden on phones, a row or card opens its record page |
| `RecordPage` | One record on its own page (see Screens) |
| `EcPanel` | A titled panel of a record page or the dashboard; `flush` for an edge-to-edge `.ec-table`; a footer for the panel's own action |
| `ChecklistPanel` | What is outstanding, as a neutral list (`RecordPage` shows it from `outstanding`) |
| `DetailPane`, `DetailSection` | An editor's sections and pinned actions inside a card: the admission setup's pathway, document and programme pages. (`SplitView` is kept but no screen uses it now.) |
| `StatusTag` | Any stored status: quiet text on a neutral pill, a small dot carrying the tone; label and tone from `core/status.ts` (`statusTag(kind, value)`), the same everywhere |
| `EmptyState` | Nothing to show |
| `StatTile` | A headline number with its context and a link to act on it (dashboard) |
| `BarList` | Magnitudes or meters: one row per item, one hue, shared baseline (dashboard) |
| `LineChart` | A count over time (one series, the brand's primary colour): a 2px line, the latest value labelled, a crosshair and figure on hover |
| `DonutChart` | One whole split into two to four parts (online / paper, entry pathways, offer responses); more fold into "Other"; a legend with each figure and share always beside it. Series colours `--ec-series-1..4`, in that order, checked as a set |
| `SettingRow` | One setting on a settings page: label and a line of help on the left, the control on the right; rows stack in an `EcPanel`, sections listed beside them |
| `EcSegmented` | A choice between a few views of one screen (first-year / senior students) |
| `EcButton` | Every button. `primary` (the loud accent; one per view or pane), `secondary`, `ghost` (Edit, Cancel, Add), `danger` (refuse, remove), `quiet-danger` (a refusal inside a row); `sm` inside sections; `loading` shows a small spinner in the button |
| `EcModal` | A small modal that asks one thing (a reason, a choice, a date) and closes; records never go in a modal |
| `EcField` | A form field: label, control, then a hint or the error |
| `EcTabs` | Filters of one list (a queue's statuses, active or left) and a setup's sections, with counts set as quiet numbers, never as badges; a separate operation is its own menu item instead; ← → move between tabs |
| `EcSkeleton` | Loading: grey shapes where the content will be (`list`, `pane`, `tiles`, `card`, `lines`), never a spinner in the page |
| `.card` / `.ec-card`, `.ec-muted` | A card; secondary text |
| `.ec-facts`, `.ec-table` | Label and value pairs (`stacked` in a side column); a plain table inside a panel |

Icons: Lucide (`@lucide/vue`), 18 px in the menu, 15 to 16 px inline.

## Rules

- Show what must be seen; details one click away (sections, "View all", Edit). No explanatory text for the obvious.
- Status tags are one or two words; the sentence beside the tag says the rest.
- Formal wording; no long dashes (use commas or " · ").
- Calm pages: no coloured banners or tinted headers for a status; colour is a dot beside a word.
- Decisions on a record sit top right of its page; a decision that needs a reason or a choice opens an `EcModal`.
- Setup lists (pathways, documents, programmes) are list pages too; each item opens on its own page, and Save or
  Cancel returns to the list.
- Documents people take away (offer letter, proof of registration) are PDFs from the server
  (`educore.api.v1.documents`), linked with `core/documents.ts`.
- Dates DD-MM-YYYY, money N$ (`core/format.ts`).
- Colours, radius, borders and shadows come from the `--ec-*` tokens, never hard-coded per screen.
