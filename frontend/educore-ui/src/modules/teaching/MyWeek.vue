<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import WeekGrid from "./WeekGrid.vue";
import { type Slot, myWeek } from "./timetable";

/** The signed-in lecturer's or student's week this semester, as a week grid (its own tab on My modules and My
 * studies); lecturers: show who teaches each class (for students) */
const props = withDefaults(defineProps<{ lecturers?: boolean }>(), { lecturers: true });
const week = ref<{ academic_year: string | null; semester: string; slots: Slot[] } | null>(null);
const loaded = ref(false);
onMounted(async () => {
  week.value = await myWeek().catch(() => null);
  loaded.value = true;
});
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const hours = computed(() =>
  (week.value?.slots ?? []).reduce((sum, s) => {
    const [h1, m1] = s.start_time.split(":").map(Number);
    const [h2, m2] = s.end_time.split(":").map(Number);
    return sum + (h2 * 60 + m2 - h1 * 60 - m1) / 60;
  }, 0),
);
const modules = computed(() => new Set((week.value?.slots ?? []).map((s) => s.course)).size);
</script>

<template>
  <section class="my-week ec-card">
    <header v-if="week" class="head">
      <h2>{{ week.semester }} {{ week.academic_year }}</h2>
      <span v-if="week.slots.length" class="ec-muted">{{ modules }} {{ modules === 1 ? "module" : "modules" }} · {{ hours }} hours a week</span>
      <span class="legend">
        <span class="key lecture">Lecture</span><span class="key practical">Practical</span><span class="key tutorial">Tutorial</span>
      </span>
    </header>
    <WeekGrid v-if="week?.slots.length" :slots="week.slots" :days="DAYS" :hide-lecturers="!props.lecturers" />
    <p v-else-if="loaded" class="none ec-muted">No class times this semester yet. The timetable office publishes them before classes start.</p>
  </section>
</template>

<style scoped>
.my-week {
  overflow: hidden;
  padding: 0 0.75rem 0.75rem 0;
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem 1rem;
  padding: 1rem 0 0.75rem 1.25rem;
}

h2 {
  margin: 0;
  font-size: 1.1rem;
}

.legend {
  display: inline-flex;
  gap: 0.75rem;
  margin-left: auto;
  font-size: 0.75rem;
}

.key {
  padding-left: 0.6rem;
  border-left: 3px solid var(--ec-primary, #1e3a8a);
}

.key.practical {
  border-left-color: #b45309;
}

.key.tutorial {
  border-left-color: #047857;
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
}
</style>
