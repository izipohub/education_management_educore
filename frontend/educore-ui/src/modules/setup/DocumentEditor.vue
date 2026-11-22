<script setup lang="ts">
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, ref, watch } from "vue";
import DetailPane from "@/core/ui/DetailPane.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import type { DocumentType, Setup } from "./api";

/** A document applicants upload, docked beside the list; "new" adds one */
const props = defineProps<{ document: DocumentType | "new"; setup: Setup; saving: boolean }>();
const emit = defineEmits<{ cancel: []; save: [Partial<DocumentType> & { document_name?: string }, string | undefined] }>();

const blank = () => ({ document_name: "", required_for: "Pathway only", must_be_certified: 1 as 0 | 1, description: "", active: 1 as 0 | 1 });
const form = ref<Partial<DocumentType> & { document_name: string }>(blank());
const reset = () => (form.value = props.document === "new" ? blank() : { ...props.document, document_name: props.document.name });
watch(() => props.document, reset, { immediate: true });

const isNew = computed(() => props.document === "new");
const flag = (key: "must_be_certified" | "active") =>
  computed({ get: () => Boolean(form.value[key]), set: (on: boolean) => (form.value[key] = on ? 1 : 0) });
const certified = flag("must_be_certified");
const active = flag("active");

function save() {
  const { document_name, required_for, must_be_certified, description, active: inUse } = form.value;
  emit(
    "save",
    { required_for, must_be_certified, description, active: inUse, ...(isNew.value ? { document_name } : {}) },
    isNew.value ? undefined : (props.document as DocumentType).name,
  );
}
</script>

<template>
  <DetailPane :title="isNew ? 'New document' : form.document_name" subtitle="A document applicants upload">
    <template #tags>
      <label class="switch"><ToggleSwitch v-model="active" input-id="doc-active" /> <span>In use</span></label>
    </template>
    <DetailSection title="Document">
      <div class="form">
        <EcField v-if="isNew" label="Name" for="doc-name"><InputText id="doc-name" v-model="form.document_name" fluid /></EcField>
        <EcField label="Asked of" for="doc-for" label-id="doc-for-label" hint="Pathway only: asked for by the pathways that list it">
          <Select v-model="form.required_for" input-id="doc-for" aria-labelledby="doc-for-label" :options="setup.choices.required_for" fluid />
        </EcField>
        <EcField label="Guidance for applicants" for="doc-desc">
          <Textarea id="doc-desc" v-model="form.description" rows="2" auto-resize fluid />
        </EcField>
        <label class="switch"><ToggleSwitch v-model="certified" input-id="doc-cert" /> <span>Certified copy required</span></label>
      </div>
    </DetailSection>
    <template #actions>
      <EcButton label="Cancel" variant="ghost" :disabled="saving" @click="isNew ? emit('cancel') : reset()" />
      <EcButton label="Save" variant="primary" :loading="saving" :disabled="isNew && !form.document_name.trim()" @click="save" />
    </template>
  </DetailPane>
</template>

<style scoped>
.form {
  display: grid;
  gap: 0.9rem;
  max-width: 32rem;
}

.switch {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.8125rem;
  cursor: pointer;
}
</style>
