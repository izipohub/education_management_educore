<script setup lang="ts">
import { type RouteLocationRaw, RouterLink } from "vue-router";

/** A headline number: label, value, one line of context, and where to act on it */
defineProps<{ label: string; value: string | number; hint?: string; to?: RouteLocationRaw; action?: string }>();
</script>

<template>
  <article class="stat ec-card">
    <p class="label">{{ label }}</p>
    <p class="value">{{ value }}</p>
    <p v-if="hint" class="ec-muted">{{ hint }}</p>
    <RouterLink v-if="to" :to="to" class="action">{{ action ?? "Open" }} →</RouterLink>
  </article>
</template>

<style scoped>
.stat {
  display: grid;
  align-content: start;
  gap: 0.25rem;
  padding: 1rem 1.1rem;
}

p {
  margin: 0;
}

.label {
  font-size: 0.8125rem;
  color: var(--ec-muted);
}

.value {
  font-size: 1.75rem;
  font-weight: 650;
  line-height: 1.15;
  color: var(--ec-ink);
}

.action {
  margin-top: 0.35rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--ec-accent);
  text-decoration: none;
}

.action:hover {
  text-decoration: underline;
}
</style>
