<script setup lang="ts">
import { Inbox } from "@lucide/vue";

/** Nothing to show: an icon, one line, and an optional hint */
defineProps<{ title: string; hint?: string }>();
</script>

<template>
  <div class="empty">
    <Inbox :size="28" :stroke-width="1.5" aria-hidden="true" />
    <p class="title">{{ title }}</p>
    <p v-if="hint" class="ec-muted">{{ hint }}</p>
  </div>
</template>

<style scoped>
.empty {
  display: grid;
  justify-items: center;
  gap: 0.35rem;
  padding: 2.5rem 1rem;
  color: var(--ec-subtle);
  text-align: center;
}

p {
  margin: 0;
}

.title {
  color: var(--ec-muted);
  font-weight: 500;
}
</style>
