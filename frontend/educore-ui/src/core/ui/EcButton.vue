<script setup lang="ts">
import type { Component } from "vue";

/**
 * The one button. Variants by what the button does:
 * - primary: the one thing to do here (the loud accent; at most one per view or pane)
 * - secondary: other actions
 * - ghost: low-key actions in a row or a section (Edit, View all, Cancel)
 * - danger: actions that refuse or remove (outlined; the confirm step in a modal uses danger too)
 * - quiet-danger: a refusal inside a row or section (red text, no border)
 */
withDefaults(
  defineProps<{
    label?: string;
    variant?: "primary" | "secondary" | "ghost" | "danger" | "quiet-danger";
    size?: "sm" | "md";
    icon?: Component;
    loading?: boolean;
    disabled?: boolean;
    type?: "button" | "submit";
    block?: boolean;
  }>(),
  { label: undefined, variant: "secondary", size: "md", icon: undefined, loading: false, disabled: false, type: "button", block: false },
);
</script>

<template>
  <button
    :type="type"
    class="ec-button"
    :class="[variant, size, { block, loading, 'icon-only': !label && !$slots.default }]"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
  >
    <span v-if="loading" class="spinner" aria-hidden="true" />
    <component :is="icon" v-else-if="icon" :size="size === 'sm' ? 15 : 16" :stroke-width="2" aria-hidden="true" />
    <span v-if="label || $slots.default" class="text"><slot>{{ label }}</slot></span>
  </button>
</template>

<style scoped>
.ec-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  height: 2.375rem;
  padding: 0 0.95rem;
  border: 1px solid transparent;
  border-radius: var(--ec-radius-sm);
  font: inherit;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color 0.12s ease,
    border-color 0.12s ease,
    color 0.12s ease,
    box-shadow 0.12s ease;
}

.ec-button.sm {
  height: 2rem;
  padding: 0 0.7rem;
  font-size: 0.8125rem;
}

.ec-button.icon-only {
  width: 2.375rem;
  padding: 0;
}

.ec-button.sm.icon-only {
  width: 2rem;
}

.ec-button.block {
  width: 100%;
}

.ec-button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.ec-button:focus-visible {
  outline: 2px solid var(--ec-accent);
  outline-offset: 2px;
}

/* the loud 10% */
.primary {
  background: var(--ec-loud);
  color: var(--ec-on-loud);
  box-shadow: 0 1px 0 rgb(0 0 0 / 0.06);
}

.primary:not(:disabled):hover {
  background: color-mix(in srgb, var(--ec-loud) 88%, black);
}

.secondary {
  background: var(--ec-surface);
  border-color: var(--ec-border);
  color: var(--ec-ink);
}

.secondary:not(:disabled):hover {
  background: var(--ec-surface-muted);
  border-color: color-mix(in srgb, var(--ec-border) 70%, var(--ec-ink));
}

.ghost {
  background: transparent;
  color: var(--ec-accent);
}

.ghost:not(:disabled):hover {
  background: var(--ec-accent-soft);
}

.danger {
  background: var(--ec-surface);
  border-color: color-mix(in srgb, var(--ec-danger) 35%, white);
  color: var(--ec-danger);
}

.danger:not(:disabled):hover {
  background: color-mix(in srgb, var(--ec-danger) 6%, white);
}

.quiet-danger {
  background: transparent;
  color: var(--ec-danger);
}

.quiet-danger:not(:disabled):hover {
  background: color-mix(in srgb, var(--ec-danger) 6%, white);
}

.spinner {
  width: 0.9rem;
  height: 0.9rem;
  border: 2px solid currentColor;
  border-right-color: transparent;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .spinner {
    animation-duration: 2s;
  }
}
</style>
