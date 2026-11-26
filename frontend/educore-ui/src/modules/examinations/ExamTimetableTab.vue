<script setup lang="ts">
import { Search } from "@lucide/vue";
import DatePicker from "primevue/datepicker";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { formatDate, fromIsoDate, toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import {
  type ExamTimetablePage,
  type Paper,
  type SessionKind,
  deletePaper,
  getExamTimetable,
  publishSession,
  savePaper,
  saveSession,
} from "./examTimetable";

/**
 * The examination timetable of a session on a campus: each class's paper by day (hours, rooms, invigilators), the
 * classes still to schedule, and publishing. The Examinations Officer schedules; the Registrar publishes; then
 * students see their papers on My studies and invigilators their duties on My modules.
 */
const props = defineProps<{ year?: string }>();
const toast = useToast();
const page = ref<ExamTimetablePage | null>(null);
const error = ref("");
const busy = ref(false);
const search = ref("");
const session = ref<string | null>(null);
const campus = ref<string | null>(null);

let adopting = false;
function take(p: ExamTimetablePage) {
  page.value = p;
  adopting = true;
  session.value = p.session?.name ?? null;
  campus.value = p.campus;
  adopting = false;
}
async function load(params: { academic_year?: string; session?: string; campus?: string }) {
  error.value = "";
  try {
    take(await getExamTimetable(params));
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch(() => props.year, (y) => load({ academic_year: y, campus: campus.value ?? undefined }), { immediate: true });
watch([session, campus], () => !adopting && load({ session: session.value ?? undefined, campus: campus.value ?? undefined }));

async function act(work: () => Promise<ExamTimetablePage>, done: string): Promise<boolean> {
  busy.value = true;
  try {
    take(await work());
    toast.add({ severity: "success", summary: done, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message.replace(/<br>/g, "\n") : String(e), life: 10000 });
    return false;
  } finally {
    busy.value = false;
  }
}

const sessionOptions = computed(() => (page.value?.sessions ?? []).map((s) => ({ value: s.name, label: s.name })));
const current = computed(() => page.value?.session ?? null);

// the papers by day
const days = computed(() => {
  const q = search.value.trim().toLowerCase();
  const byDay = new Map<string, Paper[]>();
  for (const p of page.value?.papers ?? []) {
    const text = `${p.code} ${p.course_name} ${p.rooms.map((r) => r.room_name).join(" ")} ${p.invigilators.map((i) => i.full_name).join(" ")}`;
    if (q && !text.toLowerCase().includes(q)) continue;
    byDay.set(p.exam_date, [...(byDay.get(p.exam_date) ?? []), p]);
  }
  return [...byDay.entries()].map(([date, papers]) => ({ date, papers }));
});
const weekday = (iso: string) => fromIsoDate(iso).toLocaleDateString("en-GB", { weekday: "long" });

// a paper
interface PaperForm { name?: string; student_group: string | null; day: Date | null; start_time: string; end_time: string; rooms: string[]; invigilators: string[] }
const editing = ref<PaperForm | null>(null);
function schedule(group: string) {
  editing.value = { student_group: group, day: current.value ? fromIsoDate(current.value.starts_on) : null, start_time: "08:30", end_time: "11:30", rooms: [], invigilators: [] };
}
function edit(p: Paper) {
  editing.value = { name: p.name, student_group: p.student_group, day: fromIsoDate(p.exam_date), start_time: p.start_time, end_time: p.end_time, rooms: p.rooms.map((r) => r.room), invigilators: p.invigilators.map((i) => i.user) };
}
const editingLabel = computed(() => {
  const e = editing.value;
  if (!e) return "";
  const p = page.value?.papers.find((x) => x.name === e.name);
  const c = page.value?.to_schedule.find((x) => x.group === e.student_group);
  return p ? `${p.code} ${p.course_name} · ${p.sitting} writing` : c ? `${c.code} ${c.course_name} · ${c.sitting} writing` : e.student_group ?? "";
});
const roomOptions = computed(() => (page.value?.rooms ?? []).map((r) => ({ value: r.name, label: `${r.room_name} (${r.seating_capacity} seats)` })));
const paperReady = computed(() => Boolean(editing.value?.student_group && editing.value.day && editing.value.start_time && editing.value.end_time && editing.value.rooms.length));
async function keepPaper() {
  const e = editing.value!;
  const ok = await act(
    () => savePaper({ name: e.name, session: current.value!.name, student_group: e.student_group!, exam_date: toIsoDate(e.day!), start_time: e.start_time, end_time: e.end_time, rooms: e.rooms, invigilators: e.invigilators }),
    "Paper scheduled",
  );
  if (ok) editing.value = null;
}
async function removePaper() {
  if (await act(() => deletePaper(editing.value!.name!), "Paper removed")) editing.value = null;
}

// a session
interface SessionForm { name?: string; session_name: string; semester: string; kind: SessionKind; range: Date[] | null }
const sessionForm = ref<SessionForm | null>(null);
function newSession() {
  sessionForm.value = { session_name: "", semester: page.value?.semesters[0] ?? "Semester 1", kind: "Main", range: null };
}
function editSession() {
  const s = current.value!;
  sessionForm.value = { name: s.name, session_name: s.name, semester: s.semester, kind: s.kind, range: [fromIsoDate(s.starts_on), fromIsoDate(s.ends_on)] };
}
const sessionReady = computed(() => Boolean(sessionForm.value?.session_name.trim() && sessionForm.value.range?.[0] && sessionForm.value.range?.[1]));
async function keepSession() {
  const f = sessionForm.value!;
  const ok = await act(
    () =>
      saveSession({
        name: f.name,
        session_name: f.session_name.trim(),
        academic_year: page.value?.academic_year ?? undefined,
        semester: f.semester,
        kind: f.kind,
        starts_on: toIsoDate(f.range![0]),
        ends_on: toIsoDate(f.range![1]),
        campus: campus.value,
      }),
    "Session saved",
  );
  if (ok) sessionForm.value = null;
}
const publish = () => act(() => publishSession(current.value!.name, campus.value), "Timetable published");
</script>

<template>
  <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
  <section v-else-if="page" class="ec-card tab">
    <div class="bar">
      <Select v-if="page.sessions.length" v-model="session" :options="sessionOptions" option-label="label" option-value="value" size="small" aria-label="Session" class="session" />
      <Select v-if="page.campuses.length > 1" v-model="campus" :options="page.campuses" size="small" aria-label="Campus" />
      <template v-if="current">
        <StatusTag kind="exam" :value="current.status" />
        <span class="ec-muted small">{{ current.kind === "Main" ? current.semester : "Supplementary and special" }} · {{ formatDate(current.starts_on) }} to {{ formatDate(current.ends_on) }}</span>
        <EcButton v-if="page.can_edit" label="Change days" size="sm" variant="ghost" @click="editSession" />
      </template>
      <span class="spacer" />
      <EcButton v-if="page.can_edit" label="New session" size="sm" :variant="page.sessions.length ? 'ghost' : 'primary'" @click="newSession" />
      <EcButton v-if="page.can_publish && current?.status === 'Draft' && current.papers" label="Publish" size="sm" variant="primary" :loading="busy" @click="publish" />
    </div>

    <p v-if="!current" class="none ec-muted">No examination sessions in {{ page.academic_year }} yet.</p>
    <template v-else>
      <div v-if="page.can_edit && page.to_schedule.length" class="todo">
        <span class="todo-title">To schedule {{ page.to_schedule.length }}</span>
        <button v-for="c in page.to_schedule" :key="c.group" type="button" class="chip" :aria-label="`Schedule ${c.code}`" @click="schedule(c.group)">
          {{ c.code }} <span class="ec-muted">{{ c.sitting }}</span>
        </button>
      </div>

      <div class="bar">
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Module, room or invigilator" aria-label="Search papers" fluid size="small" />
        </IconField>
        <span class="ec-muted small">{{ page.papers.length }} {{ page.papers.length === 1 ? "paper" : "papers" }}{{ page.to_schedule.length ? `, ${page.to_schedule.length} to schedule` : "" }}</span>
      </div>

      <div class="scroll">
        <table v-if="days.length" class="ec-table sticky">
          <thead>
            <tr><th>Time</th><th>Module</th><th class="num">Writing</th><th>Rooms</th><th>Invigilators</th></tr>
          </thead>
          <tbody v-for="d in days" :key="d.date">
            <tr class="day-row"><th colspan="5">{{ weekday(d.date) }} {{ formatDate(d.date) }}</th></tr>
            <tr v-for="p in d.papers" :key="p.name" :class="{ clickable: page.can_edit }" @click="page.can_edit && edit(p)">
              <td class="ec-nowrap">{{ p.start_time }}–{{ p.end_time }}</td>
              <td>
                {{ p.course_name }}
                <div class="ec-muted">{{ p.code }}</div>
              </td>
              <td class="num">{{ p.sitting }}</td>
              <td>{{ p.rooms.map((r) => r.room_name).join(", ") }}</td>
              <td>{{ p.invigilators.map((i) => i.full_name).join(", ") || "—" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">{{ search ? "No paper matches" : "No papers scheduled yet" }}</p>
      </div>
    </template>
  </section>

  <EcModal :open="editing !== null" :title="editing?.name ? 'Paper' : 'Schedule a paper'" :description="editingLabel" size="md" @update:open="(v: boolean) => !v && (editing = null)">
    <div v-if="editing" class="form">
      <div class="row">
        <EcField label="Date" for="paper-day">
          <DatePicker v-model="editing.day" input-id="paper-day" :min-date="current ? fromIsoDate(current.starts_on) : undefined" :max-date="current ? fromIsoDate(current.ends_on) : undefined" date-format="dd-mm-yy" fluid />
        </EcField>
        <EcField label="Starts" for="paper-start">
          <InputText id="paper-start" v-model="editing.start_time" type="time" step="900" fluid />
        </EcField>
        <EcField label="Ends" for="paper-end">
          <InputText id="paper-end" v-model="editing.end_time" type="time" step="900" fluid />
        </EcField>
      </div>
      <EcField label="Rooms" for="paper-rooms">
        <MultiSelect v-model="editing.rooms" input-id="paper-rooms" :options="roomOptions" option-label="label" option-value="value" display="chip" placeholder="Choose" fluid />
      </EcField>
      <EcField label="Invigilators" for="paper-invigilators">
        <MultiSelect v-model="editing.invigilators" input-id="paper-invigilators" :options="page?.invigilators ?? []" option-label="full_name" option-value="user" display="chip" filter placeholder="Choose" fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton v-if="editing?.name" label="Remove" variant="ghost" :loading="busy" class="left" @click="removePaper" />
      <EcButton label="Cancel" variant="ghost" @click="editing = null" />
      <EcButton label="Save" variant="primary" :loading="busy" :disabled="!paperReady" @click="keepPaper" />
    </template>
  </EcModal>

  <EcModal :open="sessionForm !== null" :title="sessionForm?.name ? sessionForm.name : 'New examination session'" :description="page?.academic_year ? `Academic year ${page.academic_year}` : ''" size="md" @update:open="(v: boolean) => !v && (sessionForm = null)">
    <div v-if="sessionForm" class="form">
      <EcField v-if="!sessionForm.name" label="Name" for="session-name">
        <InputText id="session-name" v-model="sessionForm.session_name" placeholder="Semester 1 examinations 2026" fluid />
      </EcField>
      <div v-if="!sessionForm.name" class="row two">
        <EcField label="Semester" for="session-semester">
          <Select v-model="sessionForm.semester" input-id="session-semester" :options="page?.semesters ?? []" fluid />
        </EcField>
        <EcField label="Examinations" for="session-kind">
          <Select v-model="sessionForm.kind" input-id="session-kind" :options="page?.kinds ?? []" fluid />
        </EcField>
      </div>
      <EcField label="Days" for="session-days">
        <DatePicker v-model="sessionForm.range" input-id="session-days" selection-mode="range" :manual-input="false" date-format="dd-mm-yy" fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="sessionForm = null" />
      <EcButton label="Save" variant="primary" :loading="busy" :disabled="!sessionReady" @click="keepSession" />
    </template>
  </EcModal>
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

.session {
  min-width: 16rem;
}

.small {
  font-size: 0.8125rem;
}

.spacer {
  flex: 1;
}

.search {
  flex: 1;
  max-width: 20rem;
}

.todo {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--ec-border);
  background: var(--ec-surface-muted);
}

.todo-title {
  margin-right: 0.35rem;
  font-size: 0.8125rem;
  font-weight: 600;
}

.chip {
  padding: 0.2rem 0.6rem;
  border: 1px solid var(--ec-border);
  border-radius: 999px;
  background: var(--ec-surface);
  font: inherit;
  font-size: 0.8125rem;
  cursor: pointer;
}

.chip:hover {
  border-color: var(--ec-primary, #2563eb);
}

.scroll {
  max-height: 70vh;
  overflow: auto;
}

.sticky thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--ec-surface, #fff);
}

.day-row th {
  padding-top: 0.9rem;
  background: var(--ec-surface-muted);
  font-size: 0.8125rem;
  text-align: left;
}

.clickable {
  cursor: pointer;
}

.clickable:hover td {
  background: var(--ec-surface-muted);
}

.form {
  display: grid;
  gap: 0.875rem;
}

.row {
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 0.75rem;
}

.row.two {
  grid-template-columns: 1fr 1fr;
}

.left {
  margin-right: auto;
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
}
</style>
