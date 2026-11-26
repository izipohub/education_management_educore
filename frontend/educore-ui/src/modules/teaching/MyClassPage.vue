<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import ReportMisconductModal from "@/modules/records/ReportMisconductModal.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import GradebookTab from "@/modules/examinations/GradebookTab.vue";
import MarksTab from "@/modules/examinations/MarksTab.vue";
import AttendanceTab from "./AttendanceTab.vue";
import { type ClassStudent, type CourseClass, getMyClasses } from "./api";

/** One of the lecturer's modules: its students, its registers per lesson, its gradebook (the CA's assessments) and
 * its marks, a tab each (each its own address,
 * so Back and a shared link return to the same tab) */
type Tab = "students" | "attendance" | "gradebook" | "marks";
const props = withDefaults(defineProps<{ group: string; tab?: Tab }>(), { tab: "students" });
const router = useRouter();
const cls = ref<CourseClass | null>(null);
const error = ref("");
const search = ref("");
/** reporting a student's misconduct to Student Affairs */
const reporting = ref(false);

onMounted(async () => {
  try {
    // the class's year: from its name ("CMP1511 WHK 2026"), else the current year
    const year = props.group.match(/(\d{4})$/)?.[1];
    const data = await getMyClasses(year);
    cls.value = data.classes.find((c) => c.name === props.group) ?? null;
    if (!cls.value) error.value = "You do not teach this module.";
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

/** Back: to the list the module was opened from (My modules, or the menu's Attendance, Gradebook or Marks) */
const route = useRoute();
const FROM: Record<string, string> = { "my-attendance": "Attendance", "my-gradebook": "Gradebook", "my-marks": "Marks" };
const from = computed(() => (typeof route.query.from === "string" && FROM[route.query.from] ? route.query.from : null));
const back = computed(() => (from.value ? { to: { name: from.value }, label: FROM[from.value]! } : { to: { name: "my-teaching" }, label: "My modules" }));
const ROUTES: Record<Tab, string> = { students: "my-class", attendance: "class-attendance", gradebook: "class-gradebook", marks: "class-marks" };
const current = computed({
  get: () => props.tab,
  set: (t: Tab) => void router.replace({ name: ROUTES[t], params: { group: props.group }, query: route.query }),
});
const tabs = computed(() => [
  { value: "students" as Tab, label: "Students", count: cls.value?.students.length },
  ...(cls.value?.students.length ? [
          { value: "attendance" as Tab, label: "Attendance" },
          { value: "gradebook" as Tab, label: "Gradebook" },
          { value: "marks" as Tab, label: "Marks" },
        ] : []),
]);

const title = computed(() => (cls.value ? `${cls.value.code} ${cls.value.course}` : undefined));
const subtitle = computed(() => {
  const c = cls.value;
  if (!c) return undefined;
  return [c.campus, c.academic_year, c.credits ? `${c.credits} credits` : null, c.nqf_level ? `NQF level ${c.nqf_level}` : null, c.co_lecturers.length ? `with ${c.co_lecturers.join(", ")}` : null]
    .filter(Boolean)
    .join(" · ");
});
const rows = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (cls.value?.students ?? []).filter((s) => !q || `${s.student_name} ${s.student}`.toLowerCase().includes(q)) as unknown as Record<string, unknown>[];
});
const row = (r: Record<string, unknown>) => r as unknown as ClassStudent;
const columns: Column[] = [
  { key: "student_name", label: "Student" },
  { key: "programme", label: "Programme", wide: true },
];
</script>

<template>
  <RecordPage :back="back" :title="title" :subtitle="subtitle" :error="error" :loading="!cls && !error">
    <div class="module">
      <EcTabs v-model="current" :tabs="tabs" label="Module" />

      <DataTable v-if="cls && tab === 'students'" :columns="columns" :rows="rows" row-key="student" noun="students" :empty-title="search ? 'No student matches' : 'No students in this module yet'">
        <template #toolbar>
          <IconField class="search">
            <InputIcon><Search :size="15" /></InputIcon>
            <InputText v-model="search" placeholder="Name or student number" aria-label="Search students" fluid size="small" />
          </IconField>
          <span class="spacer" />
          <EcButton label="Report misconduct" variant="ghost" size="sm" @click="reporting = true" />
        </template>
        <template #cell-student_name="{ row: r }">
          <span class="who">{{ row(r).student_name }}</span>
          <span class="sub">{{ row(r).student }}</span>
        </template>
        <template #cell-programme="{ row: r }">
          {{ row(r).programme }}
          <span class="sub">{{ row(r).offering }}<template v-if="row(r).mode_of_study"> · {{ row(r).mode_of_study }}</template></span>
        </template>
      </DataTable>
      <AttendanceTab v-else-if="tab === 'attendance'" :group="group" />
      <GradebookTab v-else-if="tab === 'gradebook'" :group="group" />
      <MarksTab v-else-if="tab === 'marks'" :group="group" />
    </div>
  </RecordPage>
  <ReportMisconductModal v-if="cls" v-model:open="reporting" :students="cls.students.map((x) => ({ student: x.student, student_name: x.student_name }))" />
</template>

<style scoped>
.spacer {
  flex: 1;
}

.module {
  display: grid;
  gap: 1rem;
}

.search {
  flex: 1;
  max-width: 22rem;
}

.who {
  display: block;
  font-weight: 600;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 400;
}
</style>
