<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatDate } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type CaseRow, type CaseStatus, listCases, saveDisciplineRules } from "./discipline";

/**
 * Disciplinary cases of the campus (every campus for the Registrar), by where they stand. Confidential. A row opens
 * the case. The Registrar sets the days a student has to appeal.
 */
type Tab = "Reported" | "Investigating" | "Hearing" | "Decided" | "Appealed" | "closed";
const TABS: Tab[] = ["Reported", "Investigating", "Hearing", "Decided", "Appealed", "closed"];
const route = useRoute();
const router = useRouter();
const toast = useToast();
const tab = ref<Tab>(TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : "Reported");
const rows = ref<CaseRow[]>([]);
const appealDays = ref(10);
const canSetRules = ref(false);
const search = ref("");
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  try {
    const page = await listCases();
    rows.value = page.rows;
    appealDays.value = page.appeal_days;
    canSetRules.value = page.can_set_rules;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(tab, (t) => void router.replace({ query: t === "Reported" ? {} : { tab: t } }));

const closed: CaseStatus[] = ["Closed", "Dismissed"];
const inTab = (r: CaseRow, t: Tab) => (t === "closed" ? closed.includes(r.status) : r.status === t);
const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((r) => !q || `${r.student_name} ${r.student}`.toLowerCase().includes(q));
});
const tabs = computed(() => [
  { label: "Reported", value: "Reported" as Tab, count: matching.value.filter((r) => inTab(r, "Reported")).length },
  { label: "Investigating", value: "Investigating" as Tab, count: matching.value.filter((r) => inTab(r, "Investigating")).length },
  { label: "Hearing", value: "Hearing" as Tab, count: matching.value.filter((r) => inTab(r, "Hearing")).length },
  { label: "Decided", value: "Decided" as Tab, count: matching.value.filter((r) => inTab(r, "Decided")).length },
  { label: "Appealed", value: "Appealed" as Tab, count: matching.value.filter((r) => inTab(r, "Appealed")).length },
  { label: "Closed", value: "closed" as Tab },
]);
const shown = computed(() => matching.value.filter((r) => inTab(r, tab.value)) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as CaseRow;
const columns = computed<Column[]>(() => [
  { key: "student_name", label: "Student" },
  { key: "incident_date", label: "Incident" },
  { key: "when", label: tab.value === "Hearing" ? "Hearing" : tab.value === "Appealed" ? "Appealed" : "Reported", wide: true },
  { key: "status", label: "Status" },
]);

// the days to appeal (Registrar)
const editing = ref(false);
const days = ref(10);
async function saveRule() {
  try {
    appealDays.value = (await saveDisciplineRules(days.value)).appeal_days;
    editing.value = false;
    toast.add({ severity: "success", summary: "Saved", life: 2000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Discipline" subtitle="Misconduct reported, investigated, heard and decided. Confidential">
      <EcTabs v-model="tab" :tabs="tabs" label="Cases" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="shown"
      row-key="name"
      :to="(r) => ({ name: 'disciplinary-case', params: { name: String(r.name) }, query: route.query })"
      :loading="loading"
      noun="cases"
      empty-title="No cases here"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Student" aria-label="Search cases" fluid size="small" />
        </IconField>
        <span class="rule">
          <span class="ec-muted">Appeals within {{ appealDays }} days</span>
          <EcButton v-if="canSetRules" label="Change" variant="ghost" size="sm" @click="(days = appealDays), (editing = true)" />
        </span>
      </template>
      <template #cell-student_name="{ row: r }">
        <span class="who">{{ row(r).student_name }}</span>
        <span class="sub">{{ row(r).student }} · {{ row(r).campus?.replace(" Campus", "") }}</span>
      </template>
      <template #cell-incident_date="{ row: r }">{{ formatDate(row(r).incident_date) }}</template>
      <template #cell-when="{ row: r }">
        {{ formatDate(tab === "Hearing" ? row(r).hearing_on : tab === "Appealed" ? row(r).appealed_on : row(r).reported_on) }}
      </template>
      <template #cell-status="{ row: r }">
        <StatusTag kind="discipline" :value="row(r).status" />
        <span v-if="row(r).sanction" class="sub">{{ row(r).sanction }}</span>
        <span v-else-if="row(r).level" class="sub">{{ row(r).level }}</span>
      </template>
    </DataTable>
  </section>

  <EcModal v-model:open="editing" title="Days to appeal" description="From the day the student is told of the decision">
    <EcField label="Days" for="appeal-days">
      <InputNumber v-model="days" input-id="appeal-days" :min="1" :max="60" show-buttons fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="editing = false" />
      <EcButton label="Save" variant="primary" @click="saveRule" />
    </template>
  </EcModal>
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
  flex: 1;
  max-width: 20rem;
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
</style>
