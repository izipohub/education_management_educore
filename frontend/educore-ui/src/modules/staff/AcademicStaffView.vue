<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type LecturerRow, type LecturerState, listStaff } from "./api";
import WorkloadTab from "./WorkloadTab.vue";

/**
 * Academic staff: the lecturers of the department or faculty, the classes they teach this year, and what is still
 * missing from their setup (department, campus, HR staff record), and each lecturer's workload in a semester. A row
 * opens the lecturer.
 */
type Tab = "active" | "Incomplete" | "Left" | "workload";
const route = useRoute();
const router = useRouter();
const tab = ref<Tab>((route.query.tab as Tab) || "active");
const search = ref("");
const rows = ref<LecturerRow[]>([]);
const year = ref<string | null>(null);
const loading = ref(false);
const error = ref("");

onMounted(async () => {
  loading.value = true;
  try {
    const page = await listStaff();
    rows.value = page.rows;
    year.value = page.academic_year;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
});
watch(tab, () => void router.replace({ query: tab.value === "active" ? {} : { tab: tab.value } }));

const inTab = (r: LecturerRow, t: Tab) => (t === "active" ? r.state !== "Left" : r.state === (t as LecturerState));
const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((r) => !q || `${r.instructor_name} ${r.user ?? ""} ${r.department}`.toLowerCase().includes(q));
});
const tabs = computed(() => [
  { label: "Active", value: "active" as Tab, count: matching.value.filter((r) => inTab(r, "active")).length },
  { label: "Incomplete", value: "Incomplete" as Tab, count: matching.value.filter((r) => inTab(r, "Incomplete")).length },
  { label: "Left", value: "Left" as Tab, count: matching.value.filter((r) => inTab(r, "Left")).length },
  { label: "Workload", value: "workload" as Tab },
]);
const shown = computed(() => matching.value.filter((r) => inTab(r, tab.value)) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as LecturerRow;
const columns = computed<Column[]>(() => [
  { key: "instructor_name", label: "Lecturer" },
  { key: "department", label: "Department", wide: true },
  { key: "campuses", label: "Campus", wide: true },
  { key: "classes", label: year.value ? `Classes ${year.value}` : "Classes", align: "right" },
  { key: "state", label: "Status" },
]);
</script>

<template>
  <section class="list-page">
    <PageHeader title="Academic staff" subtitle="Lecturers, the classes they teach and what their setup still needs">
      <EcTabs v-model="tab" :tabs="tabs" label="Lecturers" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <WorkloadTab v-if="tab === 'workload'" />

    <DataTable
      v-else
      :columns="columns"
      :rows="shown"
      row-key="name"
      :to="(r) => ({ name: 'lecturer', params: { name: String(r.name) }, query: route.query })"
      :loading="loading"
      noun="lecturers"
      :empty-title="tab === 'Incomplete' ? 'Every lecturer is set up' : 'No lecturers'"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name, login or department" aria-label="Search lecturers" fluid size="small" />
        </IconField>
      </template>

      <template #cell-instructor_name="{ row: r }">
        <span class="who">{{ row(r).instructor_name }}</span>
        <span class="sub">{{ row(r).user }}</span>
      </template>
      <template #cell-department="{ row: r }">
        <span v-if="row(r).department">{{ row(r).department }}</span>
        <span v-else class="ec-muted">Not set</span>
      </template>
      <template #cell-campuses="{ row: r }">
        <span v-if="row(r).campuses.length">{{ row(r).campuses.map((c) => c.replace(" Campus", "")).join(", ") }}</span>
        <span v-else class="ec-muted">Not set</span>
      </template>
      <template #cell-classes="{ row: r }">{{ row(r).classes || "" }}</template>
      <template #cell-state="{ row: r }">
        <StatusTag kind="lecturer" :value="row(r).state" />
        <span v-if="row(r).state === 'Incomplete'" class="sub">{{ row(r).missing.join(", ") }} missing</span>
      </template>
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
  flex: 1;
  max-width: 22rem;
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
