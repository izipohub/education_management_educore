<script setup lang="ts">
import { Plus, X } from "@lucide/vue";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import SelectButton from "primevue/selectbutton";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import EcButton from "@/core/ui/EcButton.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import RulesForm from "./RulesForm.vue";
import {
  type DocumentType,
  type Pathway,
  type Programme,
  type ScaleRow,
  type Setup,
  getSetup,
  savePointsScale,
  saveSettings,
} from "./api";

/** The university's admission rules: the settings; pathways, documents and programmes as lists, each item on its
 *  own page; the points scale */
const toast = useToast();
const setup = ref<Setup | null>(null);
const loadError = ref("");
const saving = ref(false);

type Tab = "rules" | "pathways" | "documents" | "programmes" | "points";
const route = useRoute();
const router = useRouter();
const TABS: Tab[] = ["rules", "pathways", "documents", "programmes", "points"];
const tab = ref<Tab>(TABS.includes(route.query.tab as Tab) ? (route.query.tab as Tab) : "rules");
// the tab stays in the address, so Back from an item returns to its list
watch(tab, (t) => void router.replace({ query: t === "rules" ? {} : { tab: t } }));
const tabs = computed(() => [
  { label: "Settings", value: "rules" as Tab },
  { label: "Entry pathways", value: "pathways" as Tab, count: setup.value?.pathways.length },
  { label: "Documents", value: "documents" as Tab, count: setup.value?.documents.length },
  { label: "Programmes", value: "programmes" as Tab, count: setup.value?.programmes.length },
  { label: "Admission point scale", value: "points" as Tab },
]);

onMounted(async () => {
  try {
    setup.value = await getSetup();
    resetScale();
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  }
});

