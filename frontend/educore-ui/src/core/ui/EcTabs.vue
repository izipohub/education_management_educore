<script setup lang="ts" generic="V extends string">
/**
 * Calm tabs for the views of one screen (statuses of a queue, sections of a setup): a row of text tabs, the
 * current one underlined in the loud accent, with an optional count. Arrow keys move between tabs.
 */
const props = defineProps<{ tabs: { value: V; label: string; count?: number }[]; label: string }>();
const current = defineModel<V>({ required: true });

function move(step: number, event: KeyboardEvent) {
  const index = props.tabs.findIndex((t) => t.value === current.value);
  const next = props.tabs[(index + step + props.tabs.length) % props.tabs.length];
  if (next) {
    current.value = next.value;
    const list = (event.currentTarget as HTMLElement).parentElement;
    requestAnimationFrame(() => list?.querySelector<HTMLElement>('[aria-selected="true"]')?.focus());
  }
}
</script>

<template>
  <div class="ec-tabs" role="tablist" :aria-label="label">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      type="button"
      role="tab"
      class="tab"
      :aria-selected="tab.value === current"
      :tabindex="tab.value === current ? 0 : -1"
      @click="current = tab.value"
      @keydown.right.prevent="move(1, $event)"
      @keydown.left.prevent="move(-1, $event)"
    >
      {{ tab.label }}
      <span v-if="tab.count !== undefined" class="count">{{ tab.count }}</span>
    </button>
  </div>
</template>

<style scoped>
.ec-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.25rem;
  border-bottom: 1px solid var(--ec-border);
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: -1px;
  padding: 0.55rem 0.1rem 0.6rem;
  background: none;
  border: 0;
  border-bottom: 2px solid transparent;
  color: var(--ec-muted);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
}

.tab:hover {
  color: var(--ec-ink);
}

.tab[aria-selected="true"] {
  color: var(--ec-ink);
  font-weight: 600;
  border-bottom-color: var(--ec-loud);
}

/* a count is information, not an alert: a quiet number beside the label */
.count {
  color: var(--ec-muted);
  font-size: 0.8rem;
  font-weight: 400;
  font-variant-numeric: tabular-nums;
}

</style>
