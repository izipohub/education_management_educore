<script setup lang="ts">
import { computed } from "vue";
import type { Slot } from "./timetable";

/** A week of class times: a column per day, each time placed by its hours; a time opens on click */
const props = defineProps<{ slots: Slot[]; days: string[]; clickable?: boolean }>();
const emit = defineEmits<{ open: [Slot] }>();

const minutes = (t: string) => {
  const [h, m] = t.split(":").map(Number);
  return h * 60 + m;
};
// the hours shown: from the earliest start to the latest end (08:00–17:00 at least)
const first = computed(() => Math.min(8 * 60, ...props.slots.map((s) => minutes(s.start_time))));
const last = computed(() => Math.max(17 * 60, ...props.slots.map((s) => minutes(s.end_time))));
const hours = computed(() => {
  const out: string[] = [];
  for (let m = Math.floor(first.value / 60) * 60; m < last.value; m += 60) out.push(`${String(m / 60).padStart(2, "0")}:00`);
  return out;
});
// Saturday only when something is on it
const shown = computed(() => props.days.filter((d) => d !== "Saturday" || props.slots.some((s) => s.day === "Saturday")));
const HOUR = 52; // px per hour
const top = (s: Slot) => ((minutes(s.start_time) - Math.floor(first.value / 60) * 60) / 60) * HOUR;
const height = (s: Slot) => ((minutes(s.end_time) - minutes(s.start_time)) / 60) * HOUR - 4;
const byDay = computed(() => Object.fromEntries(shown.value.map((d) => [d, props.slots.filter((s) => s.day === d)])));
// times that overlap on a day (other rooms) share the column
function lanes(day: string) {
  const list = byDay.value[day] ?? [];
  const placed: { slot: Slot; lane: number; of: number }[] = [];
  for (const s of list) {
    const busy = placed.filter((p) => minutes(p.slot.start_time) < minutes(s.end_time) && minutes(p.slot.end_time) > minutes(s.start_time));
    let lane = 0;
    while (busy.some((p) => p.lane === lane)) lane++;
    placed.push({ slot: s, lane, of: 1 });
  }
  for (const p of placed) {
    const overlapping = placed.filter((q) => minutes(q.slot.start_time) < minutes(p.slot.end_time) && minutes(q.slot.end_time) > minutes(p.slot.start_time));
    p.of = Math.max(...overlapping.map((q) => q.lane)) + 1;
  }
  return placed;
}
</script>

<template>
  <div class="week" :style="{ '--days': shown.length }">
    <div class="corner" />
    <div v-for="d in shown" :key="d" class="day-head">{{ d }}</div>
    <div class="hours" :style="{ height: `${hours.length * HOUR}px` }">
      <div v-for="h in hours" :key="h" class="hour" :style="{ height: `${HOUR}px` }">{{ h }}</div>
    </div>
    <div v-for="d in shown" :key="`col-${d}`" class="col" :style="{ height: `${hours.length * HOUR}px` }">
      <div v-for="h in hours" :key="h" class="line" :style="{ height: `${HOUR}px` }" />
      <component
        :is="clickable ? 'button' : 'div'"
        v-for="p in lanes(d)"
        :key="p.slot.name"
        :type="clickable ? 'button' : undefined"
        class="slot"
        :class="`k-${p.slot.kind.toLowerCase()}`"
        :style="{ top: `${top(p.slot)}px`, height: `${height(p.slot)}px`, left: `calc(${(p.lane / p.of) * 100}% + 2px)`, width: `calc(${100 / p.of}% - 4px)` }"
        :aria-label="`${p.slot.code} ${p.slot.day} ${p.slot.start_time}–${p.slot.end_time}, ${p.slot.room_name}`"
        @click="clickable && emit('open', p.slot)"
      >
        <span class="code">{{ p.slot.code }}</span>
        <span class="meta">{{ p.slot.start_time }}–{{ p.slot.end_time }} · {{ p.slot.room_name }}</span>
        <span v-if="p.slot.kind !== 'Lecture'" class="meta">{{ p.slot.kind }}</span>
        <span v-if="p.slot.lecturers.length" class="meta">{{ p.slot.lecturers.join(", ") }}</span>
      </component>
    </div>
  </div>
</template>

<style scoped>
.week {
  display: grid;
  grid-template-columns: 3.25rem repeat(var(--days), minmax(7.5rem, 1fr));
  overflow-x: auto;
}

.day-head {
  padding: 0.5rem;
  border-bottom: 1px solid var(--ec-border);
  font-size: 0.8125rem;
  font-weight: 600;
  text-align: center;
}

.hours .hour {
  padding-right: 0.4rem;
  color: var(--ec-muted);
  font-size: 0.7rem;
  text-align: right;
  transform: translateY(-0.4rem);
}

.col {
  position: relative;
  border-left: 1px solid var(--ec-border);
}

.line {
  border-bottom: 1px dashed var(--ec-border);
}

.slot {
  position: absolute;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  overflow: hidden;
  padding: 0.3rem 0.4rem;
  border: 1px solid color-mix(in srgb, var(--ec-primary, #1e3a8a) 30%, transparent);
  border-left: 3px solid var(--ec-primary, #1e3a8a);
  border-radius: 6px;
  background: color-mix(in srgb, var(--ec-primary, #1e3a8a) 8%, white);
  color: inherit;
  font: inherit;
  text-align: left;
}

button.slot {
  cursor: pointer;
}

button.slot:hover,
button.slot:focus-visible {
  background: color-mix(in srgb, var(--ec-primary, #1e3a8a) 14%, white);
}

.k-practical {
  border-left-color: #b45309;
  background: #fffbeb;
}

.k-tutorial {
  border-left-color: #047857;
  background: #ecfdf5;
}

.code {
  font-size: 0.8rem;
  font-weight: 600;
}

.meta {
  color: var(--ec-muted);
  font-size: 0.7rem;
  line-height: 1.25;
}
</style>
