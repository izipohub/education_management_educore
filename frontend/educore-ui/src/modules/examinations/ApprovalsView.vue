<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type SheetRow, type SheetsPage, listSheets } from "./api";

/**
 * The department's approvals in one queue: lecturers' assessment plans to approve and marks to moderate. A row opens
 * the module's mark sheet, where the plan is approved or returned and the marks moderated (Back returns here).
 */
type Kind = "all" | "plans" | "marks";
const page = ref<SheetsPage | null>(null);
const year = ref<string | undefined>();
const kind = ref<Kind>("all");
const search = ref("");
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    page.value = await listSheets(year.value);
    year.value = page.value.academic_year ?? undefined;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(year, (y, before) => {
  if (before !== undefined && y !== page.value?.academic_year) void load();
});

const isPlan = (r: SheetRow) => r.status === "Draft" && r.plan_status === "Proposed";
const isMarks = (r: SheetRow) => r.status === "Submitted";
const waiting = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (page.value?.rows ?? []).filter((r) => (isPlan(r) || isMarks(r)) && (!q || `${r.code} ${r.course} ${r.lecturers.join(" ")}`.toLowerCase().includes(q)));
});
const kinds = computed(() => [
  { value: "all" as Kind, label: `All ${waiting.value.length}` },
  { value: "plans" as Kind, label: `Assessment plans ${waiting.value.filter(isPlan).length}` },
  { value: "marks" as Kind, label: `Marks ${waiting.value.filter(isMarks).length}` },
]);
const rows = computed(
  () => waiting.value.filter((r) => kind.value === "all" || (kind.value === "plans" ? isPlan(r) : isMarks(r))) as unknown as Record<string, unknown>[],
);
const row = (r: Record<string, unknown>) => r as unknown as SheetRow;
const columns: Column[] = [
  { key: "course", label: "Module" },
  { key: "campus", label: "Campus", wide: true },
  { key: "lecturers", label: "Lecturers", wide: true },
  { key: "what", label: "To do" },
];
</script>

<template>
  <section class="list-page">
    <PageHeader title="Approvals" subtitle="Assessment plans to approve and marks to moderate">
      <template #actions>
        <Select v-model="year" :options="page?.academic_years ?? []" placeholder="Year" aria-label="Academic year" size="small" class="year" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="rows"
      row-key="group"
      :to="(r) => ({ name: 'mark-sheet', params: { group: String(r.group) }, query: { from: 'approvals' } })"
      :loading="loading"
      noun="modules"
      empty-title="Nothing waiting for approval"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Module or lecturer" aria-label="Search" fluid size="small" />
        </IconField>
        <EcSegmented v-model="kind" :options="kinds" label="Show" />
      </template>
      <template #cell-course="{ row: r }">
        <span class="who">{{ row(r).code }}</span>
        <span class="sub">{{ row(r).course }}</span>
      </template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-lecturers="{ row: r }">{{ row(r).lecturers.join(", ") }}</template>
      <template #cell-what="{ row: r }">{{ isPlan(row(r)) ? "Approve the assessment plan" : "Moderate the marks" }}</template>
    </DataTable>
  </section>
</template>

<style scoped>
.list-page {
  display: grid;
  gap: 1rem;
}

.year {
  width: 7.5rem;
}

.search {
  flex: 1;
  max-width: 20rem;
}

.who {
  display: block;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
}
</style>
