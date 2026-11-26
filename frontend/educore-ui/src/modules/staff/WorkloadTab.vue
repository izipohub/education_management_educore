<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type WorkloadPage, type WorkloadRow, getWorkload, saveWorkloadRule } from "./api";

/**
 * Lecturer workload for a semester: each lecturer's modules, students, contact hours a week (from the timetable) and
 * invigilation hours, against the university's rule. The Registrar sets the rule.
 */
const route = useRoute();
const router = useRouter();
const toast = useToast();
const page = ref<WorkloadPage | null>(null);
const year = ref<string | null>((route.query.year as string) || null);
const semester = ref<string>((route.query.semester as string) || "");
const search = ref("");
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  try {
    page.value = await getWorkload(year.value, semester.value || null);
    year.value = page.value.academic_year;
    semester.value = page.value.semester;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
void load();
watch([year, semester], ([y, s]) => {
  if (!page.value || (y === page.value.academic_year && s === page.value.semester)) return;
  void router.replace({ query: { ...route.query, year: y ?? undefined, semester: s || undefined } });
  void load();
});

const hours = (n: number | undefined) => `${Number((n ?? 0).toFixed(1))} h`;
const rows = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (page.value?.rows ?? []).filter((r) => !q || `${r.instructor_name} ${r.department}`.toLowerCase().includes(q)) as unknown as Record<string, unknown>[];
});
const row = (r: Record<string, unknown>) => r as unknown as WorkloadRow;
const columns: Column[] = [
  { key: "instructor_name", label: "Lecturer" },
  { key: "department", label: "Department", wide: true },
  { key: "modules", label: "Modules", align: "right" },
  { key: "students", label: "Students", align: "right", wide: true },
  { key: "hours", label: "Hours a week", align: "right" },
  { key: "invigilation", label: "Invigilation", align: "right", wide: true },
  { key: "status", label: "Load" },
];
const semesters = computed(() => (page.value?.semesters ?? []).map((s) => ({ value: s, label: s })));

// the rule (Registrar)
const editing = ref(false);
const saving = ref(false);
const least = ref(0);
const most = ref(0);
function editRule() {
  least.value = page.value?.rule.min_hours ?? 0;
  most.value = page.value?.rule.max_hours ?? 0;
  editing.value = true;
}
async function saveRule() {
  saving.value = true;
  try {
    await saveWorkloadRule({ min_hours: least.value, max_hours: most.value });
    editing.value = false;
    toast.add({ severity: "success", summary: "Rule saved", life: 2500 });
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

  <DataTable
    :columns="columns"
    :rows="rows"
    row-key="name"
    :to="(r) => ({ name: 'lecturer', params: { name: String(r.name) }, query: { ...route.query, from: 'workload' } })"
    :loading="loading"
    noun="lecturers"
    empty-title="No lecturers"
  >
    <template #toolbar>
      <IconField class="search">
        <InputIcon><Search :size="15" /></InputIcon>
        <InputText v-model="search" placeholder="Name or department" aria-label="Search lecturers" fluid size="small" />
      </IconField>
      <Select v-model="year" :options="page?.academic_years ?? []" placeholder="Year" aria-label="Academic year" size="small" class="year" />
      <EcSegmented v-if="semesters.length" v-model="semester" :options="semesters" label="Semester" />
      <span v-if="page" class="rule">
        <span class="ec-muted">{{ page.rule.min_hours }} to {{ page.rule.max_hours }} h a week</span>
        <EcButton v-if="page.can_edit_rule" label="Change" variant="ghost" size="sm" @click="editRule" />
      </span>
    </template>

    <template #cell-instructor_name="{ row: r }">
      <span class="who">{{ row(r).instructor_name }}</span>
      <span v-if="row(r).campuses?.length" class="sub">{{ row(r).campuses!.map((c) => c.replace(" Campus", "")).join(", ") }}</span>
    </template>
    <template #cell-modules="{ row: r }">{{ row(r).modules || "" }}</template>
    <template #cell-students="{ row: r }">{{ row(r).students || "" }}</template>
    <template #cell-hours="{ row: r }">{{ row(r).modules ? hours(row(r).hours) : "" }}</template>
    <template #cell-invigilation="{ row: r }">{{ row(r).invigilation ? hours(row(r).invigilation) : "" }}</template>
    <template #cell-status="{ row: r }"><StatusTag kind="workload" :value="row(r).status" /></template>
  </DataTable>

  <EcModal :open="editing" title="Contact hours a week" description="The load expected of a lecturer in a semester" @update:open="(v: boolean) => (editing = v)">
    <div class="form">
      <EcField label="At least" for="workload-least" hint="Below it the load is light">
        <InputNumber v-model="least" input-id="workload-least" :min="0" :max="60" :max-fraction-digits="1" suffix=" h" show-buttons fluid />
      </EcField>
      <EcField label="At most" for="workload-most" hint="Above it the lecturer is over the load">
        <InputNumber v-model="most" input-id="workload-most" :min="1" :max="60" :max-fraction-digits="1" suffix=" h" show-buttons fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="editing = false" />
      <EcButton label="Save" variant="primary" :loading="saving" :disabled="least > most" @click="saveRule" />
    </template>
  </EcModal>
</template>

<style scoped>
.search {
  flex: 1;
  max-width: 22rem;
}

.year {
  width: 7.5rem;
}

.rule {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-left: auto;
  font-size: 0.85rem;
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
}

.form {
  display: grid;
  gap: 0.75rem;
}
</style>
