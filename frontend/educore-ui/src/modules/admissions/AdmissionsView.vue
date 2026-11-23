<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { applicationLabel } from "@/core/status";
import { formatDate } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Application, type ApplicationsPage, OCCASIONAL, STATUSES, type Status, listApplications } from "./api";

/** The admissions list: one row per application, a row opens the application's own page */
const route = useRoute();
const router = useRouter();
const initial = STATUSES.includes(route.query.status as Status) ? (route.query.status as Status) : "Applied";
const status = ref<Status>(initial);
const academicYear = ref<string | undefined>((route.query.year as string) || undefined);
const search = ref("");
const page = ref<ApplicationsPage | null>(null);
const loading = ref(false);
const loadError = ref("");

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
  // the tab and year stay in the address, so Back from an application returns to the same list
  void router.replace({ query: { ...route.query, status: status.value, year: academicYear.value } });
  if (adoptingYear) {
    adoptingYear = false;
    return;
  }
  void load();
});
onMounted(load);

const rows = computed(() => (page.value?.rows ?? []) as unknown as Record<string, unknown>[]);
const row = (item: Record<string, unknown>) => item as unknown as Application;

const columns = computed<Column[]>(() => {
  const base: Column[] = [
    { key: "applicant", label: "Applicant" },
    { key: "offering", label: "Programme" },
    { key: "campus", label: "Campus", wide: true },
    { key: "application_date", label: "Applied", wide: true },
  ];
  if (status.value === "Applied")
    return [...base, { key: "documents", label: "Documents", wide: true }, { key: "fee_status", label: "Fee" }];
  if (status.value === "Approved") return [...base, { key: "offer_status", label: "Offer" }, { key: "offer_deadline", label: "Respond by", wide: true }];
  return [...base, { key: "decided_on", label: "Decided", wide: true }];
});
</script>

<template>
  <section class="list-page">
    <PageHeader title="Admissions" subtitle="Applications for the campuses you work on">
      <template #actions>
        <Select v-model="academicYear" :options="page?.academic_years ?? []" placeholder="Year" aria-label="Academic year" class="year" size="small" />
      </template>
      <EcTabs v-model="status" :tabs="statusOptions" label="Status" class="tabs" />
    </PageHeader>

    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <DataTable
      :columns="columns"
      :rows="rows"
      row-key="name"
      :to="(r) => ({ name: 'application-record', params: { name: String(r.name) }, query: route.query })"
      :loading="loading"
      noun="applications"
      :empty-title="`No ${applicationLabel(status).toLowerCase()} applications`"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Search name or number" aria-label="Search applications" fluid size="small" />
        </IconField>
      </template>

      <template #cell-applicant="{ row: r }">
        <span class="who">{{ row(r).applicant }}</span>
        <span class="sub">{{ row(r).name }}</span>
      </template>
      <template #cell-offering="{ row: r }">
        <span class="programme">{{ row(r).program }}</span>
        <span class="sub">{{ row(r).offering }}</span>
      </template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-application_date="{ row: r }"><span class="ec-nowrap">{{ formatDate(row(r).application_date) }}</span></template>
      <template #cell-documents="{ row: r }">
        <span v-if="row(r).online" class="ec-nowrap">{{ row(r).documents_verified }} of {{ row(r).documents_required }} verified</span>
        <span v-else class="ec-muted">Paper</span>
      </template>
      <template #cell-fee_status="{ row: r }">
        <StatusTag v-if="row(r).online" kind="fee" :value="row(r).fee_status" />
        <span v-else />
      </template>
      <template #cell-offer_status="{ row: r }">
        <StatusTag v-if="row(r).offer_status" kind="offer" :value="row(r).offer_status" />
        <span v-else class="ec-muted">Paper</span>
      </template>
      <template #cell-offer_deadline="{ row: r }"><span class="ec-nowrap">{{ formatDate(row(r).offer_deadline) }}</span></template>
      <template #cell-decided_on="{ row: r }"><span class="ec-nowrap">{{ formatDate(row(r).decided_on) }}</span></template>
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
  white-space: nowrap;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 400;
}

/* a phone shows the offering code only */
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
