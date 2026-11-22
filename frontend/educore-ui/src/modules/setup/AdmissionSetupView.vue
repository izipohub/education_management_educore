<script setup lang="ts">
import PageHeader from "@/core/ui/PageHeader.vue";
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import PathwayDrawer from "./PathwayDrawer.vue";
import ProgrammeDrawer from "./ProgrammeDrawer.vue";
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

const toast = useToast();
const setup = ref<Setup | null>(null);
const loadError = ref("");
const saving = ref(false);

type Tab = "rules" | "pathways" | "documents" | "programmes" | "points";
const tab = ref<Tab>("rules");
const TABS = [
  { label: "Rules", value: "rules" },
  { label: "Pathways", value: "pathways" },
  { label: "Documents", value: "documents" },
  { label: "Programmes", value: "programmes" },
  { label: "Points scale", value: "points" },
];

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

// --- pathways ------------------------------------------------------------------------------------------
const editingPathway = ref<Pathway | "new" | null>(null);
async function onSavePathway(data: Partial<Pathway> & { pathway_name?: string }, name?: string) {
  if (await run(() => savePathway(data, name), "Pathway saved")) editingPathway.value = null;
}
const pathwayDocs = (p: Pathway) => p.documents.filter((d) => d.required).length;

// --- documents -----------------------------------------------------------------------------------------
const editingDocument = ref<(Partial<DocumentType> & { document_name?: string; isNew?: boolean }) | null>(null);
function editDocument(doc: DocumentType | null) {
  editingDocument.value = doc
    ? { ...doc }
    : { isNew: true, document_name: "", required_for: "Pathway only", must_be_certified: 1, description: "", active: 1 };
}
async function onSaveDocument() {
  const d = editingDocument.value;
  if (!d) return;
  const { isNew, name, ...data } = d;
  if (await run(() => saveDocumentType(data, isNew ? undefined : name), "Document saved")) editingDocument.value = null;
}
const docFlag = (key: "must_be_certified" | "active") =>
  computed({
    get: () => Boolean(editingDocument.value?.[key]),
    set: (on: boolean) => editingDocument.value && (editingDocument.value[key] = on ? 1 : 0),
  });
const certified = docFlag("must_be_certified");
const docActive = docFlag("active");

// --- programmes ----------------------------------------------------------------------------------------
const editingProgramme = ref<Programme | null>(null);
async function onSaveProgramme(name: string, data: Partial<Programme>) {
  if (await run(() => saveProgramme(name, data), "Entry requirements saved")) editingProgramme.value = null;
}
function entrySummary(p: Programme) {
  if (p.level === "Postgraduate") {
    return [p.min_prior_nqf ? `NQF ${p.min_prior_nqf}` : "", p.min_prior_average ? `${p.min_prior_average}%` : ""].filter(Boolean).join(", ") || "None set";
  }
  const subjects = p.subject_requirements.map((r) => `${r.subject} ${r.grade}`).join(", ");
  return [p.min_points ? `${p.min_points} points` : "", subjects].filter(Boolean).join(" · ") || "None set";
}

// --- points scale --------------------------------------------------------------------------------------
const scale = ref<ScaleRow[]>([]);
const scaleLevel = ref("NSSCO");
function resetScale() {
  scale.value = (setup.value?.points_scale ?? []).map((r) => ({ ...r }));
}
const levelRows = computed(() => scale.value.filter((r) => r.level === scaleLevel.value));
const addGrade = () => scale.value.push({ level: scaleLevel.value, grade: "", points: 0 });
function removeGrade(row: ScaleRow) {
  scale.value.splice(scale.value.indexOf(row), 1);
}
async function onSaveScale() {
  if (await run(() => savePointsScale(scale.value.filter((r) => r.grade.trim())), "Points scale saved")) resetScale();
}
</script>

