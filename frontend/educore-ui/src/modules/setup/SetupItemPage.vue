<script setup lang="ts">
import { ChevronLeft } from "@lucide/vue";
import Message from "primevue/message";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import DocumentEditor from "./DocumentEditor.vue";
import PathwayEditor from "./PathwayEditor.vue";
import ProgrammeEditor from "./ProgrammeEditor.vue";
import { type DocumentType, type Pathway, type Setup, getSetup, saveDocumentType, savePathway, saveProgramme } from "./api";

/**
 * One entry pathway, document or programme of the admission setup, on its own page; Save or Cancel returns to
 * its list. `name` is "new" while adding a pathway or a document.
 */
const props = defineProps<{ section: "pathways" | "documents" | "programmes"; name: string }>();
const router = useRouter();
const toast = useToast();
const setup = ref<Setup | null>(null);
const error = ref("");
const saving = ref(false);

onMounted(async () => {
  try {
    setup.value = await getSetup();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

const LABELS = { pathways: "Entry pathways", documents: "Documents", programmes: "Programmes" };
const back = computed(() => ({ name: "admission-setup", query: { tab: props.section } }));
const isNew = computed(() => props.name === "new");
const pathway = computed<Pathway | "new" | null>(() => (isNew.value ? "new" : (setup.value?.pathways.find((p) => p.name === props.name) ?? null)));
const documentType = computed<DocumentType | "new" | null>(() =>
  isNew.value ? "new" : (setup.value?.documents.find((d) => d.name === props.name) ?? null),
);
const programme = computed(() => setup.value?.programmes.find((p) => p.name === props.name) ?? null);
const missing = computed(() => setup.value && !isNew.value && !(props.section === "pathways" ? pathway.value : props.section === "documents" ? documentType.value : programme.value));

async function run(call: () => Promise<Setup>, message: string) {
  saving.value = true;
  try {
    await call();
    toast.add({ severity: "success", summary: message, life: 2500 });
    await router.push(back.value);
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
const cancel = () => router.push(back.value);
</script>

<template>
  <article class="setup-item">
    <RouterLink :to="back" class="back"><ChevronLeft :size="16" aria-hidden="true" />Admission setup · {{ LABELS[section] }}</RouterLink>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-else-if="!setup" class="card"><EcSkeleton shape="pane" :rows="4" label="Loading" /></div>
    <Message v-else-if="missing" severity="error" :closable="false">{{ name }} is not in the admission setup.</Message>

    <div v-else class="editor ec-card">
      <PathwayEditor
        v-if="section === 'pathways' && pathway"
        :pathway="pathway"
        :setup="setup"
        :saving="saving"
        @save="(data, old) => run(() => savePathway(data, old), 'Entry pathway saved')"
        @cancel="cancel"
      />
      <DocumentEditor
        v-else-if="section === 'documents' && documentType"
        :document="documentType"
        :setup="setup"
        :saving="saving"
        @save="(data, old) => run(() => saveDocumentType(data, old), 'Document saved')"
        @cancel="cancel"
      />
      <ProgrammeEditor
        v-else-if="section === 'programmes' && programme"
        :programme="programme"
        :setup="setup"
        :saving="saving"
        @save="(programmeName, data) => run(() => saveProgramme(programmeName, data), 'Entry requirements saved')"
        @cancel="cancel"
      />
    </div>
  </article>
</template>

<style scoped>
.setup-item {
  display: grid;
  gap: 1rem;
  max-width: 56rem;
}

.back {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  justify-self: start;
  color: var(--ec-muted);
  font-size: 0.8125rem;
  text-decoration: none;
}

.back:hover {
  color: var(--ec-accent);
}

.editor {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
