<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type ClearanceRow, listClearance } from "./clearance";

/** Financial clearance: students on hold, owing more than allowed, or cleared; a row opens the student */
type Tab = "hold" | "owing" | "cleared";
const route = useRoute();
const router = useRouter();
const tab = ref<Tab>((route.query.tab as Tab) || "hold");
const search = ref("");
const rows = ref<ClearanceRow[]>([]);
const maxOwing = ref(0);
const loading = ref(false);
const error = ref("");

onMounted(async () => {
  loading.value = true;
  try {
    const page = await listClearance();
    rows.value = page.rows;
    maxOwing.value = page.max_owing;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
});
watch(tab, () => void router.replace({ query: tab.value === "hold" ? {} : { tab: tab.value } }));

const inTab = (r: ClearanceRow, t: Tab) => (t === "hold" ? r.holds > 0 : t === "owing" ? r.owing > maxOwing.value : r.cleared);
const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((r) => !q || `${r.student_name} ${r.name}`.toLowerCase().includes(q));
});
const tabs = computed(() => [
  { label: "On hold", value: "hold" as Tab, count: matching.value.filter((r) => inTab(r, "hold")).length },
  { label: "Owing", value: "owing" as Tab, count: matching.value.filter((r) => inTab(r, "owing")).length },
  { label: "Cleared", value: "cleared" as Tab, count: matching.value.filter((r) => inTab(r, "cleared")).length },
]);
const shown = computed(() => matching.value.filter((r) => inTab(r, tab.value)) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as ClearanceRow;
const columns: Column[] = [
  { key: "student_name", label: "Student" },
  { key: "campus", label: "Campus", wide: true },
  { key: "owing", label: "Owing", align: "right" },
  { key: "holds", label: "Holds", align: "right" },
];
</script>

<template>
  <section class="list-page">
    <PageHeader title="Financial clearance" subtitle="Holds placed by Finance, and what students owe">
      <EcTabs v-model="tab" :tabs="tabs" label="Clearance" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="shown"
      row-key="name"
      :to="(r) => ({ name: 'clearance-student', params: { name: String(r.name) }, query: route.query })"
      :loading="loading"
      noun="students"
      :empty-title="tab === 'hold' ? 'No student on hold' : tab === 'owing' ? 'No student owes more than allowed' : 'No student cleared'"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name or student number" aria-label="Search students" fluid size="small" />
        </IconField>
      </template>
      <template #cell-student_name="{ row: r }">
        <span class="who">{{ row(r).student_name }}</span>
        <span class="sub">{{ row(r).name }}</span>
      </template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-owing="{ row: r }"><span class="ec-nowrap">{{ row(r).owing ? formatMoney(row(r).owing) : "Nothing" }}</span></template>
      <template #cell-holds="{ row: r }">{{ row(r).holds || "" }}</template>
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
