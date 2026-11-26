<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import ToggleSwitch from "primevue/toggleswitch";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import WeekGrid from "./WeekGrid.vue";
import { type Room, type Slot, type SlotInput, type TimetableClass, type TimetablePage, deleteSlot, saveRoom, saveSlot, timetablePage } from "./timetable";

/** A campus's week in a semester: the classes' times and rooms; the classes still to place; the campus's rooms */
type Tab = "week" | "rooms";
const route = useRoute();
const router = useRouter();
const toast = useToast();
const tab = ref<Tab>(route.query.tab === "rooms" ? "rooms" : "week");
const page = ref<TimetablePage | null>(null);
const error = ref("");
const busy = ref(false);
const campus = ref<string | null>((route.query.campus as string) || null);
const year = ref<string | null>((route.query.year as string) || null);
const semester = ref<string | null>((route.query.semester as string) || null);
// show everything, or one room, lecturer or class
const focus = ref<string | null>(null);

async function load() {
  error.value = "";
  try {
    page.value = await timetablePage({ campus: campus.value, academic_year: year.value, semester: semester.value });
    campus.value = page.value.campus;
    year.value = page.value.academic_year;
    semester.value = page.value.semester;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
onMounted(load);
watch([campus, year, semester], ([c, y, s], [pc, py, ps]) => {
  if (c === pc && y === py && s === ps) return;
  void router.replace({ query: { ...(tab.value === "rooms" ? { tab: "rooms" } : {}), ...(c ? { campus: c } : {}), ...(y ? { year: y } : {}), ...(s ? { semester: s } : {}) } });
  focus.value = null;
  void load();
});

const tabs = computed(() => [
  { label: "Week", value: "week" as Tab },
  { label: "Rooms", value: "rooms" as Tab, count: page.value?.rooms.length },
]);
const focusOptions = computed(() => {
  const p = page.value;
  if (!p) return [];
  const lecturers = [...new Set(p.slots.flatMap((s) => s.lecturers))].sort();
  return [
    ...p.rooms.filter((r) => p.slots.some((s) => s.room === r.name)).map((r) => ({ value: `room:${r.name}`, label: `Room: ${r.room_name}` })),
    ...lecturers.map((l) => ({ value: `lecturer:${l}`, label: `Lecturer: ${l}` })),
    ...p.classes.map((c) => ({ value: `class:${c.group}`, label: `Class: ${c.code}` })),
  ];
});
const shown = computed(() => {
  const all = page.value?.slots ?? [];
  if (!focus.value) return all;
  const [kind, value] = [focus.value.slice(0, focus.value.indexOf(":")), focus.value.slice(focus.value.indexOf(":") + 1)];
  return all.filter((s) => (kind === "room" ? s.room === value : kind === "lecturer" ? s.lecturers.includes(value) : s.student_group === value));
});
const toPlace = computed(() => (page.value?.classes ?? []).filter((c) => c.hours === 0).length);

// --- a class time ---
const editing = ref<SlotInput | null>(null);
const roomOptions = computed(() =>
  (page.value?.rooms ?? []).filter((r) => !r.disabled || r.name === editing.value?.room).map((r) => ({ value: r.name, label: `${r.room_name} · ${r.room_type.toLowerCase()} · ${r.seating_capacity} seats` })),
);
const classOptions = computed(() => (page.value?.classes ?? []).map((c) => ({ value: c.group, label: `${c.code} ${c.course_name} (${c.students})` })));
function addFor(c?: TimetableClass) {
  editing.value = {
    student_group: c?.group ?? "",
    semester: semester.value ?? "Semester 1",
    day: "Monday",
    start_time: "08:00",
    end_time: "10:00",
    room: page.value?.rooms.find((r) => !r.disabled)?.name ?? "",
    kind: "Lecture",
  };
}
function open(s: Slot) {
  if (!page.value?.can_edit) return;
  editing.value = { name: s.name, student_group: s.student_group, semester: s.semester, day: s.day, start_time: s.start_time, end_time: s.end_time, room: s.room, kind: s.kind };
}
const ready = computed(() => {
  const e = editing.value;
  return Boolean(e && e.student_group && e.room && e.start_time && e.end_time && e.end_time > e.start_time);
});
async function save() {
  busy.value = true;
  try {
    const result = await saveSlot(editing.value!);
    page.value = result.page;
    editing.value = null;
    toast.add({ severity: result.warnings.length ? "warn" : "success", summary: "Saved", detail: result.warnings.join("; ") || undefined, life: result.warnings.length ? 8000 : 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message.replace(/<br>/g, "\n") : String(e), life: 10000 });
  } finally {
    busy.value = false;
  }
}
async function remove() {
  busy.value = true;
  try {
    page.value = await deleteSlot(editing.value!.name!);
    editing.value = null;
    toast.add({ severity: "success", summary: "Removed", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not removed", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}

// --- a room ---
const room = ref<(Partial<Room> & { room_name: string; room_type: string; seating_capacity: number; disabled: boolean }) | null>(null);
function editRoom(r?: Room) {
  room.value = r ? { ...r } : { room_name: "", room_number: "", room_type: "Lecture room", seating_capacity: 30, disabled: false };
}
async function keepRoom() {
  busy.value = true;
  try {
    const rooms = await saveRoom({ ...(room.value as Room), campus: campus.value! });
    if (page.value) page.value.rooms = rooms;
    room.value = null;
    toast.add({ severity: "success", summary: "Room saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="timetable">
    <PageHeader title="Timetable" subtitle="Each class's weekly times and rooms; no room, lecturer or student in two places at once">
      <EcTabs v-model="tab" :tabs="tabs" label="Timetable" class="tabs" />
    </PageHeader>

    <div class="filters">
      <Select v-if="(page?.campuses.length ?? 0) > 1" v-model="campus" :options="page?.campuses ?? []" size="small" aria-label="Campus" />
      <Select v-model="year" :options="page?.academic_years ?? []" size="small" aria-label="Academic year" />
      <Select v-if="tab === 'week'" v-model="semester" :options="page?.semesters ?? []" size="small" aria-label="Semester" />
      <Select v-if="tab === 'week'" v-model="focus" :options="focusOptions" option-label="label" option-value="value" placeholder="All classes" show-clear filter size="small" aria-label="Show" class="focus" />
      <span class="spacer" />
      <EcButton v-if="tab === 'week' && page?.can_edit" label="Add a class time" @click="addFor()" />
      <EcButton v-if="tab === 'rooms' && page?.can_edit_rooms" label="Add a room" @click="editRoom()" />
    </div>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <template v-if="page && tab === 'week'">
      <div class="layout">
        <section class="ec-card grid-card">
          <WeekGrid v-if="shown.length" :slots="shown" :days="page.days" :clickable="page.can_edit" @open="open" />
          <p v-else class="none ec-muted">No class times {{ focus ? "for this" : "yet" }} in {{ page.semester }}</p>
        </section>
        <EcPanel title="Classes" :note="toPlace ? `${toPlace} to place` : 'All placed'" flush>
          <ul class="classes">
            <li v-for="c in page.classes" :key="c.group">
              <div>
                <span class="code">{{ c.code }}</span> {{ c.course_name }}
                <div class="ec-muted small">{{ c.students }} {{ c.students === 1 ? "student" : "students" }} · {{ c.lecturers.join(", ") || "no lecturer" }}{{ c.runs === "Year" ? " · all year" : "" }}</div>
              </div>
              <span class="hours" :class="{ none: !c.hours }">{{ c.hours ? `${c.hours} h` : "Not placed" }}</span>
              <EcButton v-if="page.can_edit" label="Add" size="sm" variant="ghost" @click="addFor(c)" />
            </li>
          </ul>
          <p v-if="!page.classes.length" class="none ec-muted">No classes in {{ page.semester }}</p>
        </EcPanel>
      </div>
    </template>

    <section v-if="page && tab === 'rooms'" class="ec-card">
      <table v-if="page.rooms.length" class="ec-table">
        <thead>
          <tr><th>Room</th><th>Type</th><th class="num">Seats</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="r in page.rooms" :key="r.name" :class="{ off: r.disabled }">
            <td>{{ r.room_name }}<span v-if="r.room_number" class="ec-muted"> · {{ r.room_number }}</span></td>
            <td>{{ r.room_type }}<span v-if="r.disabled" class="ec-muted"> · not in use</span></td>
            <td class="num">{{ r.seating_capacity }}</td>
            <td class="num"><EcButton v-if="page.can_edit_rooms" label="Edit" size="sm" variant="ghost" @click="editRoom(r)" /></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="none ec-muted">No rooms on {{ page.campus }} yet</p>
    </section>
  </section>

  <EcModal :open="editing !== null" :title="editing?.name ? 'Class time' : 'Add a class time'" :description="page ? `${page.campus}, ${page.semester} ${page.academic_year}` : ''" size="md" @update:open="(v: boolean) => !v && (editing = null)">
    <div v-if="editing" class="form">
      <EcField label="Class" for="slot-class">
        <Select v-model="editing.student_group" input-id="slot-class" :options="classOptions" option-label="label" option-value="value" filter fluid />
      </EcField>
      <div class="row">
        <EcField label="Day" for="slot-day">
          <Select v-model="editing.day" input-id="slot-day" :options="page?.days ?? []" fluid />
        </EcField>
        <EcField label="Starts" for="slot-start">
          <InputText id="slot-start" v-model="editing.start_time" type="time" step="900" fluid />
        </EcField>
        <EcField label="Ends" for="slot-end">
          <InputText id="slot-end" v-model="editing.end_time" type="time" step="900" fluid />
        </EcField>
      </div>
      <EcField label="Room" for="slot-room">
        <Select v-model="editing.room" input-id="slot-room" :options="roomOptions" option-label="label" option-value="value" fluid />
      </EcField>
      <EcField label="Kind" for="slot-kind">
        <Select v-model="editing.kind" input-id="slot-kind" :options="page?.kinds ?? []" fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton v-if="editing?.name" label="Remove" variant="ghost" :loading="busy" class="left" @click="remove" />
      <EcButton label="Cancel" variant="ghost" @click="editing = null" />
      <EcButton label="Save" variant="primary" :loading="busy" :disabled="!ready" @click="save" />
    </template>
  </EcModal>

  <EcModal :open="room !== null" :title="room?.name ? room.room_name : 'Add a room'" :description="page?.campus ?? ''" @update:open="(v: boolean) => !v && (room = null)">
    <div v-if="room" class="form">
      <EcField label="Name" for="room-name">
        <InputText id="room-name" v-model="room.room_name" fluid />
      </EcField>
      <div class="row two">
        <EcField label="Number" for="room-number">
          <InputText id="room-number" v-model="room.room_number" fluid />
        </EcField>
        <EcField label="Seats" for="room-seats">
          <InputNumber v-model="room.seating_capacity" input-id="room-seats" :min="1" fluid />
        </EcField>
      </div>
      <EcField label="Type" for="room-type">
        <Select v-model="room.room_type" input-id="room-type" :options="page?.room_types ?? []" fluid />
      </EcField>
      <EcField v-if="room.name" label="Not in use" for="room-off" hint="Kept for the times already set; not offered for new ones">
        <ToggleSwitch v-model="room.disabled" input-id="room-off" />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="room = null" />
      <EcButton label="Save" variant="primary" :loading="busy" :disabled="!room?.room_name.trim() || !room?.seating_capacity" @click="keepRoom" />
    </template>
  </EcModal>
</template>

<style scoped>
.timetable {
  display: grid;
  gap: 1rem;
}

.tabs {
  flex: 1;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.focus {
  min-width: 14rem;
}

.spacer {
  flex: 1;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20rem;
  gap: 1rem;
  align-items: start;
}

@media (max-width: 1100px) {
  .layout {
    grid-template-columns: 1fr;
  }
}

.grid-card {
  overflow: hidden;
  padding: 0.5rem 0.75rem 0.75rem 0;
}

.classes {
  margin: 0;
  padding: 0;
  list-style: none;
}

.classes li {
  display: grid;
  grid-template-columns: 1fr auto auto;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 1rem;
  border-top: 1px solid var(--ec-border);
  font-size: 0.875rem;
}

.classes li:first-child {
  border-top: 0;
}

.code {
  font-weight: 600;
}

.small {
  font-size: 0.75rem;
}

.hours {
  font-size: 0.8rem;
  white-space: nowrap;
}

.hours.none {
  color: var(--ec-warn, #b45309);
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
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

.off td {
  color: var(--ec-muted);
}

.left {
  margin-right: auto;
}
</style>
