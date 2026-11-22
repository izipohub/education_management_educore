<script setup lang="ts">
/**
 * A record docked in a SplitView: header (title, context, tags), sections that scroll, and the actions pinned
 * at the bottom so they are always in reach.
 */
defineProps<{ title: string; subtitle?: string }>();
</script>

<template>
  <div class="detail">
    <header class="head">
      <div class="titles">
        <h2>{{ title }}</h2>
        <p v-if="subtitle" class="ec-muted">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.tags" class="tags"><slot name="tags" /></div>
      <div v-if="$slots.notice" class="notice"><slot name="notice" /></div>
    </header>
    <div class="body"><slot /></div>
    <footer v-if="$slots.actions" class="actions"><slot name="actions" /></footer>
  </div>
</template>

<style scoped>
.detail {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.5rem 1rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--ec-border);
}

h2 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 650;
}

.titles p {
  margin: 0.15rem 0 0;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  align-items: start;
  justify-content: flex-end;
  gap: 0.35rem;
}

.notice {
  grid-column: 1 / -1;
}

.body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: var(--ec-surface-muted);
  border-top: 1px solid var(--ec-border);
}
</style>
