<script setup lang="ts">
import { Search } from "@lucide/vue";
import DatePicker from "primevue/datepicker";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import { type AttendanceStatus, type Register, STATUS_LABELS, getRegister, takeRegister } from "./attendance";

/** A module's register for a lesson (its timetable's times on a day; a register a day without a timetable), for a
 * class of any size: search, filter to who is left to mark, absent or below the minimum; earlier registers */
const props = defineProps<{ group: string }>();
const toast = useToast();
const register = ref<Register | null>(null);
const error = ref("");
const saving = ref(false);
const day = ref<Date | null>(null);
const lesson = ref<string | null>(null);
const marks = ref<Record<string, AttendanceStatus | null>>({});
const search = ref("");
type Filter = "all" | "unmarked" | "absent" | "below";
const filter = ref<Filter>("all");
const OPTIONS = (["Present", "Absent", "Leave"] as AttendanceStatus[]).map((value) => ({ value, label: STATUS_LABELS[value] }));

const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
function take(data: Register) {
  register.value = data;
  marks.value = Object.fromEntries(data.entries.map((e) => [e.student, e.status]));
}
// set from the register itself (the latest lesson at first), without loading it again
let adopting = false;
async function load(date?: string, chosen?: string | null, startTime?: string | null) {
  error.value = "";
  try {
    const data = await getRegister(props.group, date, chosen);
    const wanted = startTime ? data.lessons.find((l) => l.start_time === startTime) : null;
    take(wanted && wanted.key !== data.lesson ? await getRegister(props.group, data.date, wanted.key) : data);
    adopting = true;
    day.value = new Date(`${register.value!.date}T00:00:00`);
    lesson.value = register.value!.lesson;
    adopting = false;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch(() => props.group, () => load(), { immediate: true });
watch(day, (d) => !adopting && d && load(iso(d)));
watch(lesson, (l) => !adopting && l && register.value && load(register.value.date, l));
const lessonOptions = computed(() =>
  (register.value?.lessons ?? []).map((l) => ({ value: l.key, label: `${l.start_time}–${l.end_time} ${l.kind.toLowerCase()}` })),
);
const current = computed(() => register.value?.lessons.find((l) => l.key === register.value?.lesson) ?? null);
const noLesson = computed(() => Boolean(register.value && register.value.timetabled && !register.value.lessons.length));

const unmarked = computed(() => Object.values(marks.value).filter((s) => !s).length);
const absent = computed(() => Object.values(marks.value).filter((s) => s === "Absent").length);
const changed = computed(() => register.value?.entries.some((e) => marks.value[e.student] !== e.status) ?? false);
const allPresent = () => {
  for (const key of Object.keys(marks.value)) if (!marks.value[key]) marks.value[key] = "Present";
};
const rate = computed(() => Object.fromEntries((register.value?.students ?? []).map((s) => [s.student, s])));
const below = computed(() => (register.value?.students ?? []).filter((s) => s.below).length);
const filters = computed(() => [
  { value: "all" as Filter, label: `All ${register.value?.entries.length ?? 0}` },
  { value: "unmarked" as Filter, label: `To mark ${unmarked.value}` },
  { value: "absent" as Filter, label: `Absent ${absent.value}` },
  ...(register.value?.minimum ? [{ value: "below" as Filter, label: `Below ${register.value.minimum}% ${below.value}` }] : []),
]);
const shown = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (register.value?.entries ?? []).filter((e) => {
    if (q && !`${e.student_name} ${e.student}`.toLowerCase().includes(q)) return false;
    if (filter.value === "unmarked") return !marks.value[e.student];
    if (filter.value === "absent") return marks.value[e.student] === "Absent";
    if (filter.value === "below") return rate.value[e.student]?.below;
    return true;
  });
});
const earlier = computed(() =>
  (register.value?.sessions ?? []).map((s) => ({
    value: `${s.date}|${s.start_time ?? ""}`,
    label: `${formatDate(s.date)}${s.start_time ? ` ${s.start_time}` : ""} · ${s.present} present${s.absent ? `, ${s.absent} absent` : ""}`,
  })),
);
function pickEarlier(value: string | null) {
  if (!value) return;
  const [date, start] = value.split("|");
  void load(date, null, start || null);
}