/** every save returns the whole setup: the screen always shows what is stored */
async function run(call: () => Promise<Setup>, message: string): Promise<boolean> {
  saving.value = true;
  try {
    setup.value = await call();
    toast.add({ severity: "success", summary: message, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    saving.value = false;
  }
}

// --- the list tabs: a row opens the item's own page ----------------------------------------------------------
const rows = computed(() => {
  const st = setup.value;
  if (!st) return [];
  const list = tab.value === "pathways" ? st.pathways : tab.value === "documents" ? st.documents : tab.value === "programmes" ? st.programmes : [];
  return list as unknown as Record<string, unknown>[];
});
const itemLink = (r: Record<string, unknown>) => ({ name: "setup-item", params: { section: tab.value, name: String(r.name) } });
const COLUMNS: Record<"pathways" | "documents" | "programmes", Column[]> = {
  pathways: [
    { key: "name", label: "Entry pathway" },
    { key: "level", label: "Level", wide: true },
    { key: "evidence", label: "Judged on", wide: true },
    { key: "applications", label: "Applications", align: "right", wide: true },
    { key: "active", label: "Status" },
  ],
  documents: [
    { key: "name", label: "Document" },
    { key: "required_for", label: "Asked of", wide: true },
    { key: "must_be_certified", label: "Certified copy", wide: true },
    { key: "active", label: "Status" },
  ],
  programmes: [
    { key: "name", label: "Programme" },
    { key: "code", label: "Code", wide: true },
    { key: "level", label: "Level", wide: true },
    { key: "entry", label: "Entry requirement" },
  ],
};
const listTab = computed(() => (tab.value === "pathways" || tab.value === "documents" || tab.value === "programmes" ? tab.value : null));

const asPathway = (i: Record<string, unknown>) => i as unknown as Pathway;
const asDocument = (i: Record<string, unknown>) => i as unknown as DocumentType;
const asProgramme = (i: Record<string, unknown>) => i as unknown as Programme;
function entry(p: Programme) {
  if (p.level === "Postgraduate") {
    return [p.min_prior_nqf ? `NQF ${p.min_prior_nqf}` : "", p.min_prior_average ? `${p.min_prior_average}%` : ""].filter(Boolean).join(", ") || "No minimum set";
  }
  return [p.min_points ? `${p.min_points} points` : "", p.subject_requirements.length ? `${p.subject_requirements.length} subjects` : ""].filter(Boolean).join(" · ") || "No minimum set";
}

// --- points scale --------------------------------------------------------------------------------------------
const scale = ref<ScaleRow[]>([]);
const scaleLevel = ref("NSSCO");
function resetScale() {
  scale.value = (setup.value?.points_scale ?? []).map((r) => ({ ...r }));
}
const levelRows = computed(() => scale.value.filter((r) => r.level === scaleLevel.value));
const addGrade = () => scale.value.push({ level: scaleLevel.value, grade: "", points: 0 });
const removeGrade = (row: ScaleRow) => scale.value.splice(scale.value.indexOf(row), 1);
async function onSaveScale() {
  if (await run(() => savePointsScale(scale.value.filter((r) => r.grade.trim())), "Admission point scale saved")) resetScale();
}
</script>

<template>
  <section class="setup">
  <PageHeader title="Admission setup" subtitle="The university's own admission rules">
    <EcTabs v-model="tab" :tabs="tabs" label="Section" class="tabs" />
  </PageHeader>

  <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>
  <div v-else-if="!setup" class="scroll">
    <div class="card"><EcSkeleton shape="lines" :rows="6" label="Loading the admission setup" /></div>
  </div>

  <template v-else>
    <div v-if="tab === 'rules'" class="scroll">
      <RulesForm
        :settings="setup.settings"
        :countries="setup.choices.countries"
        :bank-accounts="setup.choices.bank_accounts"
        :income-accounts="setup.choices.income_accounts"
        :saving="saving"
        @save="(data) => run(() => saveSettings(data), 'Settings saved')"
      />
    </div>

    <div v-else-if="tab === 'points'" class="scroll">
      <section class="card scale">
        <SelectButton v-model="scaleLevel" :options="setup.choices.school_levels" :allow-empty="false" aria-label="School level" size="small" />
        <div class="scale-rows">
          <div v-for="(row, index) in levelRows" :key="index" class="scale-row">
            <InputText v-model="row.grade" placeholder="Grade" :aria-label="`Grade ${index + 1}`" class="grade" size="small" />
            <InputNumber v-model="row.points" :min="0" :aria-label="`Points for grade ${index + 1}`" class="points" size="small" />
            <span class="ec-muted">points</span>
            <EcButton :icon="X" size="sm" variant="ghost" :aria-label="`Remove grade ${index + 1}`" @click="removeGrade(row)" />
          </div>
        </div>
        <EcButton label="Add a grade" :icon="Plus" size="sm" variant="ghost" class="start" @click="addGrade" />
        <div class="footer">
          <EcButton label="Undo changes" variant="ghost" :disabled="saving" @click="resetScale" />
          <EcButton label="Save scale" variant="primary" :loading="saving" @click="onSaveScale" />
        </div>
      </section>
    </div>

    <DataTable
      v-else-if="listTab"
      :columns="COLUMNS[listTab]"
      :rows="rows"
      row-key="name"
      :to="itemLink"
      :noun="listTab === 'pathways' ? 'entry pathways' : listTab"
      empty-title="Nothing set up yet"
    >
      <template v-if="listTab !== 'programmes'" #toolbar>
        <EcButton
          :label="listTab === 'pathways' ? 'Add an entry pathway' : 'Add a document'"
          :icon="Plus"
          size="sm"
          @click="router.push({ name: 'setup-item', params: { section: listTab, name: 'new' } })"
        />
      </template>
      <template #cell-name="{ row: r }">{{ r.name }}</template>
      <template #cell-evidence="{ row: r }">{{ asPathway(r).evidence }}<template v-if="asPathway(r).min_age"> · from age {{ asPathway(r).min_age }}</template></template>
      <template #cell-applications="{ row: r }">{{ asPathway(r).applications || "" }}</template>
      <template #cell-active="{ row: r }">
        <span class="dot" :class="{ on: r.active }">{{ r.active ? (listTab === "pathways" ? "Open" : "In use") : listTab === "pathways" ? "Closed" : "Not in use" }}</span>
      </template>
      <template #cell-must_be_certified="{ row: r }">{{ asDocument(r).must_be_certified ? "Required" : "" }}</template>
      <template #cell-entry="{ row: r }">{{ entry(asProgramme(r)) }}</template>
    </DataTable>
  </template>
  </section>
</template>

<style scoped>
.setup {
  display: grid;
  gap: 1rem;
}

.tabs {
  flex: 1;
}

.scroll {
  min-width: 0;
}

.item {
  display: grid;
  gap: 0.3rem;
}

.item-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.who {
  font-weight: 600;
  font-size: 0.9rem;
}

.dot {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.75rem;
  color: var(--ec-muted);
}

.dot::before {
  content: "";
  width: 0.45rem;
  height: 0.45rem;
  border-radius: 50%;
  background: var(--ec-subtle);
}

.dot.on::before {
  background: var(--ec-success);
}

.scale {
  display: grid;
  gap: 0.75rem;
  max-width: 32rem;
}

.scale-rows {
  display: grid;
  gap: 0.4rem;
}

.scale-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.grade {
  width: 6rem;
}

.points :deep(input) {
  width: 5rem;
}

.start {
  justify-self: start;
}

.footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
