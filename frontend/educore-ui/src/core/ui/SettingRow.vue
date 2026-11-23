<script setup lang="ts">
/**
 * One setting: what it is and a line on what it does on the left, the control on the right. Rows stack inside an
 * EcPanel; on a narrow screen the control drops under the label.
 */
defineProps<{ label: string; help?: string; for?: string }>();
</script>

<template>
  <div class="setting-row">
    <div class="text">
      <label v-if="$props.for" :for="$props.for" class="label">{{ label }}</label>
      <span v-else class="label">{{ label }}</span>
      <p v-if="help" class="ec-muted">{{ help }}</p>
    </div>
    <div class="control"><slot /></div>
  </div>
</template>

<style scoped>
.setting-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(12rem, 18rem);
  align-items: center;
  gap: 0.5rem 2rem;
  padding: 0.9rem 0;
  border-top: 1px solid var(--ec-border-soft);
}

.setting-row:first-child {
  border-top: 0;
  padding-top: 0;
}

.setting-row:last-child {
  padding-bottom: 0;
}

.label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--ec-text);
}

.text p {
  margin: 0.15rem 0 0;
}

.control {
  display: flex;
  justify-content: flex-end;
  min-width: 0;
}

/* fields fill the control column; a switch keeps its own size */
.control > :deep(:not(.p-toggleswitch)) {
  width: 100%;
}

@media (max-width: 639px) {
  .setting-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .control {
    justify-content: flex-start;
  }
}
</style>
