<script setup lang="ts">
import { ChevronDown } from "@lucide/vue";
import { ref } from "vue";

/**
 * One section of a record: a title and a one-line summary always visible, the details on request (or always,
 * when not collapsible). Keeps a record pane short: what matters first, the rest one click away.
 */
const props = withDefaults(defineProps<{ title: string; summary?: string; collapsible?: boolean; open?: boolean }>(), {
  summary: undefined,
  collapsible: false,
  open: false,
});
const expanded = ref(props.open);
</script>

<template>
  <section class="detail-section">
    <component
      :is="collapsible ? 'button' : 'div'"
      class="head"
      :type="collapsible ? 'button' : undefined"
      :aria-expanded="collapsible ? expanded : undefined"
      @click="collapsible && (expanded = !expanded)"
    >
      <h3>{{ title }}</h3>
      <span v-if="summary || $slots.summary" class="summary"><slot name="summary">{{ summary }}</slot></span>
      <ChevronDown v-if="collapsible" :size="16" class="chevron" :class="{ open: expanded }" aria-hidden="true" />
    </component>
    <div v-if="!collapsible || expanded" class="body"><slot /></div>
  </section>
</template>

<style scoped>
.detail-section {
  border-bottom: 1px solid var(--ec-border-soft);
}

.head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  width: 100%;
  padding: 0.85rem 1.25rem;
  background: none;
  border: 0;
  font: inherit;
  color: inherit;
  text-align: left;
}

button.head {
  cursor: pointer;
}

button.head:hover {
  background: var(--ec-surface-muted);
}

h3 {
  flex: 0 0 7.5rem;
  margin: 0;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--ec-muted);
}

.summary {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
  font-size: 0.875rem;
}

.chevron {
  flex: none;
  color: var(--ec-subtle);
  transition: transform 0.15s ease;
}

.chevron.open {
  transform: rotate(180deg);
}

.body {
  padding: 0 1.25rem 1rem;
  font-size: 0.875rem;
}
</style>
