<script setup lang="ts">
/**
 * A panel of a record page or dashboard: a title, an optional note or action on the right, the content, and an
 * optional footer for the panel's own action. `flush` lets a table run edge to edge.
 */
withDefaults(defineProps<{ title: string; note?: string; flush?: boolean }>(), { note: undefined, flush: false });
</script>

<template>
  <section class="panel ec-card">
    <header class="head">
      <h2>{{ title }}</h2>
      <div v-if="note || $slots.note" class="note"><slot name="note"><span class="ec-muted">{{ note }}</span></slot></div>
    </header>
    <div class="body" :class="{ flush }"><slot /></div>
    <footer v-if="$slots.footer" class="foot"><slot name="footer" /></footer>
  </section>
</template>

<style scoped>
.panel {
  overflow: hidden;
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem 0.75rem;
  padding: 0.9rem 1.25rem;
  border-bottom: 1px solid var(--ec-border-soft);
}

h2 {
  margin: 0;
  font-size: 1.0625rem;
}

.note {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.body {
  padding: 1rem 1.25rem;
  font-size: 0.875rem;
}

.body.flush {
  padding: 0;
}

.body.flush :deep(.ec-table th:first-child),
.body.flush :deep(.ec-table td:first-child) {
  padding-left: 1.25rem;
}

.body.flush :deep(.ec-table th:last-child),
.body.flush :deep(.ec-table td:last-child) {
  padding-right: 1.25rem;
}

.foot {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  border-top: 1px solid var(--ec-border-soft);
  background: var(--ec-surface-muted);
}
</style>
