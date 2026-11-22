<script setup lang="ts">
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, ref, watch } from "vue";
import type { Pathway, PathwayDocument, Setup } from "./api";

/** pathway: the one being edited; "new": adding one; null: closed */
const props = defineProps<{ pathway: Pathway | "new" | null; setup: Setup; saving: boolean }>();
const emit = defineEmits<{ close: []; save: [Partial<Pathway> & { pathway_name?: string }, string | undefined] }>();

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
watch(
  () => props.pathway,
  (p) => {
    form.value = p === "new" || !p ? blank() : { ...p, pathway_name: p.name, documents: p.documents.map((d) => ({ ...d })) };
  },
  { immediate: true },
);
const isNew = computed(() => props.pathway === "new");
const open = computed({
  get: () => Boolean(form.value.active),
  set: (on: boolean) => (form.value.active = on ? 1 : 0),
});

const documentNames = computed(() => props.setup.documents.filter((d) => d.active).map((d) => d.name));
const addDocument = () =>
  form.value.documents!.push({ document_type: "", applies_to: props.setup.choices.applies_to[0] ?? "Everyone", required: true });

function save() {
  const { pathway_name, documents, ...rest } = form.value;
  const clean = (documents ?? []).filter((d: PathwayDocument) => d.document_type);
  emit("save", { ...rest, documents: clean, ...(isNew.value ? { pathway_name } : {}) }, isNew.value ? undefined : (props.pathway as Pathway).name);
}
</script>

<template>
  <Drawer
    :visible="pathway !== null"
    position="right"
    :header="isNew ? 'New pathway' : form.pathway_name"
    :pt="{ root: { style: 'width: min(40rem, 100vw)' } }"
    @update:visible="(v: boolean) => !v && emit('close')"
  >
    <div class="form">
      <div v-if="isNew" class="field">
        <label for="pw-name">Name</label>
        <InputText id="pw-name" v-model="form.pathway_name" fluid />
      </div>
      <Message v-else-if="typeof pathway === 'object' && pathway && pathway.applications" severity="info" :closable="false">
        Used by {{ pathway.applications }} {{ pathway.applications === 1 ? "application" : "applications" }}. Close it to stop new applications.
      </Message>

      <label class="switch"><ToggleSwitch v-model="open" input-id="pw-open" /> <span>Open for applications</span></label>

      <div class="grid">
        <div class="field">
          <label for="pw-level">Level</label>
          <SelectButton v-model="form.level" :options="['Undergraduate', 'Postgraduate']" :allow-empty="false" aria-label="Level" />
        </div>
        <div class="field">
          <label id="pw-evidence-label" for="pw-evidence">Judged on</label>
          <Select v-model="form.evidence" input-id="pw-evidence" aria-labelledby="pw-evidence-label" :options="setup.choices.evidence" fluid />
        </div>
        <div class="field">
          <label for="pw-age">Minimum age</label>
          <InputNumber v-model="form.min_age" input-id="pw-age" :min="0" :max="99" fluid />
          <small class="sub">On 1 January of the intake's year. 0: none.</small>
        </div>
        <div class="field">
          <label for="pw-ref">Referees</label>
          <InputNumber v-model="form.referees_required" input-id="pw-ref" :min="0" :max="5" fluid />
        </div>
        <div class="field">
          <label for="pw-order">Order shown</label>
          <InputNumber v-model="form.sort_order" input-id="pw-order" :min="0" :use-grouping="false" fluid />
        </div>
      </div>

      <div class="field">
        <label for="pw-desc">Description for applicants</label>
        <Textarea id="pw-desc" v-model="form.description" rows="2" auto-resize fluid />
      </div>

      <div class="field">
        <label>Documents</label>
        <small class="sub">In addition to the identity documents every applicant uploads.</small>
        <div v-for="(doc, index) in form.documents" :key="index" class="doc-row">
          <Select v-model="doc.document_type" :options="documentNames" placeholder="Document" filter :aria-label="`Document ${index + 1}`" class="doc" />
          <Select v-model="doc.applies_to" :options="setup.choices.applies_to" :aria-label="`Asked of, document ${index + 1}`" />
          <SelectButton
            v-model="doc.required"
            :options="[{ label: 'Required', value: true }, { label: 'Optional', value: false }]"
            option-label="label"
            option-value="value"
            :allow-empty="false"
            :aria-label="`Required, document ${index + 1}`"
          />
          <Button label="✕" text severity="secondary" :aria-label="`Remove document ${index + 1}`" @click="form.documents!.splice(index, 1)" />
        </div>
        <Button label="Add a document" text class="add" @click="addDocument" />
      </div>
    </div>
    <template #footer>
      <div class="footer">
        <Button label="Cancel" text @click="emit('close')" />
        <Button label="Save" :loading="saving" :disabled="isNew && !form.pathway_name.trim()" @click="save" />
      </div>
    </template>
  </Drawer>
</template>

<style scoped>
.form {
  display: grid;
  gap: 1rem;
}

.grid {
  display: grid;
  align-items: start;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 0.9rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

label {
  font-size: 0.875rem;
}

.sub {
  font-size: 0.8rem;
  color: #6b7280;
}

.switch {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  cursor: pointer;
}

.doc-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.doc {
  flex: 1 1 14rem;
}

.add {
  justify-self: start;
}

.footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