<template>
  <section class="setup">
    <PageHeader title="Admission setup" subtitle="The university's own admission rules. Changes apply from the next assessment." />

    <div v-if="!setup && !loadError" class="loading"><ProgressSpinner style="width: 2.5rem; height: 2.5rem" aria-label="Loading" /></div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="setup">
      <SelectButton v-model="tab" :options="TABS" option-label="label" option-value="value" :allow-empty="false" aria-label="Section" class="tabs" />

      <RulesForm
        v-if="tab === 'rules'"
        :settings="setup.settings"
        :countries="setup.choices.countries"
        :saving="saving"
        @save="(data) => run(() => saveSettings(data), 'Rules saved')"
      />

      <template v-else-if="tab === 'pathways'">
        <DataTable :value="setup.pathways" data-key="name" class="table">
          <Column header="Pathway">
            <template #body="{ data }">
              <strong>{{ data.name }}</strong>
              <div class="sub">{{ data.level }} · {{ data.evidence }}</div>
            </template>
          </Column>
          <Column header="Rules">
            <template #body="{ data }">
              <span class="sub">
                <template v-if="data.min_age">From age {{ data.min_age }} · </template>
                <template v-if="data.referees_required">{{ data.referees_required }} referees · </template>
                {{ pathwayDocs(data) ? `${pathwayDocs(data)} required ${pathwayDocs(data) === 1 ? "document" : "documents"}` : "No required documents" }}
              </span>
            </template>
          </Column>
          <Column header="">
            <template #body="{ data }">
              <Tag :severity="data.active ? 'success' : 'secondary'" :value="data.active ? 'Open' : 'Closed'" />
            </template>
          </Column>
          <Column header="" class="actions-col">
            <template #body="{ data }"><Button label="Edit" size="small" text @click="editingPathway = data" /></template>
          </Column>
        </DataTable>
        <Button label="Add a pathway" text class="add" @click="editingPathway = 'new'" />
      </template>

      <template v-else-if="tab === 'documents'">
        <DataTable :value="setup.documents" data-key="name" class="table">
          <Column header="Document">
            <template #body="{ data }">
              <strong>{{ data.name }}</strong>
              <div v-if="data.description" class="sub">{{ data.description }}</div>
            </template>
          </Column>
          <Column header="Asked of">
            <template #body="{ data }"><span class="sub">{{ data.required_for }}</span></template>
          </Column>
          <Column header="">
            <template #body="{ data }">
              <Tag v-if="data.must_be_certified" severity="secondary" value="Certified" />
              <Tag v-if="!data.active" severity="secondary" value="Inactive" />
            </template>
          </Column>
          <Column header="" class="actions-col">
            <template #body="{ data }"><Button label="Edit" size="small" text @click="editDocument(data)" /></template>
          </Column>
        </DataTable>
        <Button label="Add a document" text class="add" @click="editDocument(null)" />
      </template>

      <DataTable v-else-if="tab === 'programmes'" :value="setup.programmes" data-key="name" class="table">
        <Column header="Programme">
          <template #body="{ data }">
            <strong>{{ data.name }}</strong>
            <div class="sub">{{ data.code }} · NQF {{ data.nqf_level }}</div>
          </template>
        </Column>
        <Column header="Level"><template #body="{ data }"><span class="sub">{{ data.level }}</span></template></Column>
        <Column header="Entry"><template #body="{ data }"><span class="sub">{{ entrySummary(data) }}</span></template></Column>
        <Column header="" class="actions-col">
          <template #body="{ data }"><Button label="Edit" size="small" text @click="editingProgramme = data" /></template>
        </Column>
      </DataTable>

      <section v-else class="card scale">
        <SelectButton v-model="scaleLevel" :options="setup.choices.school_levels" :allow-empty="false" aria-label="School level" />
        <div class="scale-rows">
          <div v-for="(row, index) in levelRows" :key="index" class="scale-row">
            <InputText v-model="row.grade" placeholder="Grade" :aria-label="`Grade ${index + 1}`" class="grade" />
            <InputNumber v-model="row.points" :min="0" :aria-label="`Points for grade ${index + 1}`" class="points" />
            <span class="sub">points</span>
            <Button label="✕" text severity="secondary" :aria-label="`Remove grade ${index + 1}`" @click="removeGrade(row)" />
          </div>
        </div>
        <Button label="Add a grade" text class="add" @click="addGrade" />
        <div class="footer">
          <Button label="Undo changes" text :disabled="saving" @click="resetScale" />
          <Button label="Save scale" :loading="saving" @click="onSaveScale" />
        </div>
      </section>

      <PathwayDrawer :pathway="editingPathway" :setup="setup" :saving="saving" @close="editingPathway = null" @save="onSavePathway" />
      <ProgrammeDrawer :programme="editingProgramme" :setup="setup" :saving="saving" @close="editingProgramme = null" @save="onSaveProgramme" />

      <Dialog
        :visible="editingDocument !== null"
        modal
        :header="editingDocument?.isNew ? 'New document' : editingDocument?.name"
        :style="{ width: 'min(32rem, calc(100vw - 32px))' }"
        @update:visible="(v: boolean) => !v && (editingDocument = null)"
      >
        <div v-if="editingDocument" class="doc-form">
          <div v-if="editingDocument.isNew" class="field">
            <label for="doc-name">Name</label>
            <InputText id="doc-name" v-model="editingDocument.document_name" fluid />
          </div>
          <div class="field">
            <label id="doc-for-label" for="doc-for">Asked of</label>
            <Select v-model="editingDocument.required_for" input-id="doc-for" aria-labelledby="doc-for-label" :options="setup.choices.required_for" fluid />
            <small class="sub">Pathway only: asked for by the pathways that list it.</small>
          </div>
          <div class="field">
            <label for="doc-desc">Guidance for applicants</label>
            <Textarea id="doc-desc" v-model="editingDocument.description" rows="2" auto-resize fluid />
          </div>
          <label class="switch"><ToggleSwitch v-model="certified" input-id="doc-cert" /> <span>Certified copy required</span></label>
          <label class="switch"><ToggleSwitch v-model="docActive" input-id="doc-active" /> <span>In use</span></label>
        </div>
        <template #footer>
          <Button label="Cancel" text @click="editingDocument = null" />
          <Button label="Save" :loading="saving" :disabled="Boolean(editingDocument?.isNew && !editingDocument.document_name?.trim())" @click="onSaveDocument" />
        </template>
      </Dialog>
    </template>
  </section>
</template>

<style scoped>
.setup {
  display: grid;
  gap: 1rem;
}

.head h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

.intro,
.sub {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.tabs {
  flex-wrap: wrap;
  justify-self: start;
}

.table {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  overflow: hidden;
}

:deep(.actions-col) {
  width: 1%;
  text-align: right;
}

.add {
  justify-self: start;
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

.footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}

.doc-form {
  display: grid;
  gap: 0.9rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

label {
  font-size: 0.875rem;
}

.switch {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  cursor: pointer;
}
</style>
