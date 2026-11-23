<script setup lang="ts">
import { computed, ref } from "vue";

/**
 * A count over time (one series, in the brand's primary colour): a 2px line over a faint area, three recessive
 * gridlines, the latest value labelled. Hovering anywhere shows a crosshair on the nearest point and its figure.
 * `points` are oldest first; labels are YYYY-MM (shown as short month names).
 */
const props = defineProps<{ points: { label: string; value: number }[]; label: string }>();

const W = 600;
const H = 200;
const PAD = { top: 16, right: 16, bottom: 28, left: 32 };
const innerW = W - PAD.left - PAD.right;
const innerH = H - PAD.top - PAD.bottom;

/** a round top for the scale: 1, 2, 5, 10, 20, 50 ... */
const top = computed(() => {
  const max = Math.max(1, ...props.points.map((p) => p.value));
  const step = 10 ** Math.floor(Math.log10(max));
  return [1, 2, 5, 10].map((m) => m * step).find((v) => v >= max) ?? max;
});
const x = (i: number) => PAD.left + (props.points.length > 1 ? (i / (props.points.length - 1)) * innerW : innerW / 2);
const y = (v: number) => PAD.top + innerH - (v / top.value) * innerH;
const line = computed(() => props.points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" "));
const area = computed(() =>
  props.points.length ? `${line.value} L${x(props.points.length - 1).toFixed(1)},${y(0)} L${x(0).toFixed(1)},${y(0)} Z` : "",
);
/** counts: whole numbers only on the scale */
const grid = computed(() => [0, top.value / 2, top.value].filter((g) => Number.isInteger(g)));

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const month = (label: string) => {
  const [year, m] = label.split("-");
  const name = MONTHS[Number(m) - 1] ?? label;
  return m === "01" ? `${name} ${year}` : name;
};
/** every other month on a narrow axis */
const showTick = (i: number) => props.points.length <= 7 || i % 2 === (props.points.length - 1) % 2;

const hover = ref<number | null>(null);
function move(event: PointerEvent) {
  const svg = event.currentTarget as SVGSVGElement;
  const box = svg.getBoundingClientRect();
  const at = ((event.clientX - box.left) / box.width) * W;
  const step = props.points.length > 1 ? innerW / (props.points.length - 1) : innerW;
  hover.value = Math.min(props.points.length - 1, Math.max(0, Math.round((at - PAD.left) / step)));
}
const last = computed(() => props.points.length - 1);
const tip = computed(() => (hover.value === null ? null : { ...props.points[hover.value]!, x: x(hover.value), y: y(props.points[hover.value]!.value) }));
</script>

<template>
  <figure class="line-chart" :aria-label="label">
    <svg :viewBox="`0 0 ${W} ${H}`" role="img" :aria-label="`${label}: ${points.map((p) => `${month(p.label)} ${p.value}`).join(', ')}`" @pointermove="move" @pointerleave="hover = null">
      <g class="grid">
        <template v-for="g in grid" :key="g">
          <line :x1="PAD.left" :x2="W - PAD.right" :y1="y(g)" :y2="y(g)" />
          <text :x="PAD.left - 8" :y="y(g) + 4" class="axis right">{{ g }}</text>
        </template>
      </g>
      <path :d="area" class="area" />
      <path :d="line" class="stroke" />
      <g v-for="(p, i) in points" :key="p.label">
        <text v-if="showTick(i)" :x="x(i)" :y="H - 8" class="axis middle">{{ month(p.label) }}</text>
      </g>
      <!-- the latest figure, labelled -->
      <template v-if="points.length && hover === null">
        <circle :cx="x(last)" :cy="y(points[last]!.value)" r="4" class="dot" />
        <text :x="x(last) - 8" :y="y(points[last]!.value) - 10" class="value end">{{ points[last]!.value }}</text>
      </template>
      <template v-if="tip">
        <line :x1="tip.x" :x2="tip.x" :y1="PAD.top" :y2="PAD.top + innerH" class="crosshair" />
        <circle :cx="tip.x" :cy="tip.y" r="4.5" class="dot" />
      </template>
    </svg>
    <div v-if="tip" class="tooltip" :style="{ left: `${(tip.x / W) * 100}%` }" role="status">
      <span class="ec-muted">{{ month(tip.label) }}</span>
      <strong>{{ tip.value }}</strong>
    </div>
  </figure>
</template>

<style scoped>
.line-chart {
  position: relative;
  margin: 0;
}

svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
  touch-action: pan-y;
}

.grid line {
  stroke: var(--ec-border-soft);
  stroke-width: 1;
}

.axis {
  fill: var(--ec-muted);
  font-size: 11px;
}

.axis.right {
  text-anchor: end;
}

.axis.middle {
  text-anchor: middle;
}

.area {
  fill: color-mix(in srgb, var(--ec-accent) 9%, transparent);
}

.stroke {
  fill: none;
  stroke: var(--ec-accent);
  stroke-width: 2;
  stroke-linejoin: round;
  stroke-linecap: round;
}

.dot {
  fill: var(--ec-accent);
  stroke: var(--ec-surface);
  stroke-width: 2;
}

.value {
  fill: var(--ec-ink);
  font-size: 12px;
  font-weight: 600;
}

.value.end {
  text-anchor: end;
}

.crosshair {
  stroke: var(--ec-subtle);
  stroke-width: 1;
  stroke-dasharray: 3 3;
}

.tooltip {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  display: grid;
  gap: 0.05rem;
  padding: 0.35rem 0.6rem;
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface);
  box-shadow: var(--ec-shadow);
  font-size: 0.8rem;
  text-align: center;
  white-space: nowrap;
  pointer-events: none;
}
</style>
