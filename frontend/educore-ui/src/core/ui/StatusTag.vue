<script setup lang="ts">
import Tag from "primevue/tag";
import { computed } from "vue";
import { type StatusKind, statusTag } from "@/core/status";

/** A stored status shown the same way everywhere (label and colour from core/status.ts) */
const props = defineProps<{ kind: StatusKind; value: string | null | undefined }>();
const tag = computed(() => statusTag(props.kind, props.value));
</script>

<template>
  <Tag :value="tag.label" :severity="tag.severity" class="status-tag" />
</template>

<style scoped>
.status-tag {
  white-space: nowrap;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
}
</style>
