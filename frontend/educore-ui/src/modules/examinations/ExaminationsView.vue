<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SettingRow from "@/core/ui/SettingRow.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Rules, type SheetRow, type SheetStatus, type SheetsPage, getRules, listSheets, publish, saveRules } from "./api";

/**
 * Examinations: every class of the year with where its marks stand (with the lecturer, to moderate, to approve,
 * approved, published); a row opens the class's marks. The examinations officer publishes approved results; the
 * Registrar sets the rules.
 */
type Tab = "all" | "Draft" | "Submitted" | "Moderated" | "Approved" | "Published" | "rules";
const route = useRoute();
const router = useRouter();
const toast = useToast();
const tab = ref<Tab>((route.query.tab as Tab) || "all");
const year = ref<string | undefined>((route.query.year as string) || undefined);
const search = ref("");
const page = ref<SheetsPage | null>(null);
const loading = ref(false);
const error = ref("");

let adopting = false;
async function load() {
  loading.value = true;
  error.value = "";
  try {
    page.value = await listSheets(year.value);
    if (!year.value && page.value.academic_year) {
      adopting = true;
      year.value = page.value.academic_year;
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
watch([tab, year], () => void router.replace({ query: { ...(tab.value !== "all" ? { tab: tab.value } : {}), ...(year.value ? { year: year.value } : {}) } }));

const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (page.value?.rows ?? []).filter((r) => !q || `${r.code} ${r.course} ${r.lecturers.join(" ")}`.toLowerCase().includes(q));
});
const count = (s: SheetStatus | "Draft") => matching.value.filter((r) => (s === "Draft" ? r.status === "Draft" || r.status === "Not started" : r.status === s)).length;
const tabs = computed(() => [
  { label: "All", value: "all" as Tab, count: matching.value.length },
  { label: "With lecturer", value: "Draft" as Tab, count: count("Draft") },
  { label: "To moderate", value: "Submitted" as Tab, count: count("Submitted") },
  { label: "To approve", value: "Moderated" as Tab, count: count("Moderated") },
  { label: "Approved", value: "Approved" as Tab, count: count("Approved") },
  { label: "Published", value: "Published" as Tab, count: count("Published") },
  { label: "Rules", value: "rules" as Tab },
]);
const rows = computed(
  () =>
    matching.value.filter((r) =>
      tab.value === "all" ? true : tab.value === "Draft" ? r.status === "Draft" || r.status === "Not started" : r.status === tab.value,
    ) as unknown as Record<string, unknown>[],
);
const row = (r: Record<string, unknown>) => r as unknown as SheetRow;
const columns: Column[] = [
  { key: "course", label: "Course" },
  { key: "campus", label: "Campus", wide: true },
  { key: "lecturers", label: "Lecturers", wide: true },
  { key: "students", label: "Students", align: "right", wide: true },
  { key: "pass_rate", label: "Pass rate", align: "right" },
  { key: "status", label: "Status" },
];

// publishing every approved class at once
const approved = computed(() => (page.value?.rows ?? []).filter((r) => r.status === "Approved").map((r) => r.group));
const publishing = ref(false);
async function publishAll() {
  publishing.value = true;
  try {
    const { published } = await publish(approved.value);
    toast.add({ severity: "success", summary: `${published} classes' results published`, life: 3000 });
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not published", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    publishing.value = false;
  }
}

// the rules (Registrar)
const rules = ref<(Rules & { grading_scales: string[]; can_edit: boolean }) | null>(null);
const form = reactive({ ca_weight: 50, exam_admission_ca: 40, pass_mark: 50, supplementary_from: 45, probation_share: 50, grading_scale: "" as string | null });
watch(
  tab,
  async (t) => {
    if (t !== "rules" || rules.value) return;
    rules.value = await getRules();
    Object.assign(form, rules.value);
  },
  { immediate: true },
);
const rulesChanged = computed(() => Boolean(rules.value) && (Object.keys(form) as (keyof typeof form)[]).some((k) => form[k] !== rules.value![k]));
const savingRules = ref(false);
async function saveTheRules() {
  savingRules.value = true;
  try {
    rules.value = await saveRules({ ...form });
    Object.assign(form, rules.value);
    toast.add({ severity: "success", summary: "Rules saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    savingRules.value = false;
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Examinations" subtitle="Marks from the lecturers, moderated by the department, approved by the examination board">
      <template #actions>
        <EcButton v-if="page?.can_publish && approved.length" :label="`Publish ${approved.length} approved`" variant="primary" :loading="publishing" @click="publishAll" />
        <Select v-model="year" :options="page?.academic_years ?? []" placeholder="Year" aria-label="Academic year" size="small" class="year" />
      </template>
      <EcTabs v-model="tab" :tabs="tabs" label="Status" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div v-if="tab === 'rules'" class="rules">
      <template v-if="rules">
        <EcPanel title="Final mark" :note="rules.can_edit ? undefined : 'Set by the Registrar'">
          <SettingRow label="Continuous assessment weight" help="The rest is the examination" for="caw">
            <InputNumber v-model="form.ca_weight" input-id="caw" :min="0" :max="100" suffix=" %" show-buttons :disabled="!rules.can_edit" fluid />
          </SettingRow>
          <SettingRow label="Continuous assessment for examination admission" for="adm">
            <InputNumber v-model="form.exam_admission_ca" input-id="adm" :min="0" :max="100" suffix=" %" show-buttons :disabled="!rules.can_edit" fluid />
          </SettingRow>
          <SettingRow label="Pass mark" for="pass">
            <InputNumber v-model="form.pass_mark" input-id="pass" :min="0" :max="100" suffix=" %" show-buttons :disabled="!rules.can_edit" fluid />
          </SettingRow>
          <SettingRow label="Supplementary examination from" help="Up to the pass mark" for="supp">
            <InputNumber v-model="form.supplementary_from" input-id="supp" :min="0" :max="100" suffix=" %" show-buttons :disabled="!rules.can_edit" fluid />
          </SettingRow>
        </EcPanel>
        <EcPanel title="Grades and standing">
          <SettingRow label="Grading scale" for="scale">
            <Select v-model="form.grading_scale" input-id="scale" :options="rules.grading_scales" :disabled="!rules.can_edit" fluid />
          </SettingRow>
          <dl class="bands">
            <div v-for="b in rules.bands" :key="b.grade"><dt>{{ b.grade }}</dt><dd>from {{ b.from }}</dd></div>
          </dl>
          <SettingRow label="Credits failed for probation" help="Share of the year's credits" for="prob">
            <InputNumber v-model="form.probation_share" input-id="prob" :min="0" :max="100" suffix=" %" show-buttons :disabled="!rules.can_edit" fluid />
          </SettingRow>
        </EcPanel>
        <div v-if="rules.can_edit && rulesChanged" class="save-bar">
          <span class="ec-muted">Unsaved changes</span>
          <EcButton label="Undo" variant="ghost" @click="Object.assign(form, rules)" />
          <EcButton label="Save" variant="primary" :loading="savingRules" @click="saveTheRules" />
        </div>
      </template>
    </div>

    <DataTable
      v-else
      :columns="columns"
      :rows="rows"
      row-key="group"
      :to="(r) => ({ name: 'mark-sheet', params: { group: String(r.group) }, query: route.query })"
      :loading="loading"
      noun="classes"
      empty-title="No classes here"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Course, code or lecturer" aria-label="Search" fluid size="small" />
        </IconField>
      </template>
      <template #cell-course="{ row: r }">
        <span class="who">{{ row(r).course }}</span>
        <span class="sub">{{ row(r).code }}</span>
      </template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-lecturers="{ row: r }">{{ row(r).lecturers.join(", ") }}</template>
      <template #cell-pass_rate="{ row: r }">{{ row(r).pass_rate !== null ? `${row(r).pass_rate}%` : "" }}</template>
      <template #cell-status="{ row: r }"><StatusTag kind="marks" :value="row(r).status" /></template>
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
}

.rules {
  display: grid;
  gap: 1rem;
  max-width: 52rem;
}

.bands {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin: 0.25rem 0 0.9rem;
  padding: 0.75rem 0.9rem;
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface-muted);
  font-size: 0.85rem;
}

.bands div {
  display: flex;
  gap: 0.35rem;
}

.bands dt {
  font-weight: 700;
}

.bands dd {
  margin: 0;
  color: var(--ec-muted);
}

.save-bar {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--ec-surface);
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius);
  box-shadow: 0 -2px 8px rgb(0 0 0 / 0.05);
}

.save-bar .ec-muted {
  margin-right: auto;
}
</style>
