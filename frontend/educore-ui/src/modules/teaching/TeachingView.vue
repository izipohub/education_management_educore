<script setup lang="ts">
import { RefreshCw, Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Semester, semesterLabel } from "@/modules/curriculum/api";
import { type Allocation, type ClassRow, getAllocation, updateClassLists } from "./allocation";

/**
 * Teaching allocation: each course taught this year on each campus, with its class list (from approved
 * registrations) and its lecturers; a row opens the class. The head of department or the dean allocates.
 */
type Period = "all" | Semester;
const route = useRoute();
const router = useRouter();
const toast = useToast();
const year = ref<string | undefined>((route.query.year as string) || undefined);
const period = ref<Period>((route.query.period as Period) || "all");
const campus = ref<string | null>((route.query.campus as string) || null);
const search = ref("");
const data = ref<Allocation | null>(null);
const loading = ref(false);
const error = ref("");

let adopting = false;
async function load() {
  loading.value = true;
  error.value = "";
  try {
    data.value = await getAllocation(year.value);
    if (!year.value && data.value.academic_year) {
      adopting = true;
      year.value = data.value.academic_year;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(year, () => {
  if (adopting) {
    adopting = false;
    return;
  }
  void load();
});
watch([year, period, campus], () => {
  const query: Record<string, string> = {};
  if (year.value) query.year = year.value;
  if (period.value !== "all") query.period = period.value;
  if (campus.value) query.campus = campus.value;
  void router.replace({ query });
});

const inScope = computed(() =>
  (data.value?.rows ?? []).filter((r) => {
    if (campus.value && r.campus !== campus.value) return false;
    const q = search.value.trim().toLowerCase();
    return !q || `${r.code} ${r.course_name} ${r.lecturers.join(" ")}`.toLowerCase().includes(q);
  }),
);
const tabs = computed(() => {
  const count = (p: Period) => inScope.value.filter((r) => p === "all" || r.semester === p).length;
  return [
    { label: "All", value: "all" as Period, count: count("all") },
    { label: "Semester 1", value: "Semester 1" as Period, count: count("Semester 1") },
    { label: "Semester 2", value: "Semester 2" as Period, count: count("Semester 2") },
    { label: "Full year", value: "Year" as Period, count: count("Year") },
  ];
});
const rows = computed(() => inScope.value.filter((r) => period.value === "all" || r.semester === period.value) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as ClassRow;
const columns: Column[] = [
  { key: "course_name", label: "Course" },
  { key: "campus", label: "Campus", wide: true },
  { key: "semester", label: "Runs in", wide: true },
  { key: "students", label: "Students", align: "right" },
  { key: "lecturers", label: "Lecturers" },
  { key: "state", label: "Status" },
];

const updating = ref(false);
async function update() {
  if (!year.value) return;
  updating.value = true;
  try {
    const result = await updateClassLists(year.value);
    data.value = result;
    const done = [result.made && `${result.made} classes made`, result.updated && `${result.updated} updated`].filter(Boolean).join(", ");
    toast.add({ severity: "success", summary: done || "Class lists are up to date", life: 3000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not updated", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    updating.value = false;
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Teaching" subtitle="Classes by course and campus, their students and lecturers">
      <template #actions>
        <EcButton v-if="data?.can_edit" label="Update class lists" :icon="RefreshCw" :loading="updating" @click="update" />
        <Select v-model="year" :options="data?.academic_years ?? []" placeholder="Year" aria-label="Academic year" size="small" class="year" />
      </template>
      <EcTabs v-model="period" :tabs="tabs" label="Period" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="rows"
      row-key="key"
      :to="(r) => (r.group ? { name: 'teaching-class', params: { group: String(r.group) }, query: route.query } : null)"
      :loading="loading"
      noun="classes"
      empty-title="No classes this year"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Course, code or lecturer" aria-label="Search classes" fluid size="small" />
        </IconField>
        <Select v-if="(data?.campuses.length ?? 0) > 1" v-model="campus" :options="data?.campuses ?? []" placeholder="All campuses" show-clear size="small" aria-label="Campus" class="filter" />
      </template>

      <template #cell-course_name="{ row: r }">
        <span class="who">{{ row(r).course_name }}</span>
        <span class="sub">{{ row(r).code }} · {{ row(r).department }}</span>
      </template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-semester="{ row: r }"><span class="ec-nowrap">{{ semesterLabel(row(r).semester) }}</span></template>
      <template #cell-students="{ row: r }">
        <span class="ec-nowrap">{{ row(r).in_class }}</span>
        <span v-if="row(r).in_class !== row(r).registered" class="sub">{{ row(r).registered }} registered</span>
      </template>
      <template #cell-lecturers="{ row: r }">
        <span v-if="row(r).lecturers.length">{{ row(r).lecturers.join(", ") }}</span>
        <span v-else class="ec-muted">None yet</span>
      </template>
      <template #cell-state="{ row: r }"><StatusTag kind="class" :value="row(r).state" /></template>
    </DataTable>
  </section>
</template>

<style scoped>
.list-page {
  display: grid;
  gap: 1rem;
}

.tabs {
  flex: 1;
}

.year {
  width: 7.5rem;
}

.search {
  flex: 1;
  max-width: 22rem;
}

.filter {
  min-width: 10rem;
}

.who {
  display: block;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 400;
  white-space: nowrap;
}
</style>
