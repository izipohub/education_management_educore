<script setup lang="ts">
import { computed } from "vue";

/**
 * Magnitudes compared at a glance: one row per item (name, bar, figure), one hue, bars on a shared baseline.
 * Ordered items (a pipeline) keep their order; others come largest first from the caller. With `max`, each
 * row is a meter against its own limit (places filled, fees collected); a row at its limit shows `fullLabel`.
 */
const props = defineProps<{
  rows: { label: string; value: number; max?: number; note?: string }[];
  /** formats a figure (counts by default) */
  format?: (value: number) => string;
  fullLabel?: string;
  /** what the list shows, for screen readers */
  label: string;
}>();

const scale = computed(() => Math.max(1, ...props.rows.map((r) => r.max ?? r.value)));
const fmt = (v: number) => (props.format ? props.format(v) : v.toLocaleString("en-NA"));
const share = (r: { value: number; max?: number }) => Math.min(100, (r.value / (r.max || scale.value)) * 100);
const full = (r: { value: number; max?: number }) => Boolean(r.max) && r.value >= r.max!;
const describe = (r: { label: string; value: number; max?: number; note?: string }) =>
  r.max ? `${r.label}: ${fmt(r.value)} of ${fmt(r.max)}${r.note ? `, ${r.note}` : ""}` : `${r.label}: ${fmt(r.value)}`;
</script>

<template>
  <ul class="bars" :aria-label="label">
    <li v-for="r in rows" :key="r.label" class="row" :title="describe(r)" :aria-label="describe(r)">
      <span class="name">{{ r.label }}</span>
      <span class="track" :class="{ meter: r.max }" aria-hidden="true">
        <span class="fill" :class="{ full: full(r) }" :style="{ width: `${share(r)}%` }" />
      </span>
      <span class="figure">
        <template v-if="r.max">{{ fmt(r.value) }}<span class="ec-muted"> / {{ fmt(r.max) }}</span></template>
        <template v-else>{{ fmt(r.value) }}</template>
        <span v-if="full(r) && fullLabel" class="full-label">{{ fullLabel }}</span>
      </span>
    </li>
  </ul>
</template>

<style scoped>
.bars {
  display: grid;
  gap: 0.6rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.row {
  display: grid;
  grid-template-columns: minmax(6rem, 9rem) minmax(0, 1fr) 7.5rem;
  align-items: center;
  gap: 0.75rem;
  font-size: 0.85rem;
}

.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* a plain bar has no visible track; a meter's track is a lighter step of the same hue */
.track {
  height: 0.6rem;
  border-radius: 999px;
}

.track.meter {
  background: color-mix(in srgb, var(--ec-accent) 12%, white);
}

.fill {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: 999px;
  background: var(--ec-accent);
}

.fill.full {
  background: var(--ec-danger);
}

.figure {
  font-variant-numeric: tabular-nums;
  text-align: right;
  white-space: nowrap;
}

.full-label {
  margin-left: 0.4rem;
  color: var(--ec-danger);
  font-weight: 600;
  font-size: 0.75rem;
}

@media (max-width: 479px) {
  .row {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .track {
    grid-column: 1 / -1;
    grid-row: 2;
  }
}
</style>
