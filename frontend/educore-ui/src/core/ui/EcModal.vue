<script setup lang="ts">
import Dialog from "primevue/dialog";

/**
 * A small modal for one decision that needs a reason or a choice. Records and editing belong in the docked side
 * window (SplitView / SidePanel); a modal only asks, then closes. Focus is kept inside while open; Escape closes.
 */
withDefaults(defineProps<{ title: string; description?: string; size?: "sm" | "md" | "lg" }>(), { description: undefined, size: "sm" });
const open = defineModel<boolean>("open", { required: true });
</script>

<template>
  <Dialog
    v-model:visible="open"
    modal
    :header="title"
    :draggable="false"
    :dismissable-mask="true"
    :style="{ width: `min(${size === 'sm' ? 28 : size === 'md' ? 36 : 46}rem, calc(100vw - 32px))` }"
    :pt="{
      root: { class: 'ec-modal' },
      header: { class: 'ec-modal-header' },
      content: { class: 'ec-modal-content' },
      footer: { class: 'ec-modal-footer' },
    }"
  >
    <p v-if="description" class="description">{{ description }}</p>
    <div class="body"><slot /></div>
    <template v-if="$slots.footer" #footer><slot name="footer" /></template>
  </Dialog>
</template>

<style scoped>
.description {
  margin: 0 0 0.75rem;
  color: var(--ec-muted);
  font-size: 0.875rem;
}

.body {
  display: grid;
  gap: 0.75rem;
}
</style>

<style>
/* calm: no heavy shadow, the same radius and borders as the cards */
.ec-modal.p-dialog {
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius);
  box-shadow: 0 12px 32px rgb(16 20 30 / 0.12);
}

.ec-modal .ec-modal-header {
  padding: 1.1rem 1.25rem 0.5rem;
}

.ec-modal .p-dialog-title {
  font-size: 1rem;
  font-weight: 650;
  color: var(--ec-ink);
}

.ec-modal .ec-modal-content {
  padding: 0.25rem 1.25rem 1rem;
}

.ec-modal .ec-modal-footer {
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: var(--ec-surface-muted);
  border-top: 1px solid var(--ec-border-soft);
  border-radius: 0 0 var(--ec-radius) var(--ec-radius);
}
</style>
