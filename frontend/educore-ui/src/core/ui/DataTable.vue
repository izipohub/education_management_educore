<script setup lang="ts" generic="T extends Record<string, unknown>">
import { LayoutGrid, List } from "@lucide/vue";
import { ref, watch } from "vue";
import type { RouteLocationRaw } from "vue-router";
import { useRouter } from "vue-router";
import EcSkeleton from "./EcSkeleton.vue";
import EmptyState from "./EmptyState.vue";

/**
 * A list of records, as a table or as a grid of cards (the viewer's choice, remembered per list on this
 * browser), with the toolbar (search, filters) above. A row or card opens its record page (`to`); the first
 * column holds the link, so the list works from the keyboard too. Cells are plain values unless a `cell-<key>`
 * slot shapes them; a card shows the same cells, the first as its title.
 */
export interface Column {
  key: string;
  label: string;
  align?: "left" | "right";
  /** hidden on narrow screens */
  wide?: boolean;
  width?: string;
}

const props = withDefaults(
  defineProps<{
    columns: Column[];
    rows: T[];
    rowKey: keyof T & string;
    to?: (row: T) => RouteLocationRaw;
    loading?: boolean;
    emptyTitle?: string;
    emptyHint?: string;
    /** what the table lists, for screen readers and the count below ("applications") */
    noun: string;
  }>(),
  { to: undefined, loading: false, emptyTitle: "Nothing here", emptyHint: undefined },
);

type View = "list" | "grid";
const viewKey = () => `ec-view:${props.noun}`;
function readView(): View {
  try {
    return localStorage.getItem(viewKey()) === "grid" ? "grid" : "list";
  } catch {
    return "list";
  }
}
const view = ref<View>(readView());
watch(view, (value) => {
  try {
    localStorage.setItem(viewKey(), value);
  } catch {
    // private browsing: the choice lasts for this visit
  }
});

const router = useRouter();
function open(row: T, event: MouseEvent) {
  // a click on the link itself (or with a modifier, for a new tab) is left to the link
  if (!props.to || (event.target as HTMLElement).closest("a, button, input") || event.metaKey || event.ctrlKey) return;
  void router.push(props.to(row));
}
</script>

<template>
  <section class="data-table ec-card" :aria-label="noun">
    <div class="toolbar">
      <slot name="toolbar" />
      <div class="views" role="group" aria-label="Show as">
        <button type="button" :aria-pressed="view === 'list'" title="List" aria-label="List" @click="view = 'list'">
          <List :size="16" aria-hidden="true" />
        </button>
        <button type="button" :aria-pressed="view === 'grid'" title="Grid" aria-label="Grid" @click="view = 'grid'">
          <LayoutGrid :size="16" aria-hidden="true" />
        </button>
      </div>
    </div>

    <EcSkeleton v-if="loading && !rows.length" shape="list" :rows="6" :label="`Loading ${noun}`" class="loading" />
    <EmptyState v-else-if="!rows.length" :title="emptyTitle" :hint="emptyHint" />
    <ul v-else-if="view === 'grid'" class="grid" :aria-busy="loading">
      <li v-for="row in rows" :key="String(row[rowKey])" class="tile" :class="{ link: to }" @click="open(row, $event)">
        <template v-for="(c, i) in columns" :key="c.key">
          <div v-if="i === 0" class="tile-title">
            <RouterLink v-if="to" :to="to(row)" class="primary">
              <slot :name="`cell-${c.key}`" :row="row">{{ row[c.key] }}</slot>
            </RouterLink>
            <slot v-else :name="`cell-${c.key}`" :row="row">{{ row[c.key] }}</slot>
          </div>
        </template>
        <dl class="tile-facts">
          <div v-for="c in columns.slice(1)" :key="c.key">
            <dt>{{ c.label }}</dt>
            <dd><slot :name="`cell-${c.key}`" :row="row">{{ row[c.key] ?? "" }}</slot></dd>
          </div>
        </dl>
      </li>
    </ul>
    <div v-else class="scroll">
      <table :aria-busy="loading">
        <thead>
          <tr>
            <th v-for="c in columns" :key="c.key" scope="col" :class="[c.align, { wide: c.wide }]" :style="c.width ? { width: c.width } : undefined">
              {{ c.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="String(row[rowKey])" :class="{ link: to }" @click="open(row, $event)">
            <td v-for="(c, i) in columns" :key="c.key" :class="[c.align, { wide: c.wide }]">
              <RouterLink v-if="i === 0 && to" :to="to(row)" class="primary">
                <slot :name="`cell-${c.key}`" :row="row">{{ row[c.key] }}</slot>
              </RouterLink>
              <slot v-else :name="`cell-${c.key}`" :row="row">{{ row[c.key] ?? "" }}</slot>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer v-if="rows.length" class="foot ec-muted">{{ rows.length }} {{ rows.length === 1 ? noun.replace(/s$/, "") : noun }}</footer>
  </section>
</template>

<style scoped>
.data-table {
  overflow: hidden;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--ec-border-soft);
}

.views {
  display: inline-flex;
  margin-left: auto;
  padding: 0.15rem;
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface-muted);
}

.views button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.9rem;
  height: 1.7rem;
  border: 0;
  border-radius: calc(var(--ec-radius-sm) - 2px);
  background: none;
  color: var(--ec-muted);
  cursor: pointer;
}

.views button:hover {
  color: var(--ec-ink);
}

.views button[aria-pressed="true"] {
  background: var(--ec-surface);
  color: var(--ec-ink);
  box-shadow: var(--ec-shadow);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 16.5rem), 1fr));
  gap: 0.75rem;
  margin: 0;
  padding: 1rem;
  list-style: none;
  background: var(--ec-surface-muted);
}

.tile {
  display: grid;
  align-content: start;
  gap: 0.75rem;
  padding: 0.9rem 1rem;
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface);
  font-size: 0.875rem;
}

.tile.link {
  cursor: pointer;
}

.tile.link:hover {
  border-color: color-mix(in srgb, var(--ec-accent) 35%, var(--ec-border));
}

.tile-title {
  padding-bottom: 0.65rem;
  border-bottom: 1px solid var(--ec-border-soft);
}

.tile-facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.6rem 1rem;
  margin: 0;
}

/* a card leaves out what a record does not have (a table keeps the empty cell, for the column) */
.tile-facts div:has(> dd:empty),
.tile-facts div:has(> dd > span:only-child:empty) {
  display: none;
}

.tile-facts dt {
  color: var(--ec-muted);
  font-size: 0.75rem;
}

.tile-facts dd {
  margin: 0.1rem 0 0;
  min-width: 0;
}

.loading {
  padding: 1rem;
}

.scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

th {
  padding: 0.6rem 1rem;
  background: var(--ec-surface-muted);
  border-bottom: 1px solid var(--ec-border);
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-align: left;
  white-space: nowrap;
}

td {
  padding: 0.7rem 1rem;
  border-bottom: 1px solid var(--ec-border-soft);
  vertical-align: middle;
}

tbody tr:last-child td {
  border-bottom: 0;
}

tr.link {
  cursor: pointer;
}

tr.link:hover td {
  background: var(--ec-surface-muted);
}

.right {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.primary {
  color: var(--ec-ink);
  font-weight: 600;
  text-decoration: none;
}

.primary:hover {
  text-decoration: underline;
}

.foot {
  padding: 0.6rem 1rem;
  border-top: 1px solid var(--ec-border-soft);
}

@media (max-width: 767px) {
  .wide {
    display: none;
  }

  th,
  td {
    padding-left: 0.75rem;
    padding-right: 0.75rem;
  }
}
</style>
