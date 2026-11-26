<script setup lang="ts">
import { Paperclip } from "@lucide/vue";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import ServiceThread from "@/modules/records/ServiceThread.vue";
import { type ServiceRequest, documentUrl, myServiceRequests, withdrawService, writeMine } from "@/modules/records/serviceRequests";

/** One of the student's service requests: what they asked, the office's messages, writing back, and the outcome */
const props = defineProps<{ name: string }>();
const toast = useToast();
const request = ref<ServiceRequest | null>(null);
const error = ref("");

watch(
  () => props.name,
  async () => {
    try {
      request.value = (await myServiceRequests()).requests.find((r) => r.name === props.name) ?? null;
      if (!request.value) error.value = "This request is not yours, or no longer exists.";
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);
const open = computed(() => request.value?.status === "Submitted" || request.value?.status === "In progress");
const outstanding = computed(() => (request.value?.fee_unpaid && open.value ? [`Fee of ${formatMoney(request.value.fee)} to pay (on your fee statement)`] : []));
async function send(message: string, file: File | null) {
  try {
    request.value = await writeMine(props.name, message, file);
  } catch (e) {
    toast.add({ severity: "error", summary: "Not sent", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    throw e;
  }
}
async function withdraw() {
  try {
    request.value = await withdrawService(props.name);
    toast.add({ severity: "success", summary: "Request withdrawn", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not withdrawn", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  }
}
</script>

<template>
  <RecordPage
    :back="{ to: { name: 'my-requests' }, label: 'Requests' }"
    :title="request?.category"
    :subtitle="request ? `${request.office} · asked ${formatDate(request.submitted_on)}${open ? ` · answer by ${formatDate(request.due_on)}` : ''}` : undefined"
    :error="error"
    :outstanding="outstanding"
  >
    <template v-if="request" #tags><StatusTag kind="service" :value="request.status" /></template>
    <template v-if="request?.status === 'Submitted'" #actions>
      <EcButton label="Withdraw" variant="ghost" @click="withdraw" />
    </template>

    <template v-if="request">
      <EcPanel title="Your request">
        <p class="details">{{ request.details }}</p>
        <a v-if="request.attachment" :href="documentUrl(request.name)" class="doc" target="_blank" rel="noopener"><Paperclip :size="13" /> Your document</a>
        <p v-if="request.outcome_note" class="outcome"><strong>{{ request.status }}:</strong> {{ request.outcome_note }}</p>
      </EcPanel>
      <EcPanel title="Messages">
        <ServiceThread :request="request" :can-reply="open" :send="send" :placeholder="`Write to ${request.office}`" />
      </EcPanel>
    </template>
  </RecordPage>
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
