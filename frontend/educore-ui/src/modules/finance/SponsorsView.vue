<script setup lang="ts">
import { Plus, Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type SponsorRow, listSponsors } from "./sponsors";

/**
 * Sponsors: the bursaries, loan funds and employers that pay students' fees, how many students each pays for in
 * the year, what it was invoiced and what it owes. A row opens the sponsor.
 */
type Tab = "active" | "owing" | "past";
const route = useRoute();
const router = useRouter();
const year = ref<string | undefined>((route.query.year as string) || undefined);
const tab = ref<Tab>((route.query.tab as Tab) || "active");
const search = ref("");
const rows = ref<SponsorRow[]>([]);
const years = ref<string[]>([]);
const loading = ref(false);
const error = ref("");

let adopting = false;
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const page = await listSponsors(year.value);
    rows.value = page.rows;
    years.value = page.academic_years;
    if (!year.value && page.academic_year) {
      adopting = true;
      year.value = page.academic_year;
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
watch([year, tab], () => {
  const query: Record<string, string> = {};
  if (year.value) query.year = year.value;
  if (tab.value !== "active") query.tab = tab.value;
  void router.replace({ query });
});

const inTab = (r: SponsorRow, t: Tab) => (t === "past" ? !!r.disabled : !r.disabled && (t === "active" || r.owing > 0));
const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((r) => !q || `${r.sponsor_name} ${r.name} ${r.sponsor_type}`.toLowerCase().includes(q));
});
const tabs = computed(() => [
  { label: "Sponsoring", value: "active" as Tab, count: matching.value.filter((r) => inTab(r, "active")).length },
  { label: "Owing", value: "owing" as Tab, count: matching.value.filter((r) => inTab(r, "owing")).length },
  { label: "No longer sponsoring", value: "past" as Tab, count: matching.value.filter((r) => inTab(r, "past")).length },
]);
const shown = computed(() => matching.value.filter((r) => inTab(r, tab.value)) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as SponsorRow;
const columns = computed<Column[]>(() => [
  { key: "sponsor_name", label: "Sponsor" },
  { key: "sponsor_type", label: "Type", wide: true },
  { key: "students", label: `Students ${year.value ?? ""}`.trim(), align: "right" },
  { key: "invoiced", label: `Invoiced ${year.value ?? ""}`.trim(), align: "right", wide: true },
  { key: "owing", label: "Owing", align: "right" },
]);
</script>

<template>
  <section class="list-page">
    <PageHeader title="Sponsors" subtitle="Bursaries, loan funds and employers paying students' fees">
      <template #actions>
        <EcButton label="New sponsor" :icon="Plus" @click="router.push({ name: 'sponsor', params: { name: 'new' } })" />
        <Select v-model="year" :options="years" placeholder="Year" aria-label="Academic year" size="small" class="year" />
      </template>
      <EcTabs v-model="tab" :tabs="tabs" label="Sponsors" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="shown"
      row-key="name"
      :to="(r) => ({ name: 'sponsor', params: { name: String(r.name) }, query: { ...route.query } })"
      :loading="loading"
      noun="sponsors"
      :empty-title="tab === 'owing' ? 'No sponsor owes anything' : 'No sponsors'"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name or sponsor number" aria-label="Search sponsors" fluid size="small" />
        </IconField>
      </template>

      <template #cell-sponsor_name="{ row: r }">
        <span class="who">{{ row(r).sponsor_name }}</span>
        <span class="sub">{{ row(r).name }}</span>
      </template>
      <template #cell-students="{ row: r }">{{ row(r).students || "" }}</template>
      <template #cell-invoiced="{ row: r }"><span class="ec-nowrap">{{ row(r).invoiced ? formatMoney(row(r).invoiced) : "" }}</span></template>
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

.year {
  width: 7.5rem;
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
