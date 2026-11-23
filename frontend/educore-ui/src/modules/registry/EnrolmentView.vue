<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatDate, formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import type { Group } from "@/modules/registration/groups";
import { type Enrolled, type EnrolmentsPage, type Offer, listEnrolments } from "./api";

/** Registration, first-year students: admitted applicants to register, and those registered; a row opens its page */
defineProps<{ groups: { value: Group; label: string }[] }>();
const group = defineModel<Group>("group", { required: true });
type View = "waiting" | "enrolled";
const route = useRoute();
const router = useRouter();
const view = ref<View>(route.query.view === "enrolled" ? "enrolled" : "waiting");
const academicYear = ref<string | undefined>((route.query.year as string) || undefined);
const search = ref("");
const page = ref<EnrolmentsPage | null>(null);
const loading = ref(false);
const loadError = ref("");

const viewOptions = computed(() => [
  { label: "To register", count: page.value?.waiting.length ?? 0, value: "waiting" as View },
  { label: "Registered", count: page.value?.enrolled.length ?? 0, value: "enrolled" as View },
]);
const rows = computed(() => ((view.value === "waiting" ? page.value?.waiting : page.value?.enrolled) ?? []) as unknown as Record<string, unknown>[]);
const asOffer = (item: Record<string, unknown>) => item as unknown as Offer;
const asEnrolled = (item: Record<string, unknown>) => item as unknown as Enrolled;

let adoptingYear = false;
async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await listEnrolments({ academic_year: academicYear.value, search: search.value.trim() || undefined });
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

let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(load, 300);
});
watch([view, academicYear], ([, year], [, before]) => {
  // the server's own choice of year is not written to the address: that would cancel a click made meanwhile
  if (adoptingYear) {
    adoptingYear = false;
    return;
  }
  void router.replace({ query: { ...route.query, view: view.value, year: academicYear.value } });
  if (year !== before) void load();
});
onMounted(load);

const columns = computed<Column[]>(() =>
  view.value === "waiting"
    ? [
        { key: "applicant", label: "Applicant" },
        { key: "offering", label: "Programme" },
        { key: "campus", label: "Campus", wide: true },
        { key: "decided_on", label: "Offered", wide: true },
        { key: "fees", label: "Year's fees", align: "right", wide: true },
        { key: "offer_status", label: "Offer" },
      ]
    : [
        { key: "applicant", label: "Student" },
        { key: "offering", label: "Programme" },
        { key: "campus", label: "Campus", wide: true },
        { key: "enrollment_date", label: "Registered", wide: true },
        { key: "invoice", label: "Invoice" },
        { key: "outstanding", label: "Owing", align: "right", wide: true },
      ],
);
</script>

<template>
  <section class="list-page">
    <PageHeader title="Registration" subtitle="First-year students: admitted applicants on your campuses">
      <template #actions>
        <EcSegmented v-if="groups.length" v-model="group" :options="groups" label="Students" />
        <Select v-model="academicYear" :options="page?.academic_years ?? []" placeholder="Year" aria-label="Academic year" class="year" size="small" />
      </template>
      <EcTabs v-model="view" :tabs="viewOptions" label="View" class="tabs" />
    </PageHeader>

    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <DataTable
      :columns="columns"
      :rows="rows"
      row-key="name"
      :to="(r) => ({ name: 'enrolment-record', params: { name: String(r.name) }, query: { ...route.query, group: 'first-year' } })"
      :loading="loading"
      :noun="view === 'waiting' ? 'applicants' : 'students'"
      :empty-title="view === 'waiting' ? 'Nobody waiting to register' : 'Nobody registered yet'"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Search name or number" aria-label="Search" fluid size="small" />
        </IconField>
      </template>

      <template #cell-applicant="{ row: r }">
        <span class="who">{{ asOffer(r).applicant }}</span>
        <span class="sub">{{ view === "waiting" ? asOffer(r).name : (asEnrolled(r).student ?? asEnrolled(r).name) }}</span>
      </template>
      <template #cell-offering="{ row: r }">
        <span class="programme">{{ asOffer(r).program }}</span>
        <span class="sub">{{ asOffer(r).offering }}</span>
      </template>
      <template #cell-campus="{ row: r }">{{ asOffer(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-decided_on="{ row: r }"><span class="ec-nowrap">{{ formatDate(asOffer(r).decided_on) }}</span></template>
      <template #cell-fees="{ row: r }"><span class="ec-nowrap">{{ asOffer(r).fees !== null ? formatMoney(asOffer(r).fees) : "Not set" }}</span></template>
      <template #cell-offer_status="{ row: r }">
        <StatusTag v-if="asOffer(r).online" kind="offer" :value="asOffer(r).offer_status" />
        <span v-else class="ec-muted">Paper</span>
      </template>
      <template #cell-enrollment_date="{ row: r }"><span class="ec-nowrap">{{ formatDate(asEnrolled(r).enrollment_date) }}</span></template>
      <template #cell-invoice="{ row: r }">
        <span v-if="asEnrolled(r).invoice">{{ asEnrolled(r).invoice!.status }}</span>
        <span v-else class="ec-muted">Not invoiced</span>
      </template>
      <template #cell-outstanding="{ row: r }">
        <span class="ec-nowrap">{{ asEnrolled(r).invoice ? formatMoney(asEnrolled(r).invoice!.outstanding_amount) : "" }}</span>
      </template>
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
