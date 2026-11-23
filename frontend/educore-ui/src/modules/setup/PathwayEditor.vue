<script setup lang="ts">
import { Plus, X } from "@lucide/vue";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Checkbox from "primevue/checkbox";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, ref, watch } from "vue";
import DetailPane from "@/core/ui/DetailPane.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import type { Pathway, PathwayDocument, Setup } from "./api";

/** A pathway, docked beside the list: edited in place; "new" adds one */
const props = defineProps<{ pathway: Pathway | "new"; setup: Setup; saving: boolean }>();
const emit = defineEmits<{ cancel: []; save: [Partial<Pathway> & { pathway_name?: string }, string | undefined] }>();

const blank = (): Partial<Pathway> & { pathway_name: string } => ({
  pathway_name: "",
  level: "Undergraduate",
  evidence: props.setup.choices.evidence[0],
  min_age: 0,
  min_work_years: 0,
  referees_required: 0,
  sort_order: 60,
  active: 1,
  description: "",
  documents: [],
});
const form = ref(blank());
const reset = () => {
  const p = props.pathway;
  form.value = p === "new" ? blank() : { ...p, pathway_name: p.name, documents: p.documents.map((d) => ({ ...d })) };
};
watch(() => props.pathway, reset, { immediate: true });

const isNew = computed(() => props.pathway === "new");
const existing = computed(() => (props.pathway === "new" ? null : props.pathway));
const open = computed({ get: () => Boolean(form.value.active), set: (on: boolean) => (form.value.active = on ? 1 : 0) });
const documentNames = computed(() => props.setup.documents.filter((d) => d.active).map((d) => d.name));
const addDocument = () =>
  form.value.documents!.push({ document_type: "", applies_to: props.setup.choices.applies_to[0] ?? "Everyone", required: true });

function save() {
  const { pathway_name, documents, ...rest } = form.value;
  const clean = (documents ?? []).filter((d: PathwayDocument) => d.document_type);
  // the name is sent too: a changed name renames the pathway, and its applications follow
  emit("save", { ...rest, documents: clean, pathway_name: pathway_name.trim() }, existing.value?.name);
}
</script>

<template>
  <DetailPane
    :title="isNew ? 'New entry pathway' : form.pathway_name"
    :subtitle="existing ? `Used by ${existing.applications} ${existing.applications === 1 ? 'application' : 'applications'}` : 'A way into the university'"
  >
    <template #tags>
      <label class="switch"><ToggleSwitch v-model="open" input-id="pw-open" /> <span>Open</span></label>
    </template>

    <DetailSection title="Entry">
      <div class="grid">
        <EcField
          label="Name"
          for="pw-name"
          :hint="existing && form.pathway_name.trim() !== existing.name ? 'Renaming keeps its applications' : undefined"
        >
          <InputText id="pw-name" v-model="form.pathway_name" fluid />
        </EcField>
        <EcField label="Level" for="pw-level" label-id="pw-level-label">
          <Select v-model="form.level" input-id="pw-level" aria-labelledby="pw-level-label" :options="['Undergraduate', 'Postgraduate']" fluid />
        </EcField>
        <EcField label="Judged on" for="pw-evidence" label-id="pw-evidence-label">
          <Select v-model="form.evidence" input-id="pw-evidence" aria-labelledby="pw-evidence-label" :options="setup.choices.evidence" fluid />
        </EcField>
        <EcField label="Minimum age" for="pw-age" hint="On the first day of the academic year. 0: none">
          <InputNumber v-model="form.min_age" input-id="pw-age" :min="0" :max="99" fluid />
        </EcField>
        <EcField label="Minimum years of work" for="pw-work" hint="Relevant experience. 0: none">
          <InputNumber v-model="form.min_work_years" input-id="pw-work" :min="0" :max="40" :max-fraction-digits="1" fluid />
        </EcField>
        <EcField label="Referees" for="pw-ref">
          <InputNumber v-model="form.referees_required" input-id="pw-ref" :min="0" :max="5" fluid />
        </EcField>
        <EcField label="Order shown" for="pw-order">
          <InputNumber v-model="form.sort_order" input-id="pw-order" :min="0" :use-grouping="false" fluid />
        </EcField>
      </div>
      <EcField label="Description for applicants" for="pw-desc" class="spaced">
        <Textarea id="pw-desc" v-model="form.description" rows="2" auto-resize fluid />
      </EcField>
    </DetailSection>

    <DetailSection title="Documents" :summary="`${form.documents?.filter((d) => d.required).length ?? 0} required`">
      <p class="ec-muted">In addition to the identity documents every applicant uploads.</p>
      <div v-for="(doc, index) in form.documents" :key="index" class="doc-row">
        <Select v-model="doc.document_type" :options="documentNames" placeholder="Document" filter :aria-label="`Document ${index + 1}`" class="doc" size="small" />
        <Select v-model="doc.applies_to" :options="setup.choices.applies_to" :aria-label="`Asked of, document ${index + 1}`" size="small" />
        <label class="required"><Checkbox v-model="doc.required" binary :input-id="`doc-req-${index}`" /> Required</label>
        <EcButton :icon="X" size="sm" variant="ghost" :aria-label="`Remove document ${index + 1}`" @click="form.documents!.splice(index, 1)" />
      </div>
      <EcButton label="Add a document" :icon="Plus" size="sm" variant="ghost" @click="addDocument" />
    </DetailSection>

    <template #actions>
      <EcButton label="Cancel" variant="ghost" :disabled="saving" @click="emit('cancel')" />
      <EcButton label="Save" variant="primary" :loading="saving" :disabled="!form.pathway_name.trim()" @click="save" />
    </template>
  </DetailPane>
</template>

<style scoped>
.grid {
  display: grid;
  align-items: start;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 0.9rem;
}

.spaced {
  margin-top: 0.9rem;
}

.switch {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  cursor: pointer;
}

p {
  margin: 0 0 0.6rem;
}

/* one line per document: which, asked of whom, required, remove */
.doc-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(9rem, 12rem) auto auto;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.doc {
  min-width: 0;
}

.required {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.85rem;
  white-space: nowrap;
}

@media (max-width: 639px) {
  .doc-row {
    grid-template-columns: minmax(0, 1fr) auto;
  }
}
</style>
