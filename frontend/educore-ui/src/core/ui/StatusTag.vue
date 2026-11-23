<script setup lang="ts">
import { computed } from "vue";
import { type StatusKind, statusTag } from "@/core/status";

/**
 * A stored status shown the same way everywhere (label and tone from core/status.ts): quiet text on a neutral
 * pill, with a small dot carrying the tone, so a list of statuses stays calm and the words do the work.
 */
const props = defineProps<{ kind: StatusKind; value: string | null | undefined }>();
const tag = computed(() => statusTag(props.kind, props.value));
</script>

<template>
  <span class="status-tag" :class="`tone-${tag.severity}`"><span class="dot" aria-hidden="true" />{{ tag.label }}</span>
</template>

<style scoped>
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.12rem 0.55rem;
  border: 1px solid var(--ec-border);
  border-radius: 999px;
  background: var(--ec-surface);
  color: var(--ec-text);
  font-size: 0.75rem;
  font-weight: 500;
  line-height: 1.4;
  white-space: nowrap;
}

.dot {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  background: var(--ec-subtle);
}

.tone-success .dot {
  background: var(--ec-success);
}

.tone-info .dot {
  background: var(--ec-accent);
}

.tone-warn .dot {
  background: var(--ec-warn);
}

.tone-danger .dot {
  background: var(--ec-danger);
}

.tone-contrast .dot {
  background: var(--ec-ink);
}
</style>
