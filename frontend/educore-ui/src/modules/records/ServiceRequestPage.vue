<script setup lang="ts">
import { Paperclip } from "@lucide/vue";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import ServiceThread from "./ServiceThread.vue";
import { type ServiceRequest, declineService, documentUrl, getServiceRequest, resolveService, takeService, writeService } from "./serviceRequests";

/** One service request, for the office handling it: the student's request and document, the messages, and the decisions */
const props = defineProps<{ name: string }>();
const route = useRoute();
const toast = useToast();
const request = ref<ServiceRequest | null>(null);
const error = ref("");
const busy = ref(false);

watch(
  () => props.name,
  async () => {
    try {
      request.value = await getServiceRequest(props.name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);
const open = computed(() => request.value?.status === "Submitted" || request.value?.status === "In progress");
const subtitle = computed(() => {
  const r = request.value;
  return r ? [r.student_name, r.student, r.campus?.replace(" Campus", ""), `asked ${formatDate(r.submitted_on)}`].filter(Boolean).join(" · ") : "";
});
const outstanding = computed(() => {
  const r = request.value;
  if (!r || !open.value) return [];
  return [r.overdue && `Overdue since ${formatDate(r.due_on)}`, r.fee_unpaid && `Fee of ${formatMoney(r.fee)} not paid yet`].filter(Boolean) as string[];
});

async function act(run: () => Promise<ServiceRequest>, done: string) {
  busy.value = true;
  try {
    request.value = await run();
    toast.add({ severity: "success", summary: done, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not done", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}
async function send(message: string, file: File | null) {
  if (!(await act(() => writeService(props.name, message, file), "Sent to the student"))) throw new Error("not sent");
}
// resolving or declining: one note to the student
const closing = ref<"resolve" | "decline" | null>(null);
const note = ref("");
async function confirmClose() {
  const ok = await act(
    () => (closing.value === "resolve" ? resolveService(props.name, note.value.trim()) : declineService(props.name, note.value.trim())),
    closing.value === "resolve" ? "Resolved" : "Declined",
  );
  if (ok) closing.value = null;
}
</script>

<template>
  <RecordPage
    :back="{ to: { name: 'service-requests', query: route.query }, label: 'Service requests' }"
    :title="request?.category"
    :subtitle="subtitle"
    :error="error"
    :outstanding="outstanding"
  >
    <template v-if="request" #tags><StatusTag kind="service" :value="request.status" /></template>
    <template v-if="request && open" #actions>
      <EcButton v-if="request.status === 'Submitted'" label="Take it" :loading="busy" @click="act(() => takeService(name), 'Yours now')" />
      <EcButton label="Decline" variant="ghost" :disabled="busy" @click="(closing = 'decline'), (note = '')" />
      <EcButton label="Resolve" variant="primary" :disabled="busy || request.fee_unpaid" @click="(closing = 'resolve'), (note = '')" />
    </template>

    <template v-if="request">
      <EcPanel title="The request">
        <p class="details">{{ request.details }}</p>
        <a v-if="request.attachment" :href="documentUrl(request.name)" class="doc" target="_blank" rel="noopener"><Paperclip :size="13" /> The student's document</a>
        <p v-if="request.outcome_note" class="outcome"><strong>{{ request.status }}:</strong> {{ request.outcome_note }}</p>
      </EcPanel>
      <EcPanel title="Messages" note="The student sees your office's name">
        <ServiceThread :request="request" :can-reply="open" :send="send" placeholder="Write to the student (they are emailed)" />
      </EcPanel>
    </template>

    <template v-if="request" #aside>
      <EcPanel title="Handling">
        <dl class="ec-facts stacked">
          <div><dt>Office</dt><dd>{{ request.office }}</dd></div>
          <div><dt>Due</dt><dd>{{ formatDate(request.due_on) }}</dd></div>
          <div><dt>Handled by</dt><dd>{{ request.assigned_to ?? "Not taken yet" }}</dd></div>
          <div v-if="request.fee"><dt>Fee</dt><dd>{{ formatMoney(request.fee) }} · {{ request.fee_unpaid ? "not paid" : "paid" }}</dd></div>
        </dl>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal :open="closing !== null" :title="closing === 'resolve' ? 'Resolve the request' : 'Decline the request'" @update:open="(v: boolean) => !v && (closing = null)">
    <EcField :label="closing === 'resolve' ? 'To the student (optional)' : 'Why (to the student)'" for="close-note" :hint="closing === 'resolve' ? 'E.g. the letter is ready for collection' : undefined">
      <Textarea id="close-note" v-model="note" rows="3" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="closing = null" />
      <EcButton :label="closing === 'resolve' ? 'Resolve' : 'Decline'" variant="primary" :loading="busy" :disabled="closing === 'decline' && !note.trim()" @click="confirmClose" />
    </template>
  </EcModal>
</template>

<style scoped>
.details {
  margin: 0;
  white-space: pre-line;
}

.doc {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin-top: 0.6rem;
  color: var(--ec-accent);
  font-size: 0.85rem;
  text-decoration: none;
}

.outcome {
  margin: 0.9rem 0 0;
  padding-top: 0.9rem;
  border-top: 1px solid var(--ec-border-soft);
}
</style>
