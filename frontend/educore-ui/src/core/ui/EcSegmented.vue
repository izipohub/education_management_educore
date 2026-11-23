<script setup lang="ts" generic="V extends string">
/** A choice between a few views of one screen (e.g. first-year and senior students), shown side by side */
defineProps<{ options: { value: V; label: string }[]; label: string }>();
const current = defineModel<V>({ required: true });
</script>

<template>
  <div class="segmented" role="group" :aria-label="label">
    <button
      v-for="o in options"
      :key="o.value"
      type="button"
      :aria-pressed="o.value === current"
      @click="current = o.value"
    >
      {{ o.label }}
    </button>
  </div>
</template>

<style scoped>
.segmented {
  display: inline-flex;
  padding: 0.15rem;
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface-muted);
}

button {
  padding: 0.35rem 0.8rem;
  border: 0;
  border-radius: calc(var(--ec-radius-sm) - 2px);
  background: none;
  color: var(--ec-muted);
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 500;
  white-space: nowrap;
  cursor: pointer;
}

button:hover {
  color: var(--ec-ink);
}

button[aria-pressed="true"] {
  background: var(--ec-surface);
  color: var(--ec-ink);
  font-weight: 600;
  box-shadow: var(--ec-shadow);
}
</style>
