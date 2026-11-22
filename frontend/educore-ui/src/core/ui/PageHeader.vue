<script setup lang="ts">
/** Every screen's title row: title, one line of context, actions on the right; filters or tabs below */
defineProps<{ title: string; subtitle?: string }>();
</script>

<template>
  <header class="page-header">
    <div class="titles">
      <h1>{{ title }}</h1>
      <p v-if="subtitle" class="ec-muted">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="actions"><slot name="actions" /></div>
    <div v-if="$slots.default" class="below"><slot /></div>
  </header>
</template>

<style scoped>
.page-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.75rem 1rem;
}

h1 {
  margin: 0;
  font-size: 1.375rem;
  font-weight: 650;
  letter-spacing: -0.01em;
}

.titles p {
  margin: 0.2rem 0 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.below {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
</style>
