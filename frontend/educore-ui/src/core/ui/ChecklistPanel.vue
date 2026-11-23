<script setup lang="ts">
import { Circle } from "@lucide/vue";
import EcPanel from "./EcPanel.vue";

/** What is still outstanding on a record, in words: a neutral list, never a coloured banner */
defineProps<{ items: string[]; title?: string }>();
</script>

<template>
  <EcPanel v-if="items.length" :title="title ?? 'Outstanding'">
    <ul class="checklist">
      <li v-for="item in items" :key="item"><Circle :size="12" :stroke-width="2" aria-hidden="true" />{{ item }}</li>
    </ul>
  </EcPanel>
</template>

<style scoped>
.checklist {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

li {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}

li svg {
  flex: none;
  color: var(--ec-subtle);
  transform: translateY(1px);
}
</style>
