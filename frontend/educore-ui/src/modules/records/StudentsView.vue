<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type StudentRow, type StudentsPage, listStudents } from "./api";

/** The students the user may see (their campus and faculty), with filters; a row opens the student's record */
type Status = "Active" | "Left";
const route = useRoute();
const router = useRouter();
const q = route.query;
const status = ref<Status>(q.status === "Left" ? "Left" : "Active");
const campus = ref<string | null>((q.campus as string) || null);
const program = ref<string | null>((q.program as string) || null);
const standing = ref<string | null>((q.standing as string) || null);
const search = ref("");
const page = ref<StudentsPage | null>(null);
const loading = ref(false);
const loadError = ref("");

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await listStudents({
      status: status.value,
      search: search.value.trim() || undefined,
      campus: campus.value || undefined,
      program: program.value || undefined,
      standing: standing.value || undefined,
    });
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
let timer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(timer);
  timer = setTimeout(load, 300);
});
watch([status, campus, program, standing], () => {
  // the filters stay in the address, so Back from a student returns to the same list
  const query: Record<string, string> = {};
  if (status.value !== "Active") query.status = status.value;
  if (campus.value) query.campus = campus.value;
  if (program.value) query.program = program.value;
  if (standing.value) query.standing = standing.value;
  void router.replace({ query });
  void load();
});

const tabs = computed(() => [
  { label: "Active", value: "Active" as Status },
  { label: "Left", value: "Left" as Status },
]);
const rows = computed(() => (page.value?.rows ?? []) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as StudentRow;
const columns: Column[] = [
  { key: "student_name", label: "Student" },
  { key: "program", label: "Programme" },
  { key: "campus", label: "Campus", wide: true },
  { key: "academic_year", label: "Last registered", wide: true },
  { key: "standing", label: "Standing" },
  { key: "owing", label: "Owing", align: "right", wide: true },
];
</script>

<template>
  <section class="list-page">
    <PageHeader title="Students" subtitle="Students on the campuses and in the faculties you work on">
      <EcTabs v-model="status" :tabs="tabs" label="Status" class="tabs" />
    </PageHeader>

    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <DataTable
      :columns="columns"
      :rows="rows"
      row-key="name"
      :to="(r) => ({ name: 'student-record', params: { name: String(r.name) }, query: route.query })"
      :loading="loading"
      noun="students"
      empty-title="No students match"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name, student or ID number" aria-label="Search students" fluid size="small" />
        </IconField>
        <Select v-if="(page?.campuses.length ?? 0) > 1" v-model="campus" :options="page?.campuses ?? []" placeholder="All campuses" show-clear size="small" aria-label="Campus" class="filter" />
        <Select v-model="program" :options="page?.programmes ?? []" placeholder="All programmes" show-clear filter size="small" aria-label="Programme" class="filter wide-filter" />
        <Select v-model="standing" :options="page?.standings ?? []" placeholder="Any standing" show-clear size="small" aria-label="Standing" class="filter" />
      </template>

      <template #cell-student_name="{ row: r }">
        <span class="who">{{ row(r).student_name }}</span>
        <span class="sub">{{ row(r).name }}</span>
      </template>
      <template #cell-program="{ row: r }">
        <span class="programme">{{ row(r).program ?? "Not registered" }}</span>
        <span class="sub">{{ row(r).offering }}</span>
      </template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-standing="{ row: r }"><StatusTag kind="standing" :value="row(r).standing" /></template>
      <template #cell-owing="{ row: r }"><span class="ec-nowrap">{{ row(r).owing ? formatMoney(row(r).owing) : "Nothing" }}</span></template>
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

.search {
  flex: 1 1 16rem;
  max-width: 22rem;
}

.filter {
  min-width: 10rem;
}

.wide-filter {
  min-width: 14rem;
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

@media (max-width: 767px) {
  .programme {
    display: none;
  }

  .programme + .sub {
    margin-top: 0;
    color: inherit;
    font-size: inherit;
  }
}
</style>
