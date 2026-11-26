<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatDate } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type QueueRow, serviceQueue } from "./serviceRequests";

/**
 * Service requests for this person's offices: to answer (oldest first, the overdue marked), their own, and those
 * closed. A row opens the request.
 */
type Tab = "open" | "overdue" | "mine" | "closed";
const TABS: Tab[] = ["open", "overdue", "mine", "closed"];
const route = useRoute();
const router = useRouter();
const tab = ref<Tab>(TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : "open");
const rows = ref<QueueRow[]>([]);
const offices = ref<string[]>([]);
const search = ref("");
const loading = ref(false);
const error = ref("");

onMounted(async () => {
  loading.value = true;
  try {
    const page = await serviceQueue();
    rows.value = page.rows;
    offices.value = page.offices;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
});
watch(tab, (t) => void router.replace({ query: t === "open" ? {} : { tab: t } }));

const isOpen = (r: QueueRow) => r.status === "Submitted" || r.status === "In progress";
const inTab = (r: QueueRow, t: Tab) => (t === "open" ? isOpen(r) : t === "overdue" ? r.overdue : t === "mine" ? r.mine && isOpen(r) : !isOpen(r));
const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((r) => !q || `${r.student_name} ${r.student} ${r.category}`.toLowerCase().includes(q));
});
const tabs = computed(() => [
  { label: "To answer", value: "open" as Tab, count: matching.value.filter((r) => inTab(r, "open")).length },
  { label: "Overdue", value: "overdue" as Tab, count: matching.value.filter((r) => inTab(r, "overdue")).length },
  { label: "Mine", value: "mine" as Tab, count: matching.value.filter((r) => inTab(r, "mine")).length },
  { label: "Closed", value: "closed" as Tab },
]);
const shown = computed(() => {
  const list = matching.value.filter((r) => inTab(r, tab.value));
  return (tab.value === "closed" ? [...list].reverse() : list) as unknown as Record<string, unknown>[];
});
const row = (r: Record<string, unknown>) => r as unknown as QueueRow;
const columns = computed<Column[]>(() => [
  { key: "student_name", label: "Student" },
  { key: "category", label: "Request" },
  ...(offices.value.length > 1 ? [{ key: "office", label: "Office", wide: true }] : []),
  { key: "due_on", label: tab.value === "closed" ? "Asked" : "Due" },
  { key: "status", label: "Status" },
]);
</script>

<template>
  <section class="list-page">
    <PageHeader title="Service requests" subtitle="What students ask the offices for, and the answers">
      <EcTabs v-model="tab" :tabs="tabs" label="Requests" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="shown"
      row-key="name"
      :to="(r) => ({ name: 'service-request', params: { name: String(r.name) }, query: route.query })"
      :loading="loading"
      noun="requests"
      :empty-title="tab === 'overdue' ? 'Nothing overdue' : tab === 'closed' ? 'Nothing closed yet' : 'Nothing waiting'"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Student or request" aria-label="Search requests" fluid size="small" />
        </IconField>
      </template>
      <template #cell-student_name="{ row: r }">
        <span class="who">{{ row(r).student_name }}</span>
        <span class="sub">{{ row(r).student }} · {{ row(r).campus?.replace(" Campus", "") }}</span>
      </template>
      <template #cell-due_on="{ row: r }">
        <template v-if="tab === 'closed'">{{ formatDate(row(r).submitted_on) }}</template>
        <template v-else>
          {{ formatDate(row(r).due_on) }}
          <span v-if="row(r).overdue" class="sub">Overdue</span>
        </template>
      </template>
      <template #cell-status="{ row: r }">
        <StatusTag kind="service" :value="row(r).status" />
        <span v-if="row(r).assigned_to && isOpen(row(r))" class="sub">{{ row(r).assigned_to }}</span>
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
