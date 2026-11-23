<script setup lang="ts">
import { computed, ref } from "vue";

/**
 * One whole split into a few parts (online / paper, entry pathways, offer responses). At most four slices in the
 * chart's fixed colour order; more fold into "Other". A legend with each part's figure and share always sits
 * beside it, so no part is told by colour alone; hovering a slice or a legend row highlights the pair.
 */
const props = withDefaults(defineProps<{ slices: { label: string; value: number }[]; label: string; centreLabel?: string }>(), {
  centreLabel: "Total",
});

/** the chart colours, in fixed order (validated as a set; see docs/architecture/ui-conventions.md) */
const COLOURS = ["var(--ec-series-1)", "var(--ec-series-2)", "var(--ec-series-3)", "var(--ec-series-4)"];
const MAX = 4;

const parts = computed(() => {
  const rows = props.slices.filter((s) => s.value > 0);
  if (rows.length <= MAX) return rows;
  const kept = rows.slice(0, MAX - 1);
  return [...kept, { label: "Other", value: rows.slice(MAX - 1).reduce((sum, r) => sum + r.value, 0) }];
});
const total = computed(() => parts.value.reduce((sum, p) => sum + p.value, 0));
const pct = (v: number) => (total.value ? Math.round((v / total.value) * 100) : 0);

const R = 42;
const C = 2 * Math.PI * R;
/** each slice as a dash on one circle, with a small gap between slices (the surface shows through) */
const arcs = computed(() => {
  const gap = parts.value.length > 1 ? 1.2 : 0;
  let offset = 0;
  return parts.value.map((p, i) => {
    const length = (p.value / (total.value || 1)) * C;
    const arc = { ...p, colour: COLOURS[i]!, dash: `${Math.max(length - gap, 0.5)} ${C}`, offset: -offset };
    offset += length;
    return arc;
  });
});
const active = ref<number | null>(null);
</script>

<template>
  <div class="donut" role="group" :aria-label="label">
    <div v-if="!total" class="ec-muted none">Nothing yet</div>
    <template v-else>
      <svg viewBox="0 0 100 100" class="donut-ring" aria-hidden="true">
        <circle cx="50" cy="50" :r="R" class="track" />
        <circle
          v-for="(a, i) in arcs"
          :key="a.label"
          cx="50"
          cy="50"
          :r="R"
          class="slice"
          :class="{ dim: active !== null && active !== i }"
          :stroke="a.colour"
          :stroke-dasharray="a.dash"
          :stroke-dashoffset="a.offset"
          transform="rotate(-90 50 50)"
          @mouseenter="active = i"
          @mouseleave="active = null"
        >
          <title>{{ a.label }}: {{ a.value }} ({{ pct(a.value) }}%)</title>
        </circle>
        <text x="50" y="49" class="centre-value">{{ active !== null ? arcs[active]!.value : total }}</text>
        <text x="50" y="61" class="centre-label">{{ active !== null ? `${pct(arcs[active]!.value)}%` : centreLabel }}</text>
      </svg>
      <ul class="legend">
        <li
          v-for="(a, i) in arcs"
          :key="a.label"
          :class="{ dim: active !== null && active !== i }"
          @mouseenter="active = i"
          @mouseleave="active = null"
        >
          <span class="key" :style="{ background: a.colour }" aria-hidden="true" />
          <span class="name">{{ a.label }}</span>
          <span class="figure">{{ a.value }}</span>
          <span class="share">{{ pct(a.value) }}%</span>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.donut {
  display: grid;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  align-items: center;
  gap: 1.25rem;
}

.none {
  grid-column: 1 / -1;
  padding: 1rem 0;
}

.donut-ring {
  width: 100%;
  display: block;
}

.track {
  fill: none;
  stroke: var(--ec-border-soft);
  stroke-width: 12;
}

.slice {
  fill: none;
  stroke-width: 12;
  cursor: default;
  transition: opacity 0.15s ease;
}

.dim {
  opacity: 0.35;
}

.centre-value {
  fill: var(--ec-ink);
  font-size: 17px;
  font-weight: 650;
  text-anchor: middle;
  font-variant-numeric: tabular-nums;
}

.centre-label {
  fill: var(--ec-muted);
  font-size: 8px;
  text-anchor: middle;
}

.legend {
  display: grid;
  gap: 0.45rem;
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: 0.85rem;
}

.legend li {
  display: grid;
  grid-template-columns: 0.65rem minmax(0, 1fr) auto 2.75rem;
  align-items: center;
  gap: 0.5rem;
  transition: opacity 0.15s ease;
}

.key {
  width: 0.65rem;
  height: 0.65rem;
  border-radius: 3px;
}

.name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.figure {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.share {
  color: var(--ec-muted);
  text-align: right;
  font-variant-numeric: tabular-nums;
}

@media (max-width: 479px) {
  .donut {
    grid-template-columns: 6rem minmax(0, 1fr);
    gap: 0.9rem;
  }
}
</style>
