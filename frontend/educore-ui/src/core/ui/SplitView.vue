<script setup lang="ts" generic="T extends Record<string, unknown>">
import { ChevronLeft } from "@lucide/vue";
import { computed, nextTick, ref } from "vue";
import EcSkeleton from "./EcSkeleton.vue";
import EmptyState from "./EmptyState.vue";

/**
 * A queue: the list on the left stays in view, the selected record opens docked on the right (no overlay).
 * ↑/↓ move through the list. On narrow screens the record replaces the list, with a Back button.
 */
const props = withDefaults(
  defineProps<{
    items: T[];
    itemKey: keyof T & string;
    loading?: boolean;
    emptyTitle?: string;
    emptyHint?: string;
    /** shown on the right while nothing is selected */
    placeholder?: string;
    listLabel?: string;
    detailLabel?: string;
  }>(),
  {
    loading: false,
    emptyTitle: "Nothing here",
    emptyHint: undefined,
    placeholder: "Select an item to see it here",
    listLabel: "List",
    detailLabel: "Details",
  },
);
const selected = defineModel<string | null>("selected", { default: null });

const list = ref<HTMLElement | null>(null);
const index = computed(() => props.items.findIndex((item) => item[props.itemKey] === selected.value));

function select(item: T) {
  selected.value = item[props.itemKey] as string;
}

async function move(step: number) {
  if (!props.items.length) return;
  const next = Math.min(Math.max(index.value + step, 0), props.items.length - 1);
  select(props.items[next]!);
  await nextTick();
  list.value?.querySelector<HTMLElement>('[aria-selected="true"]')?.scrollIntoView({ block: "nearest" });
}
</script>

<template>
  <div class="split" :class="{ 'has-selection': selected !== null }">
    <div class="list-pane ec-card">
      <div v-if="$slots.filters" class="filters"><slot name="filters" /></div>
      <EcSkeleton v-if="loading && !items.length" shape="list" :rows="5" />
      <EmptyState v-else-if="!items.length" :title="emptyTitle" :hint="emptyHint" />
      <ul
        v-else
        ref="list"
        class="list"
        role="listbox"
        :aria-label="listLabel"
        tabindex="0"
        :aria-busy="loading"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
      >
        <li
          v-for="item in items"
          :key="String(item[itemKey])"
          role="option"
          :aria-selected="item[itemKey] === selected"
          class="row"
          @click="select(item)"
        >
          <slot name="item" :item="item" :selected="item[itemKey] === selected" />
        </li>
      </ul>
    </div>

    <div class="detail-pane ec-card" role="region" :aria-label="detailLabel">
      <template v-if="selected !== null">
        <button type="button" class="back" @click="selected = null"><ChevronLeft :size="16" aria-hidden="true" /> Back to the list</button>
        <slot name="detail" :selected="selected" />
      </template>
      <EmptyState v-else :title="placeholder" />
    </div>
  </div>
</template>

<style scoped>
.split {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: minmax(18rem, 26rem) minmax(0, 1fr);
  gap: 1rem;
}

.list-pane,
.detail-pane {
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  padding: 0.75rem;
  border-bottom: 1px solid var(--ec-border-soft);
}

.list {
  flex: 1;
  margin: 0;
  padding: 0.25rem 0;
  overflow-y: auto;
  list-style: none;
  outline: none;
}

.row {
  padding: 0.7rem 1rem;
  border-left: 3px solid transparent;
  cursor: pointer;
}

.row + .row {
  border-top: 1px solid var(--ec-border-soft);
}

.row:hover {
  background: var(--ec-surface-muted);
}

.row[aria-selected="true"] {
  background: var(--ec-accent-soft);
  border-left-color: var(--ec-loud);
}

.list:focus-visible .row[aria-selected="true"] {
  outline: 2px solid var(--ec-accent);
  outline-offset: -2px;
}

.detail-pane {
  position: relative;
}

.back {
  display: none;
}

/* narrow: one pane at a time */
@media (max-width: 1023px) {
  .split {
    grid-template-columns: minmax(0, 1fr);
  }

  .split.has-selection .list-pane,
  .split:not(.has-selection) .detail-pane {
    display: none;
  }

  .back {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.75rem 1rem 0;
    background: none;
    border: 0;
    color: var(--ec-accent);
    font: inherit;
    font-size: 0.875rem;
    cursor: pointer;
  }
}
</style>
