<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import { applicationLabel } from "@/core/status";
import { formatDate } from "@/core/format";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SplitView from "@/core/ui/SplitView.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import ApplicationDetail from "./ApplicationDetail.vue";
import { type Application, type ApplicationsPage, OCCASIONAL, type Places, STATUSES, type Status, listApplications } from "./api";

const status = ref<Status>("Applied");
const academicYear = ref<string | undefined>();
const search = ref("");
const page = ref<ApplicationsPage | null>(null);
const loading = ref(false);
const loadError = ref("");
const selected = ref<string | null>(null);

const statusOptions = computed(() =>
  STATUSES.filter((s) => !OCCASIONAL.includes(s) || (page.value?.counts[s] ?? 0) > 0 || s === status.value).map((s) => ({
    label: applicationLabel(s),
    count: page.value?.counts[s] ?? 0,
    value: s,
  })),
);

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await listApplications({ status: status.value, academic_year: academicYear.value, search: search.value.trim() || undefined });
    if (!academicYear.value && page.value.academic_year) {
      adoptingYear = true;
      academicYear.value = page.value.academic_year;
    }
    // the open record stays open while it is still in the list; otherwise the first one opens
    const rows = page.value.rows;
    if (!rows.some((r) => r.name === selected.value)) selected.value = rows[0]?.name ?? null;
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error);
  } finally {
    loading.value = false;
  }
}

/** set while the year chosen by the server is put in the selector, so that does not load again */
let adoptingYear = false;
let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(load, 300);
});
watch([status, academicYear], () => {
  if (adoptingYear) {
    adoptingYear = false;
    return;
  }
  void load();
});
onMounted(load);

const rows = computed(() => (page.value?.rows ?? []) as unknown as Record<string, unknown>[]);
const row = (item: Record<string, unknown>) => item as unknown as Application;
function places(name: string | null): Places | undefined {
  const r = page.value?.rows.find((x) => x.name === name);
  return r ? page.value?.capacity[`${r.offering}|${r.academic_year}`] : undefined;
}
const docsClass = (r: Application) => (r.documents_verified === r.documents_required ? "done" : r.documents_rejected.length ? "bad" : "");
</script>

<template>
  <PageHeader title="Admissions" subtitle="Applications for the campuses you work on.">
    <template #actions>
      <Select v-model="academicYear" :options="page?.academic_years ?? []" placeholder="Year" aria-label="Academic year" class="year" size="small" />
    </template>
    <EcTabs v-model="status" :tabs="statusOptions" label="Status" class="tabs" />
  </PageHeader>

  <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

  <SplitView
    v-model:selected="selected"
    :items="rows"
    item-key="name"
    :loading="loading"
    list-label="Applications"
    :empty-title="`No ${applicationLabel(status).toLowerCase()} applications`"
    placeholder="Select an application"
  >
    <template #filters>
      <IconField class="search">
        <InputIcon><Search :size="15" /></InputIcon>
        <InputText v-model="search" placeholder="Search name or number" aria-label="Search applications" fluid size="small" />
      </IconField>
    </template>

    <template #item="{ item }">
      <div class="item">
        <div class="item-top">
          <span class="who">{{ row(item).applicant }}</span>
          <span class="ec-muted ec-nowrap">{{ row(item).offering }}</span>
        </div>
        <div class="item-bottom">
          <span class="ec-muted">{{ formatDate(row(item).application_date) }}</span>
          <template v-if="status === 'Applied' && row(item).online">
            <span class="chip" :class="docsClass(row(item))">Docs {{ row(item).documents_verified }}/{{ row(item).documents_required }}</span>
            <StatusTag kind="fee" :value="row(item).fee_status" />
          </template>
          <StatusTag v-else-if="status === 'Approved' && row(item).offer_status" kind="offer" :value="row(item).offer_status" />
          <span v-else-if="!row(item).online" class="ec-muted">Paper</span>
        </div>
      </div>
    </template>

    <template #detail="{ selected: name }">
      <ApplicationDetail :key="name" :name="name" :places="places(name)" @changed="load" />
    </template>
  </SplitView>
</template>

<style scoped>
.tabs {
  flex: 1;
}

.year {
  width: 7.5rem;
}

.search {
  flex: 1;
}

.item {
  display: grid;
  gap: 0.3rem;
}

.item-top,
.item-bottom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.item-top {
  justify-content: space-between;
}

.who {
  font-weight: 600;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip {
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  background: #f3f4f6;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 600;
}

.chip.done {
  background: #dcfce7;
  color: var(--ec-success);
}

.chip.bad {
  background: #fee2e2;
  color: var(--ec-danger);
}
</style>
