<script setup lang="ts">
import { Plus, X } from "@lucide/vue";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
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
  emit("save", { ...rest, documents: clean, ...(isNew.value ? { pathway_name } : {}) }, existing.value?.name);
}
</script>

<template>
  <DetailPane
    :title="isNew ? 'New pathway' : form.pathway_name"
    :subtitle="existing ? `Used by ${existing.applications} ${existing.applications === 1 ? 'application' : 'applications'}` : 'A route into the university'"
  >
    <template #tags>
      <label class="switch"><ToggleSwitch v-model="open" input-id="pw-open" /> <span>Open</span></label>
    </template>

    <DetailSection title="Route">
      <div class="grid">
        <EcField v-if="isNew" label="Name" for="pw-name"><InputText id="pw-name" v-model="form.pathway_name" fluid /></EcField>
        <EcField label="Level">
          <SelectButton v-model="form.level" :options="['Undergraduate', 'Postgraduate']" :allow-empty="false" aria-label="Level" size="small" />
        </EcField>
        <EcField label="Judged on" for="pw-evidence" label-id="pw-evidence-label">
          <Select v-model="form.evidence" input-id="pw-evidence" aria-labelledby="pw-evidence-label" :options="setup.choices.evidence" fluid />
        </EcField>
        <EcField label="Minimum age" for="pw-age" hint="On 1 January of the intake's year. 0: none">
          <InputNumber v-model="form.min_age" input-id="pw-age" :min="0" :max="99" fluid />
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
        <SelectButton
          v-model="doc.required"
          :options="[{ label: 'Required', value: true }, { label: 'Optional', value: false }]"
          option-label="label"
          option-value="value"
          :allow-empty="false"
          size="small"
          :aria-label="`Required, document ${index + 1}`"
        />
        <EcButton :icon="X" size="sm" variant="ghost" :aria-label="`Remove document ${index + 1}`" @click="form.documents!.splice(index, 1)" />
      </div>
      <EcButton label="Add a document" :icon="Plus" size="sm" variant="ghost" @click="addDocument" />
    </DetailSection>

    <template #actions>
      <EcButton label="Cancel" variant="ghost" :disabled="saving" @click="isNew ? emit('cancel') : reset()" />
      <EcButton label="Save" variant="primary" :loading="saving" :disabled="isNew && !form.pathway_name.trim()" @click="save" />
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

.doc-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.doc {
  flex: 1 1 14rem;
}
</style>
