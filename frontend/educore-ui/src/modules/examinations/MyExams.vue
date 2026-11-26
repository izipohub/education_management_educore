<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { formatDate, fromIsoDate } from "@/core/format";
import { type Paper, getMyExams } from "./examTimetable";

/** The signed-in student's examination papers, or the member of staff's invigilation, once the timetable is
 * published (on the Timetable tab of My studies and My modules); papers already written are kept, greyed */
const props = defineProps<{ duties?: boolean }>();
const papers = ref<Paper[]>([]);
onMounted(async () => {
  const mine = await getMyExams().catch(() => null);
  papers.value = (props.duties ? mine?.duties : mine?.papers) ?? [];
});
const upcoming = computed(() => papers.value.filter((p) => !p.written).length);
const weekday = (iso: string) => fromIsoDate(iso).toLocaleDateString("en-GB", { weekday: "short" });
</script>

<template>
  <section v-if="papers.length" class="ec-card exams">
    <header class="head">
      <h2>{{ duties ? "Invigilation" : "Examinations" }}</h2>
      <span class="ec-muted">{{ papers[0].session }}{{ upcoming ? ` · ${upcoming} to come` : " · all written" }}</span>
    </header>
    <table class="ec-table">
      <thead>
        <tr><th>Date</th><th>Time</th><th>Module</th><th>Room</th><th v-if="duties" class="num">Writing</th></tr>
      </thead>
      <tbody>
        <tr v-for="p in papers" :key="p.name" :class="{ written: p.written }">
          <td class="ec-nowrap">{{ weekday(p.exam_date) }} {{ formatDate(p.exam_date) }}</td>
          <td class="ec-nowrap">{{ p.start_time }}–{{ p.end_time }}</td>
          <td>
            {{ p.course_name }}
            <div class="ec-muted">{{ p.code }}<template v-if="duties"> · {{ p.campus }}</template></div>
          </td>
          <td>{{ p.rooms.map((r) => r.room_name).join(", ") }}</td>
          <td v-if="duties" class="num">{{ p.sitting }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>

<style scoped>
.exams {
  overflow: hidden;
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem 1rem;
  padding: 1rem 1.25rem 0.75rem;
}

h2 {
  margin: 0;
  font-size: 1.1rem;
}

.written td {
  color: var(--ec-muted);
}
</style>