async function save() {
  if (!register.value) return;
  saving.value = true;
  try {
    take(await takeRegister(props.group, register.value.date, Object.entries(marks.value).map(([student, status]) => ({ student, status: status as AttendanceStatus })), register.value.lesson));
    toast.add({ severity: "success", summary: `Register for ${formatDate(register.value.date)}${current.value ? ` ${current.value.start_time}` : ""} saved`, life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
  <section v-else-if="register" class="ec-card tab">
    <div class="bar">
      <DatePicker v-model="day" :max-date="new Date()" date-format="dd-mm-yy" show-icon icon-display="input" aria-label="Date" class="day" size="small" />
      <Select v-if="earlier.length" :options="earlier" option-label="label" option-value="value" placeholder="Earlier registers" size="small" aria-label="Earlier registers" class="earlier" @update:model-value="pickEarlier" />
      <EcSegmented v-if="lessonOptions.length > 1" :model-value="lesson ?? ''" @update:model-value="(v: string) => (lesson = v)" :options="lessonOptions" label="Lesson" />
      <span v-if="current" class="state ec-muted">{{ lessonOptions.length > 1 ? "" : `${current.start_time}–${current.end_time} ${current.kind.toLowerCase()} · ` }}{{ current.room_name }}</span>
    </div>
    <p v-if="noLesson" class="none ec-muted">
      No lesson of this module on {{ formatDate(register.date) }}.
      {{ register.lesson_days.length ? `It meets on ${register.lesson_days.join(", ")}.` : "It has no lessons this semester." }}
    </p>
    <template v-else>
    <div class="bar">
      <IconField class="search">
        <InputIcon><Search :size="15" /></InputIcon>
        <InputText v-model="search" placeholder="Name or student number" aria-label="Search students" fluid size="small" />
      </IconField>
      <EcSegmented v-model="filter" :options="filters" label="Show" />
      <span class="spacer" />
      <span class="state ec-muted">{{ register.taken ? "Taken" : `${unmarked} to mark` }}</span>
      <EcButton v-if="unmarked" label="Mark the rest present" size="sm" @click="allPresent" />
      <EcButton :label="register.taken ? 'Save changes' : 'Save register'" size="sm" variant="primary" :loading="saving" :disabled="!changed || unmarked > 0" @click="save" />
    </div>
    <div class="scroll">
      <table class="ec-table sticky">
        <thead>
          <tr><th>Student</th><th>{{ current ? `${formatDate(register.date)} ${current.start_time}` : formatDate(register.date) }}</th><th class="num">So far</th></tr>
        </thead>
        <tbody>
          <tr v-for="e in shown" :key="e.student">
            <td>
              {{ e.student_name }}
              <div class="ec-muted">{{ e.student }}</div>
            </td>
            <td><EcSegmented :model-value="marks[e.student] as AttendanceStatus" :options="OPTIONS" :label="`Attendance of ${e.student_name}`" @update:model-value="(v: AttendanceStatus) => (marks[e.student] = v)" /></td>
            <td class="num ec-nowrap">
              <template v-if="rate[e.student]?.rate !== null && rate[e.student]?.rate !== undefined">
                <span :class="{ low: rate[e.student].below }">{{ rate[e.student].rate }}%</span>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!shown.length" class="none ec-muted">No student here</p>
    </div>
    </template>
  </section>
</template>

<style scoped>
.tab {
  overflow: hidden;
}

.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--ec-border);
}

.day {
  width: 10rem;
}

.earlier {
  min-width: 14rem;
}

.state {
  font-size: 0.8125rem;
}

.spacer {
  flex: 1;
}

.search {
  flex: 1;
  max-width: 20rem;
}

.scroll {
  max-height: 70vh;
  overflow-y: auto;
}

.sticky thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--ec-surface, #fff);
}

.low {
  color: var(--ec-danger, #b42318);
  font-weight: 600;
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
}
</style>
