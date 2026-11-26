<script setup lang="ts">
import { onMounted, ref } from "vue";
import { type Slot, myWeek } from "./timetable";

/** The signed-in lecturer's or student's classes this semester: a row per class time, the day named once.
 * card: a card like the class cards on My teaching; lecturers: show who teaches (for students). */
withDefaults(defineProps<{ card?: boolean; lecturers?: boolean }>(), { card: false, lecturers: true });
const week = ref<{ academic_year: string | null; semester: string; slots: Slot[] } | null>(null);
onMounted(async () => {
  week.value = await myWeek().catch(() => null);
});
const firstOfDay = (i: number) => i === 0 || week.value!.slots[i - 1].day !== week.value!.slots[i].day;
</script>

<template>
  <section v-if="week && week.slots.length" :class="card ? 'week-card' : 'block'">
    <h2 v-if="card" class="card-title">This week <span class="when">{{ week.semester }} {{ week.academic_year }}</span></h2>
    <h2 v-else class="block-title">Timetable <span class="when">({{ week.semester }} {{ week.academic_year }})</span></h2>
    <div :class="{ box: !card }">
    <table class="ec-table week">
      <thead>
        <tr>
          <th>Day</th>
          <th>Time</th>
          <th>Course</th>
          <th>Room</th>
          <th v-if="lecturers" class="wide">Lecturer</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="(s, i) in week.slots" :key="s.name" :class="{ 'new-day': firstOfDay(i) && i > 0 }">
          <td class="day">{{ firstOfDay(i) ? s.day : "" }}</td>
          <td class="ec-nowrap">{{ s.start_time }}–{{ s.end_time }}</td>
          <td>
            <span class="code">{{ s.code }}</span> {{ s.course_name }}
            <span v-if="s.kind !== 'Lecture'" class="kind">{{ s.kind }}</span>
          </td>
          <td>{{ s.room_name }}</td>
          <td v-if="lecturers" class="wide ec-muted">{{ s.lecturers.join(", ") }}</td>
        </tr>
      </tbody>
    </table>
    </div>
  </section>
</template>

<style scoped>
.week-card {
  margin-bottom: 1rem;
  padding: 1.25rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
}

.card-title {
  margin: 0 0 0.75rem;
  font-size: 1.1rem;
}

.block {
  margin-bottom: 1.5rem;
}

/* as the other sections of My studies */
.block-title {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6b7280;
}

.box {
  overflow: hidden;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
}

.when {
  margin-left: 0.25rem;
  color: var(--ec-muted);
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
}

.week {
  width: 100%;
}

.day {
  width: 7rem;
  font-weight: 600;
}

.new-day td {
  border-top: 2px solid var(--ec-border);
}

.code {
  color: var(--color-brand-navy);
  font-weight: 600;
}

.kind {
  margin-left: 0.35rem;
  padding: 0.05rem 0.4rem;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
  font-size: 0.7rem;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .wide {
    display: none;
  }
}
</style>
