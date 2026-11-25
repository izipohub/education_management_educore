<script setup lang="ts">
import { Plus, X } from "@lucide/vue";
import Checkbox from "primevue/checkbox";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, ref, watch } from "vue";
import DetailPane from "@/core/ui/DetailPane.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import type { FundingRoute, PathwayDocument, Setup } from "./api";

/** A funding route: who pays, what applicants on it are asked for; "new" adds one */
const props = defineProps<{ route: FundingRoute | "new"; setup: Setup; saving: boolean }>();
const emit = defineEmits<{ cancel: []; save: [Partial<FundingRoute>, string | undefined] }>();

const blank = (): Partial<FundingRoute> & { route_name: string; documents: PathwayDocument[] } => ({
  route_name: "",
  kind: props.setup.choices.funding_kinds[0],
  sponsor: null,
  description: "",
  ask_who: 1,
  sort_order: 60,
  active: 1,
  documents: [],
});
const form = ref(blank());
watch(
  () => props.route,
  () => {
    const r = props.route;
    form.value = r === "new" ? blank() : { ...r, documents: r.documents.map((d) => ({ ...d })) };
  },
  { immediate: true },
);
const isNew = computed(() => props.route === "new");
const existing = computed(() => (props.route === "new" ? null : props.route));
const offered = computed({ get: () => Boolean(form.value.active), set: (on: boolean) => (form.value.active = on ? 1 : 0) });
const askWho = computed({ get: () => Boolean(form.value.ask_who), set: (on: boolean) => (form.value.ask_who = on ? 1 : 0) });
const documentNames = computed(() => props.setup.documents.filter((d) => d.active).map((d) => d.name));
const addDocument = () => form.value.documents.push({ document_type: "", applies_to: props.setup.choices.applies_to[0] ?? "Everyone", required: true });

function save() {
  const { route_name, documents, kind, sponsor, description, ask_who, sort_order, active } = form.value;
  emit(
    "save",
    { route_name: route_name.trim(), kind, sponsor: sponsor || null, description, ask_who, sort_order, active, documents: documents.filter((d) => d.document_type) },
    existing.value?.name,
  );
}
</script>

<template>
  <DetailPane :title="isNew ? 'New funding route' : form.route_name" :subtitle="existing ? (existing.pays_application_fee ? 'Pays the application fee' : 'No application fee') : 'How studies are paid for'">
    <template #tags>
      <label class="switch"><ToggleSwitch v-model="offered" input-id="fr-active" /> <span>Offered</span></label>
    </template>

    <DetailSection title="Funding">
      <div class="grid">
        <EcField label="Name" for="fr-name" :hint="existing && form.route_name.trim() !== existing.name ? 'Renaming keeps its applications' : undefined">
          <InputText id="fr-name" v-model="form.route_name" fluid />
        </EcField>
        <EcField label="Kind" for="fr-kind">
          <Select v-model="form.kind" input-id="fr-kind" :options="setup.choices.funding_kinds" fluid />
        </EcField>
        <EcField label="Sponsor" for="fr-sponsor" hint="Finance sees the students who chose it">
          <Select v-model="form.sponsor" input-id="fr-sponsor" :options="setup.choices.sponsors" option-label="sponsor_name" option-value="name" show-clear placeholder="None" fluid />
        </EcField>
        <EcField label="Order shown" for="fr-order">
          <InputNumber v-model="form.sort_order" input-id="fr-order" :min="0" :use-grouping="false" fluid />
        </EcField>
      </div>
      <label class="switch spaced"><ToggleSwitch v-model="askWho" input-id="fr-ask" /> <span>Ask the name and contact of who pays</span></label>
      <EcField label="Description for applicants" for="fr-desc" class="spaced">
        <Textarea id="fr-desc" v-model="form.description" rows="2" auto-resize fluid />
      </EcField>
      <p class="ec-muted spaced">Whether applicants on this route pay the application fee is set by the Bursar in Fee settings.</p>
    </DetailSection>

    <DetailSection title="Documents" :summary="`${form.documents.filter((d) => d.required).length} required`">
      <div v-for="(doc, index) in form.documents" :key="index" class="doc-row">
        <Select v-model="doc.document_type" :options="documentNames" placeholder="Document" filter :aria-label="`Document ${index + 1}`" class="doc" size="small" />
        <Select v-model="doc.applies_to" :options="setup.choices.applies_to" :aria-label="`Asked of, document ${index + 1}`" size="small" />
        <label class="required"><Checkbox v-model="doc.required" binary :input-id="`fr-req-${index}`" /> Required</label>
        <EcButton :icon="X" size="sm" variant="ghost" :aria-label="`Remove document ${index + 1}`" @click="form.documents.splice(index, 1)" />
      </div>
      <EcButton label="Add a document" :icon="Plus" size="sm" variant="ghost" @click="addDocument" />
    </DetailSection>

    <template #actions>
      <EcButton label="Cancel" variant="ghost" :disabled="saving" @click="emit('cancel')" />
      <EcButton label="Save" variant="primary" :loading="saving" :disabled="!form.route_name.trim()" @click="save" />
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
  margin: 0;
}

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
