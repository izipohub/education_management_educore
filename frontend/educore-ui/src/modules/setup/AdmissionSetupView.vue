<script setup lang="ts">
import { Plus, X } from "@lucide/vue";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import SelectButton from "primevue/selectbutton";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SplitView from "@/core/ui/SplitView.vue";
import DocumentEditor from "./DocumentEditor.vue";
import PathwayEditor from "./PathwayEditor.vue";
import ProgrammeEditor from "./ProgrammeEditor.vue";
import RulesForm from "./RulesForm.vue";
import {
  type DocumentType,
  type Pathway,
  type Programme,
  type ScaleRow,
  type Setup,
  getSetup,
  saveDocumentType,
  savePathway,
  savePointsScale,
  saveProgramme,
  saveSettings,
} from "./api";

/** The university's admission rules: settings on the Rules tab; pathways, documents and programmes as a list with
 *  the editor docked beside it; the points scale */
const toast = useToast();
const setup = ref<Setup | null>(null);
const loadError = ref("");
const saving = ref(false);

type Tab = "rules" | "pathways" | "documents" | "programmes" | "points";
const tab = ref<Tab>("rules");
const tabs = computed(() => [
  { label: "Rules", value: "rules" as Tab },
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

// --- the selected item of the list tabs ("new" while adding one) ----------------------------------------------
const NEW = "__new__";
const selected = ref<string | null>(null);
const items = computed(() => {
  const s = setup.value;
  if (!s) return [];
  const list = tab.value === "pathways" ? s.pathways : tab.value === "documents" ? s.documents : tab.value === "programmes" ? s.programmes : [];
  return list as unknown as Record<string, unknown>[];
});
watch(tab, () => (selected.value = (items.value[0]?.name as string) ?? null));

const pathway = computed<Pathway | "new" | null>(() =>
  selected.value === NEW ? "new" : (setup.value?.pathways.find((p) => p.name === selected.value) ?? null),
);
const documentType = computed<DocumentType | "new" | null>(() =>
  selected.value === NEW ? "new" : (setup.value?.documents.find((d) => d.name === selected.value) ?? null),
);
const programme = computed<Programme | null>(() => setup.value?.programmes.find((p) => p.name === selected.value) ?? null);
const first = () => (items.value[0]?.name as string) ?? null;

async function onSavePathway(data: Partial<Pathway> & { pathway_name?: string }, name?: string) {
  if (await run(() => savePathway(data, name), "Pathway saved")) selected.value = name ?? data.pathway_name ?? null;
}
async function onSaveDocument(data: Partial<DocumentType> & { document_name?: string }, name?: string) {
  if (await run(() => saveDocumentType(data, name), "Document saved")) selected.value = name ?? data.document_name ?? null;
}
const onSaveProgramme = (name: string, data: Partial<Programme>) => run(() => saveProgramme(name, data), "Entry requirements saved");

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
  <PageHeader title="Admission setup" subtitle="The university's own admission rules. Changes apply from the next assessment.">
    <EcTabs v-model="tab" :tabs="tabs" label="Section" class="tabs" />
  </PageHeader>

  <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>
  <div v-else-if="!setup" class="scroll">
    <div class="card"><EcSkeleton shape="lines" :rows="6" label="Loading the admission setup" /></div>
  </div>

  <template v-else>
    <div v-if="tab === 'rules'" class="scroll">
      <RulesForm :settings="setup.settings" :countries="setup.choices.countries" :saving="saving" @save="(data) => run(() => saveSettings(data), 'Rules saved')" />
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

    <!-- the list, and the selected item's editor docked beside it -->
    <SplitView v-else v-model:selected="selected" :items="items" item-key="name" :list-label="tab" placeholder="Select an item to edit it">
      <template v-if="tab !== 'programmes'" #filters>
        <EcButton :label="tab === 'pathways' ? 'Add an entry pathway' : 'Add a document'" :icon="Plus" size="sm" :disabled="selected === NEW" @click="selected = NEW" />
      </template>

      <template #item="{ item }">
        <div v-if="tab === 'pathways'" class="item">
          <div class="item-top">
            <span class="who">{{ asPathway(item).name }}</span>
            <span class="dot" :class="{ on: asPathway(item).active }">{{ asPathway(item).active ? "Open" : "Closed" }}</span>
          </div>
          <span class="ec-muted">{{ asPathway(item).level }} · {{ asPathway(item).evidence }}<template v-if="asPathway(item).min_age"> · from age {{ asPathway(item).min_age }}</template></span>
        </div>
        <div v-else-if="tab === 'documents'" class="item">
          <div class="item-top">
            <span class="who">{{ asDocument(item).name }}</span>
            <span v-if="!asDocument(item).active" class="dot">Not in use</span>
          </div>
          <span class="ec-muted">{{ asDocument(item).required_for }}<template v-if="asDocument(item).must_be_certified"> · certified</template></span>
        </div>
        <div v-else class="item">
          <div class="item-top">
            <span class="who">{{ asProgramme(item).name }}</span>
            <span class="ec-muted ec-nowrap">{{ asProgramme(item).code }}</span>
          </div>
          <span class="ec-muted">{{ asProgramme(item).level }} · {{ entry(asProgramme(item)) }}</span>
        </div>
      </template>

      <template #detail>
        <PathwayEditor v-if="tab === 'pathways' && pathway" :key="String(selected)" :pathway="pathway" :setup="setup" :saving="saving" @save="onSavePathway" @cancel="selected = first()" />
        <DocumentEditor v-else-if="tab === 'documents' && documentType" :key="String(selected)" :document="documentType" :setup="setup" :saving="saving" @save="onSaveDocument" @cancel="selected = first()" />
        <ProgrammeEditor v-else-if="tab === 'programmes' && programme" :key="String(selected)" :programme="programme" :setup="setup" :saving="saving" @save="onSaveProgramme" />
      </template>
    </SplitView>
  </template>
</template>

<style scoped>
.tabs {
  flex: 1;
}

/* the pages that are forms scroll inside the window (the screen itself fills it, like the queues) */
.scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
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
