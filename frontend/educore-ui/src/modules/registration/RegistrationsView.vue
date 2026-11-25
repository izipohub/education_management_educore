<script setup lang="ts">
import Message from "primevue/message";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatDate } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Queue, type QueueRow, getQueue } from "./api";
import type { Group } from "./groups";
import CourseChangesQueue from "./CourseChangesQueue.vue";
import { changeQueue } from "./courseChanges";

/** Registration, senior students: their course registrations to approve; a row opens the registration's page */
defineProps<{ groups: { value: Group; label: string }[] }>();
const group = defineModel<Group>("group", { required: true });
type State = "Submitted" | "Returned" | "Approved" | "changes";
const STATES: State[] = ["Submitted", "Returned", "Approved", "changes"];
const route = useRoute();
const router = useRouter();
const status = ref<State>(STATES.includes(route.query.status as State) ? (route.query.status as State) : "Submitted");
const page = ref<Queue | null>(null);
const loading = ref(false);
const loadError = ref("");

const changesToDecide = ref(0);
async function load() {
  if (status.value === "changes") return;
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await getQueue(status.value);
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(() => {
  void load();
  void changeQueue("Submitted").then((q) => (changesToDecide.value = q.counts.Submitted)).catch(() => undefined);
});
watch(status, () => {
  void router.replace({ query: { ...route.query, status: status.value } });
  void load();
});

const tabs = computed(() =>
  STATES.map((s) =>
    s === "changes" ? { label: "Course changes", count: changesToDecide.value, value: s } : { label: s, count: page.value?.counts[s] ?? 0, value: s },
  ),
);
const rows = computed(() => (page.value?.rows ?? []) as unknown as Record<string, unknown>[]);
const asRow = (item: Record<string, unknown>) => item as unknown as QueueRow;
const columns: Column[] = [
  { key: "student_name", label: "Student" },
  { key: "offering", label: "Programme" },
  { key: "year_of_study", label: "Year", align: "right", wide: true },
  { key: "credits", label: "Credits", align: "right", wide: true },
  { key: "submitted_on", label: "Submitted", wide: true },
  { key: "standing", label: "Standing" },
];
</script>

<template>
  <section class="list-page">
    <PageHeader
      title="Registration"
      :subtitle="`Senior students: course registrations in your faculty and campus${page?.academic_year ? ` · ${page.academic_year}` : ''}`"
    >
      <template #actions>
        <EcSegmented v-if="groups.length" v-model="group" :options="groups" label="Students" />
      </template>
      <EcTabs v-model="status" :tabs="tabs" label="Status" class="tabs" />
    </PageHeader>

    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <CourseChangesQueue v-if="status === 'changes'" @counts="(c) => (changesToDecide = c.Submitted)" />

    <DataTable
      v-else
      :columns="columns"
      :rows="rows"
      row-key="name"
      :to="(r) => ({ name: 'registration-record', params: { name: String(r.name) }, query: { ...route.query, group: 'senior' } })"
      :loading="loading"
      noun="registrations"
      :empty-title="`No ${status.toLowerCase()} registrations`"
    >
      <template #cell-student_name="{ row: r }">
        <span class="who">{{ asRow(r).student_name }}</span>
        <span class="sub">{{ asRow(r).student }}</span>
      </template>
      <template #cell-offering="{ row: r }">
        <span class="programme">{{ asRow(r).program }}</span>
        <span class="sub">{{ asRow(r).offering }}</span>
      </template>
      <template #cell-submitted_on="{ row: r }">
        <span class="ec-nowrap">{{ formatDate(asRow(r).submitted_on) }}</span>
        <span v-if="asRow(r).late" class="sub">Late</span>
      </template>
      <template #cell-standing="{ row: r }"><StatusTag kind="standing" :value="asRow(r).standing" /></template>
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
