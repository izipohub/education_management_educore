<script setup lang="ts">
/** A form field: label above, the control, then a hint or the error (never both) */
defineProps<{ label: string; for?: string; hint?: string; error?: string; labelId?: string }>();
</script>

<template>
  <div class="ec-field" :class="{ invalid: error }">
    <label :id="labelId" :for="$props.for" class="label">{{ label }}</label>
    <slot />
    <small v-if="error" class="error" role="alert">{{ error }}</small>
    <small v-else-if="hint" class="hint">{{ hint }}</small>
  </div>
</template>

<style scoped>
.ec-field {
  display: grid;
  gap: 0.35rem;
  min-width: 0;
}

.label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--ec-text);
}

.hint {
  font-size: 0.75rem;
  color: var(--ec-muted);
}

.error {
  font-size: 0.75rem;
  color: var(--ec-danger);
}
</style>
