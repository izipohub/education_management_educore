<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Delivery, type MyTranscripts, deliveryText, myTranscripts, requestTranscript } from "@/modules/records/transcripts";

/** Official transcripts: the student's requests to the Registry, and asking for one */
const toast = useToast();
const state = ref<MyTranscripts | null>(null);
const open = ref(false);
const delivery = ref<Delivery>("Collect at the campus");
const copies = ref(1);
const recipient = ref("");
const email = ref("");
const address = ref("");
const busy = ref(false);

onMounted(async () => {
  state.value = await myTranscripts().catch(() => null);
});

const options = [
  { value: "Collect at the campus" as Delivery, label: "Collect" },
  { value: "Email" as Delivery, label: "Email" },
  { value: "Post" as Delivery, label: "Post" },
];
const count = computed(() => (delivery.value === "Email" ? 1 : copies.value || 0));
const fee = computed(() => (state.value?.fee ?? 0) * count.value);
const ready = computed(() => {
  if (delivery.value === "Email") return Boolean(recipient.value.trim() && /\S+@\S+\.\S+/.test(email.value.trim()));
  if (delivery.value === "Post") return Boolean(recipient.value.trim() && address.value.trim() && copies.value >= 1);
  return copies.value >= 1;
});
function start() {
  delivery.value = "Collect at the campus";
  copies.value = 1;
  recipient.value = email.value = address.value = "";
  open.value = true;
}
async function send() {
  busy.value = true;
  try {
    state.value = await requestTranscript({
      copies: count.value,
      delivery: delivery.value,
      recipient: recipient.value.trim() || undefined,
      email: delivery.value === "Email" ? email.value.trim() : undefined,
      postal_address: delivery.value === "Post" ? address.value.trim() : undefined,
    });
    open.value = false;
    toast.add({ severity: "success", summary: "Sent to the Registry", detail: fee.value ? `Pay ${formatMoney(fee.value)} with your student number as the reference` : undefined, life: 5000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not sent", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section v-if="state && (state.requests.length || state.has_results)" class="block transcripts">
    <div class="head">
      <h2>Official transcripts</h2>
      <EcButton v-if="state.has_results" label="Ask for a transcript" size="sm" @click="start" />
    </div>
    <ul v-if="state.requests.length" class="history">
      <li v-for="r in state.requests" :key="r.name">
        <div class="line">
          <span>{{ deliveryText(r) }}<template v-if="r.copies > 1">, {{ r.copies }} copies</template></span>
          <StatusTag kind="transcript" :value="r.status" />
        </div>
        <div class="sub">
          Asked {{ formatDate(r.requested_on) }}
          <template v-if="r.status === 'Requested' && r.fee && !r.paid"> · {{ formatMoney(r.fee) }} to pay first</template>
          <template v-if="r.status === 'Issued'"> · issued {{ formatDate(r.issued_on) }}</template>
          <template v-if="r.review_note"> · Registry: {{ r.review_note }}</template>
        </div>
      </li>
    </ul>
  </section>

  <EcModal :open="open" title="Ask for an official transcript" description="Your academic record, stamped and signed by the Registry" @update:open="(v: boolean) => (open = v)">
    <div class="form">
      <EcSegmented v-model="delivery" :options="options" label="How you receive it" />
      <EcField v-if="delivery !== 'Email'" label="Copies" for="transcript-copies">
        <InputNumber v-model="copies" input-id="transcript-copies" :min="1" :max="10" show-buttons fluid />
      </EcField>
      <EcField v-if="delivery !== 'Collect at the campus'" label="Who it is for" for="transcript-recipient" hint="The institution, employer or person">
        <InputText id="transcript-recipient" v-model="recipient" fluid />
      </EcField>
      <EcField v-if="delivery === 'Email'" label="Their email address" for="transcript-email" hint="The Registry emails it there">
        <InputText id="transcript-email" v-model="email" type="email" fluid />
      </EcField>
      <EcField v-if="delivery === 'Post'" label="Postal address" for="transcript-address">
        <Textarea id="transcript-address" v-model="address" rows="3" auto-resize fluid />
      </EcField>
      <p class="sub">
        <template v-if="fee">The fee is {{ formatMoney(fee) }}; the Registry issues it once paid.</template>
        <template v-else>There is no fee.</template>
        <template v-if="state?.needs_clearance"> You must be financially cleared.</template>
      </p>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="open = false" />
      <EcButton label="Send" variant="primary" :loading="busy" :disabled="!ready" @click="send" />
    </template>
  </EcModal>
</template>

<style scoped>
.transcripts {
  margin-bottom: 1.5rem;
}

h2 {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6b7280;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.form {
  display: grid;
  gap: 0.75rem;
}

.history {
  display: grid;
  gap: 0.6rem;
  margin: 0.5rem 0 0;
  padding: 0;
  list-style: none;
}

.line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.sub {
  margin: 0.25rem 0 0;
  color: var(--ec-muted);
  font-size: 0.8rem;
}
</style>
