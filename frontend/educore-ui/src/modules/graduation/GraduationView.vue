<script setup lang="ts">
import { Search } from "@lucide/vue";
import Checkbox from "primevue/checkbox";
import DatePicker from "primevue/datepicker";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatDate, toIsoDate } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Candidate, type Candidates, type Completion, confirmCompletion, listCandidates } from "./api";

/**
 * Graduation: every student's progress towards completing their programme (required courses and credits, from
 * published results). The examinations office and faculty prepare the list for the Senate; the Registrar records
 * the completions the Senate approved, after which the student's academic record is final.
 */
type Tab = "all" | Completion;
const route = useRoute();
const router = useRouter();
const toast = useToast();
const tab = ref<Tab>((route.query.tab as Tab) || "all");
const programme = ref<string | null>((route.query.programme as string) || null);
const campus = ref<string | null>((route.query.campus as string) || null);
const search = ref("");
const page = ref<Candidates | null>(null);
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    page.value = await listCandidates({ program: programme.value ?? undefined, campus: campus.value ?? undefined });
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch([programme, campus], () => void load());
watch([tab, programme, campus], () =>
  void router.replace({
    query: {
      ...(tab.value !== "all" ? { tab: tab.value } : {}),
      ...(programme.value ? { programme: programme.value } : {}),
      ...(campus.value ? { campus: campus.value } : {}),
    },
  }),
);

const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (page.value?.rows ?? []).filter((r) => !q || `${r.student_name} ${r.name} ${r.program ?? ""}`.toLowerCase().includes(q));
});
const count = (s: Completion) => matching.value.filter((r) => r.status === s).length;
const tabs = computed(() => [
  { label: "All", value: "all" as Tab, count: matching.value.length },
  { label: "Eligible", value: "Eligible" as Tab, count: count("Eligible") },
  { label: "Not yet", value: "Not yet" as Tab, count: count("Not yet") },
  { label: "Completed", value: "Completed" as Tab, count: count("Completed") },
]);
const rows = computed(() => matching.value.filter((r) => tab.value === "all" || r.status === tab.value) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as Candidate;
const columns: Column[] = [
  { key: "student", label: "Student" },
  { key: "program", label: "Programme", wide: true },
  { key: "campus", label: "Campus", wide: true },
  { key: "credits", label: "Credits", align: "right" },
  { key: "outstanding", label: "Still to pass", wide: true },
  { key: "status", label: "Status" },
];
const share = (r: Candidate) => (r.credits_needed ? Math.min(100, Math.round((100 * r.credits_passed) / r.credits_needed)) : 100);

// recording the completions the Senate approved (Registrar)
const ready = computed(() => (page.value?.rows ?? []).filter((r) => r.status === "Eligible" && !r.held));
const confirming = ref(false);
const chosen = ref<string[]>([]);
const reference = ref("");
const completedOn = ref<Date>(new Date());
const saving = ref(false);
function openConfirm() {
  chosen.value = ready.value.map((r) => r.name);
  reference.value = "";
  completedOn.value = new Date();
  confirming.value = true;
}
async function confirm() {
  saving.value = true;
  try {
    const { confirmed } = await confirmCompletion(chosen.value, reference.value.trim(), toIsoDate(completedOn.value));
    toast.add({ severity: "success", summary: `${confirmed} ${confirmed === 1 ? "completion" : "completions"} recorded`, life: 3000 });
    confirming.value = false;
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not recorded", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Graduation" subtitle="Progress towards each programme's requirements, from published results">
      <template #actions>
        <EcButton v-if="page?.can_confirm && ready.length" :label="`Record ${ready.length} completions`" variant="primary" @click="openConfirm" />
      </template>
      <EcTabs v-model="tab" :tabs="tabs" label="Status" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="rows"
      row-key="name"
      :to="(r) => ({ name: 'student-record', params: { name: String(r.name) } })"
      :loading="loading"
      noun="students"
      empty-title="No students here"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name, student number or programme" aria-label="Search" fluid size="small" />
        </IconField>
        <Select v-model="programme" :options="page?.programmes ?? []" placeholder="Programme" aria-label="Programme" show-clear size="small" class="filter" />
        <Select v-if="(page?.campuses.length ?? 0) > 1" v-model="campus" :options="page?.campuses ?? []" placeholder="Campus" aria-label="Campus" show-clear size="small" class="filter" />
      </template>
      <template #cell-student="{ row: r }">
        <span class="who">{{ row(r).student_name }}</span>
        <span class="sub">{{ row(r).name }}</span>
      </template>
      <template #cell-program="{ row: r }">{{ row(r).program }}</template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-credits="{ row: r }">
        <span class="who">{{ row(r).credits_passed }} of {{ row(r).credits_needed }}</span>
        <span class="bar" aria-hidden="true"><span :style="{ width: `${share(row(r))}%` }" /></span>
      </template>
      <template #cell-outstanding="{ row: r }">
        <template v-if="row(r).status === 'Completed'">{{ formatDate(row(r).completed_on) }} · {{ row(r).reference }}</template>
        <template v-else-if="row(r).outstanding.length">{{ row(r).outstanding.join(", ") }}</template>
        <span v-else-if="row(r).status === 'Not yet'" class="ec-muted">{{ row(r).credits_needed - row(r).credits_passed }} more credits</span>
      </template>
      <template #cell-status="{ row: r }">
        <StatusTag kind="completion" :value="row(r).status" />
        <span v-if="row(r).held && row(r).status !== 'Completed'" class="sub">{{ row(r).held }}</span>
      </template>
    </DataTable>
  </section>

  <EcModal :open="confirming" title="Record completions" description="As approved by the Senate; each student's academic record then reads final" size="md" @update:open="(v: boolean) => (confirming = v)">
    <ul class="chosen">
      <li v-for="r in ready" :key="r.name">
        <Checkbox v-model="chosen" :value="r.name" :input-id="`c-${r.name}`" />
        <label :for="`c-${r.name}`">{{ r.student_name }} <span class="ec-muted">· {{ r.program }}</span></label>
      </li>
    </ul>
    <EcField label="Senate meeting" for="senate" hint="E.g. Senate, 05-12-2026">
      <InputText id="senate" v-model="reference" fluid />
    </EcField>
    <EcField label="Date of completion" for="completed-on">
      <DatePicker v-model="completedOn" input-id="completed-on" date-format="dd-mm-yy" show-icon fluid :max-date="new Date()" />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="confirming = false" />
      <EcButton :label="`Record ${chosen.length}`" variant="primary" :loading="saving" :disabled="!chosen.length || !reference.trim()" @click="confirm" />
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
  max-width: 22rem;
}

.filter {
  width: 13rem;
}

.who {
  display: block;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  white-space: nowrap;
  color: var(--ec-muted);
  font-size: 0.75rem;
}

.bar {
  display: block;
  width: 5rem;
  height: 4px;
  margin: 0.3rem 0 0 auto;
  border-radius: 2px;
  background: var(--ec-surface-muted);
  overflow: hidden;
}

.bar span {
  display: block;
  height: 100%;
  background: var(--ec-accent);
}

.chosen {
  display: grid;
  gap: 0.5rem;
  max-height: 16rem;
  margin: 0 0 1rem;
  padding: 0;
  overflow-y: auto;
  list-style: none;
}

.chosen li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
