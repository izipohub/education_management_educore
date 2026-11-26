<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type CourseClass, type MyClasses, getMyClasses } from "./api";
import MyWeek from "./MyWeek.vue";
import MyExams from "@/modules/examinations/MyExams.vue";

/** The lecturer's modules: a row per module (however many students), opening the module's page; and their
 * timetable. From the menu it also opens on one piece of the daily work (focus): the modules to take
 * a register for, keep a gradebook or enter marks in, each row opening that tab of the module; or the timetable. */
type Focus = "attendance" | "gradebook" | "marks" | "timetable";
const props = defineProps<{ focus?: Focus }>();
const FOCUS: Record<Exclude<Focus, "timetable">, { title: string; route: string; from: string }> = {
  attendance: { title: "Attendance", route: "class-attendance", from: "my-attendance" },
  gradebook: { title: "Gradebook", route: "class-gradebook", from: "my-gradebook" },
  marks: { title: "Marks", route: "class-marks", from: "my-marks" },
};
const focused = computed(() => (props.focus && props.focus !== "timetable" ? FOCUS[props.focus] : null));
const data = ref<MyClasses | null>(null);
const error = ref("");
const loading = ref(false);
const academicYear = ref<string | undefined>();
const search = ref("");
type Tab = "modules" | "timetable";
const tab = computed<Tab>(() => (props.focus === "timetable" ? "timetable" : "modules"));
let adoptingYear = false;

async function load() {
  error.value = "";
  loading.value = true;
  try {
    data.value = await getMyClasses(academicYear.value);
    if (!academicYear.value && data.value.academic_year) {
      adoptingYear = true;
      academicYear.value = data.value.academic_year;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}

watch(academicYear, () => {
  if (adoptingYear) {
    adoptingYear = false;
    return;
  }
  void load();
});
onMounted(load);

/** different people: a student in three of your classes counts once */
const totalStudents = computed(() => new Set(data.value?.classes.flatMap((c) => c.students.map((s) => s.student))).size);
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;
const subtitle = computed(() =>
  data.value?.linked ? `${plural(data.value.classes.length, "module", "modules")} · ${plural(totalStudents.value, "student", "students")}` : undefined,
);
const rows = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (data.value?.classes ?? []).filter((c) => !q || `${c.code} ${c.course} ${c.campus}`.toLowerCase().includes(q)) as unknown as Record<string, unknown>[];
});
const row = (r: Record<string, unknown>) => r as unknown as CourseClass;
const columns = computed<Column[]>(() => [
  { key: "course", label: "Module" },
  { key: "campus", label: "Campus", wide: true },
  { key: "students", label: "Students", align: "right" },
  props.focus === "gradebook"
    ? { key: "plan", label: "Assessment plan" }
    : props.focus === "marks"
      ? { key: "marks", label: "Marks" }
      : { key: "links", label: "", align: "right" },
]);
const title = computed(() => (props.focus === "timetable" ? "My timetable" : focused.value?.title ?? "My modules"));
/** a row opens the module, or the tab the menu item is for (and Back returns to that list) */
const rowLink = (r: Record<string, unknown>) =>
  focused.value
    ? { name: focused.value.route, params: { group: String(r.name) }, query: { from: focused.value.from } }
    : { name: "my-class", params: { group: String(r.name) } };
</script>

<template>
  <section class="teaching">
    <PageHeader :title="title" :subtitle="focus === 'timetable' ? undefined : subtitle">
      <template v-if="data?.linked && data.academic_years.length && tab === 'modules'" #actions>
        <Select v-model="academicYear" :options="data.academic_years" aria-label="Academic year" class="year" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <Message v-else-if="data && !data.linked" severity="info" :closable="false">
      You are not on record as a lecturer. Ask your head of department.
    </Message>

    <template v-else>
      <template v-if="data?.linked && tab === 'timetable'">
        <MyWeek :lecturers="false" />
        <MyExams duties />
      </template>

      <DataTable
        v-if="tab === 'modules'"
        :columns="columns"
        :rows="rows"
        row-key="name"
        :to="rowLink"
        :loading="loading"
        noun="modules"
        :empty-title="search ? 'No module matches' : `You are not assigned to any module in ${academicYear ?? 'this year'}`"
      >
        <template #toolbar>
          <IconField class="search">
            <InputIcon><Search :size="15" /></InputIcon>
            <InputText v-model="search" placeholder="Module code or name" aria-label="Search modules" fluid size="small" />
          </IconField>
        </template>
        <template #cell-course="{ row: r }">
          <span class="who"><span class="code">{{ row(r).code }}</span> {{ row(r).course }}</span>
          <span class="sub">
            {{ row(r).academic_year }}<template v-if="row(r).credits"> · {{ row(r).credits }} credits</template><template v-if="row(r).co_lecturers.length"> · with {{ row(r).co_lecturers.join(", ") }}</template>
          </span>
        </template>
        <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
        <template #cell-students="{ row: r }">{{ row(r).students.length }}</template>
        <template #cell-plan="{ row: r }">
          <StatusTag v-if="row(r).plan_status" kind="plan" :value="row(r).plan_status === 'Draft' ? null : row(r).plan_status" />
          <span v-else-if="row(r).students.length" class="sub">Not set up</span>
        </template>
        <template #cell-marks="{ row: r }"><StatusTag kind="marks" :value="row(r).marks_status" /></template>
        <template #cell-links="{ row: r }">
          <span v-if="row(r).students.length" class="links">
            <RouterLink :to="{ name: 'class-attendance', params: { group: row(r).name } }">Attendance</RouterLink>
            <RouterLink :to="{ name: 'class-marks', params: { group: row(r).name } }">Marks</RouterLink>
          </span>
        </template>
      </DataTable>
    </template>
  </section>
</template>

<style scoped>
.teaching {
  display: grid;
  gap: 1rem;
}

.tabs {
  flex: 1;
}

.year {
  min-width: 9rem;
}

.search {
  flex: 1;
  max-width: 22rem;
}

.who {
  display: block;
}

.code {
  color: var(--color-brand-navy);
  font-weight: 600;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 400;
}

.links {
  display: inline-flex;
  gap: 0.9rem;
}

.links a {
  color: var(--ec-accent);
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.links a:hover {
  text-decoration: underline;
}
</style>
