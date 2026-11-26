<script setup lang="ts">
import { X } from "@lucide/vue";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import { formatDate } from "@/core/format";
import { semesterLabel } from "@/modules/curriculum/api";
import { type ClassDetail, getClass, setLecturers } from "./allocation";

/** One class: its lecturers (the head of department or dean allocates them) and its class list */
const props = defineProps<{ group: string }>();
const route = useRoute();
const toast = useToast();
const data = ref<ClassDetail | null>(null);
const lecturers = ref<string[]>([]);
const error = ref("");
const saving = ref(false);

function take(d: ClassDetail) {
  data.value = d;
  lecturers.value = d.lecturers.map((l) => l.instructor);
}
watch(
  () => props.group,
  async () => {
    data.value = null;
    error.value = "";
    try {
      take(await getClass(props.group));
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

const back = computed(() => ({ to: { name: "teaching", query: route.query }, label: "Teaching" }));
const nameOf = (instructor: string) => data.value?.instructors.find((i) => i.name === instructor)?.instructor_name ?? instructor;
const departmentOf = (instructor: string) => data.value?.instructors.find((i) => i.name === instructor)?.department ?? "";
const changed = computed(() => JSON.stringify(lecturers.value) !== JSON.stringify(data.value?.lecturers.map((l) => l.instructor) ?? []));
const adding = ref<string | null>(null);
const available = computed(() =>
  (data.value?.instructors ?? [])
    .filter((i) => !lecturers.value.includes(i.name))
    .map((i) => ({ value: i.name, label: [i.instructor_name, i.department, `${i.hours} h a week`].filter(Boolean).join(" · ") })),
);
function add() {
  if (adding.value) lecturers.value.push(adding.value);
  adding.value = null;
}

async function save() {
  saving.value = true;
  try {
    take(await setLecturers(props.group, lecturers.value));
    toast.add({ severity: "success", summary: "Lecturers saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
const subtitle = computed(() => {
  const d = data.value;
  return d ? [d.course, d.campus, d.academic_year, semesterLabel(d.semester), d.credits ? `${d.credits} credits` : ""].filter(Boolean).join(" · ") : "";
});
</script>

<template>
  <RecordPage :back="back" :title="data ? `${data.code ?? data.course} ${data.campus?.replace(' Campus', '') ?? ''}` : undefined" :subtitle="subtitle" :error="error">
    <template v-if="data && data.can_edit && changed" #actions>
      <EcButton label="Undo" variant="ghost" :disabled="saving" @click="data && take(data)" />
      <EcButton label="Save" variant="primary" :loading="saving" @click="save" />
    </template>

    <template v-if="data">
      <EcPanel title="Class list" :note="`${data.students.length} ${data.students.length === 1 ? 'student' : 'students'}`" flush>
        <table v-if="data.students.length" class="ec-table">
          <thead>
            <tr><th>Student</th><th>Student number</th><th>Programme</th><th class="num">Year</th></tr>
          </thead>
          <tbody>
            <tr v-for="s in data.students" :key="s.student">
              <td>{{ s.student_name }}</td>
              <td class="ec-muted ec-nowrap">{{ s.student }}</td>
              <td>{{ s.offering }}</td>
              <td class="num">{{ s.year_of_study || "" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No students registered for this course yet</p>
      </EcPanel>
    </template>

    <template v-if="data" #aside>
      <EcPanel title="Attendance" :note="data.attendance.sessions.length ? `${data.attendance.sessions.length} sessions` : undefined" :flush="data.attendance.sessions.length > 0">
        <table v-if="data.attendance.sessions.length" class="ec-table">
          <tbody>
            <tr v-for="s in data.attendance.students" :key="s.student">
              <td>
                {{ s.student_name }}
                <div v-if="s.below" class="ec-muted">Below {{ data.attendance.minimum }}%</div>
              </td>
              <td class="num ec-nowrap">{{ s.rate === null ? "" : `${s.rate}%` }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No register taken yet</p>
      </EcPanel>

      <EcPanel title="Lecturers" flush>
        <ul v-if="lecturers.length" class="lecturers">
          <li v-for="l in lecturers" :key="l">
            <span class="grow">{{ nameOf(l) }}<span class="sub">{{ departmentOf(l) }}</span></span>
            <EcButton v-if="data.can_edit" :icon="X" size="sm" variant="ghost" :aria-label="`Remove ${nameOf(l)}`" @click="lecturers.splice(lecturers.indexOf(l), 1)" />
          </li>
        </ul>
        <p v-else class="none ec-muted">No lecturer allocated</p>
        <template v-if="data.can_edit" #footer>
          <Select v-model="adding" :options="available" option-label="label" option-value="value" filter placeholder="Add a lecturer" size="small" aria-label="Add a lecturer" class="add" @change="add" />
        </template>
      </EcPanel>

      <EcPanel v-if="data.moodle.connected" title="Moodle">
        <p v-if="data.moodle.error" class="none moodle-error">Not in Moodle yet: {{ data.moodle.error }}</p>
        <p v-else-if="data.moodle.course_id" class="none">Course {{ data.moodle.course_id }} · synced {{ formatDate(data.moodle.synced_on) }}</p>
        <p v-else class="none ec-muted">Made in Moodle at the next sync</p>
      </EcPanel>
    </template>
  </RecordPage>
</template>

<style scoped>
.none {
  margin: 0;
  padding: 1rem 1.25rem;
}

.lecturers {
  margin: 0;
  padding: 0;
  list-style: none;
}

.lecturers li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1.25rem;
  border-bottom: 1px solid var(--ec-border-soft);
  font-size: 0.875rem;
}

.lecturers li:last-child {
  border-bottom: 0;
}

.grow {
  flex: 1;
  min-width: 0;
}

.sub {
  display: block;
  color: var(--ec-muted);
  font-size: 0.75rem;
}

.moodle-error {
  color: var(--ec-muted);
}

.add {
  width: 100%;
}
</style>
