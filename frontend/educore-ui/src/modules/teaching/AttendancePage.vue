<script setup lang="ts">
import DatePicker from "primevue/datepicker";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import { type AttendanceStatus, type Register, STATUS_LABELS, getRegister, takeRegister } from "./attendance";

/** The lecturer's register for one of their classes on a day, and each student's attendance so far */
const props = defineProps<{ group: string }>();
const toast = useToast();
const register = ref<Register | null>(null);
const error = ref("");
const saving = ref(false);
const day = ref<Date>(new Date());
const marks = ref<Record<string, AttendanceStatus | null>>({});
const OPTIONS = (["Present", "Absent", "Leave"] as AttendanceStatus[]).map((value) => ({ value, label: STATUS_LABELS[value] }));

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
function take(data: Register) {
  register.value = data;
  marks.value = Object.fromEntries(data.entries.map((e) => [e.student, e.status]));
}
async function load() {
  error.value = "";
  try {
    take(await getRegister(props.group, iso(day.value)));
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch([() => props.group, day], load, { immediate: true });

const unmarked = computed(() => Object.values(marks.value).filter((s) => !s).length);
const changed = computed(() => register.value?.entries.some((e) => marks.value[e.student] !== e.status) ?? false);
const allPresent = () => {
  for (const key of Object.keys(marks.value)) if (!marks.value[key]) marks.value[key] = "Present";
};
const rate = computed(() => Object.fromEntries((register.value?.students ?? []).map((s) => [s.student, s])));
const below = computed(() => (register.value?.students ?? []).filter((s) => s.below));
const subtitle = computed(() => {
  const c = register.value?.class;
  return c ? [c.course_name, c.campus?.replace(" Campus", ""), c.academic_year].filter(Boolean).join(" · ") : "";
});

async function save() {
  if (!register.value) return;
  saving.value = true;
  try {
    const entries = register.value.entries.map((e) => ({ student: e.student, status: marks.value[e.student] as AttendanceStatus }));
    take(await takeRegister(props.group, register.value.date, entries));
    toast.add({ severity: "success", summary: `Register for ${formatDate(register.value.date)} saved`, life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <RecordPage
    :back="{ to: { name: 'my-teaching' }, label: 'My teaching' }"
    :title="register ? `Attendance: ${register.class.code ?? register.class.course}` : undefined"
    :subtitle="subtitle"
    :error="error"
    :outstanding="below.map((s) => `${s.student_name}: ${s.rate}% attendance, below ${register?.minimum}%`)"
  >
    <template v-if="register" #actions>
      <DatePicker v-model="day" :max-date="new Date()" date-format="dd-mm-yy" show-icon icon-display="input" aria-label="Date" class="day" />
      <EcButton v-if="unmarked" label="Mark the rest present" @click="allPresent" />
      <EcButton :label="register.taken ? 'Save changes' : 'Save register'" variant="primary" :loading="saving" :disabled="!changed || unmarked > 0" @click="save" />
    </template>

    <EcPanel v-if="register" :title="`Register ${formatDate(register.date)}`" :note="register.taken ? 'Taken' : `${unmarked} to mark`" flush>
      <table class="ec-table">
        <thead>
          <tr><th>Student</th><th>Attendance</th><th class="num">So far</th></tr>
        </thead>
        <tbody>
          <tr v-for="e in register.entries" :key="e.student">
            <td>
              {{ e.student_name }}
              <div class="ec-muted">{{ e.student }}</div>
            </td>
            <td><EcSegmented :model-value="marks[e.student] as AttendanceStatus" :options="OPTIONS" :label="`Attendance of ${e.student_name}`" @update:model-value="(v: AttendanceStatus) => (marks[e.student] = v)" /></td>
            <td class="num ec-nowrap">
              <template v-if="rate[e.student]?.rate !== null && rate[e.student]?.rate !== undefined">
                {{ rate[e.student].rate }}%
                <div v-if="rate[e.student].below" class="ec-muted">Below {{ register.minimum }}%</div>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </EcPanel>

    <template v-if="register" #aside>
      <EcPanel title="Sessions" :note="`${register.sessions.length}`" :flush="register.sessions.length > 0">
        <table v-if="register.sessions.length" class="ec-table">
          <tbody>
            <tr v-for="s in register.sessions" :key="s.date">
              <td><button type="button" class="link" @click="day = new Date(`${s.date}T00:00:00`)">{{ formatDate(s.date) }}</button></td>
              <td class="num ec-muted ec-nowrap">{{ s.present }} present<template v-if="s.absent"> · {{ s.absent }} absent</template><template v-if="s.excused"> · {{ s.excused }} excused</template></td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No register taken yet</p>
      </EcPanel>
    </template>
  </RecordPage>
</template>

<style scoped>
.day {
  width: 10.5rem;
}

.none {
  margin: 0;
}

.link {
  padding: 0;
  border: 0;
  background: none;
  color: var(--ec-accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}
</style>
