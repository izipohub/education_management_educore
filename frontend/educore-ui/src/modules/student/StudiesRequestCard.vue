<script setup lang="ts">
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { formatDate, toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type MyStudiesRequests, type RequestType, myStudiesRequests, requestStudiesChange } from "@/modules/records/studiesRequests";

/** Interrupting or cancelling studies: the student's request to the Registry, and its outcome */
const toast = useToast();
const state = ref<MyStudiesRequests | null>(null);
const open = ref(false);
const type = ref<RequestType>("Interruption");
const lastDay = ref<Date>(new Date());
const returnYear = ref<string | null>(null);
const reason = ref("");
const busy = ref(false);

onMounted(async () => {
  state.value = await myStudiesRequests().catch(() => null);
});

const types = [
  { value: "Interruption" as RequestType, label: "Interrupt studies" },
  { value: "Cancellation" as RequestType, label: "Cancel studies" },
];
const ready = computed(() => Boolean(reason.value.trim() && lastDay.value && (type.value === "Cancellation" || returnYear.value)));
function start() {
  type.value = "Interruption";
  lastDay.value = new Date();
  returnYear.value = state.value?.return_years[0] ?? null;
  reason.value = "";
  open.value = true;
}
async function send() {
  busy.value = true;
  try {
    state.value = await requestStudiesChange(type.value, toIsoDate(lastDay.value), reason.value.trim(), type.value === "Interruption" ? returnYear.value : null);
    open.value = false;
    toast.add({ severity: "success", summary: "Sent to the Registry", life: 3000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not sent", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
const describe = (r: MyStudiesRequests["requests"][number]) =>
  r.request_type === "Interruption" ? `Interrupt studies, returning in ${r.return_year}` : "Cancel studies";
</script>

<template>
  <section v-if="state && (state.requests.length || state.can_request)" class="block studies">
    <div class="head">
      <h2>Interrupting or cancelling studies</h2>
      <EcButton v-if="state.can_request" label="Ask the Registry" size="sm" @click="start" />
    </div>
    <p v-if="state.interrupted_until" class="sub">Your studies are interrupted; you register again for {{ state.interrupted_until }}.</p>
    <ul v-if="state.requests.length" class="history">
      <li v-for="r in state.requests" :key="r.name">
        <div class="line">
          <span>{{ describe(r) }}</span>
          <StatusTag kind="request" :value="r.status" />
        </div>
        <div class="sub">
          Last day {{ formatDate(r.last_day) }} · {{ r.reason }}<template v-if="r.review_note"> · Registry: {{ r.review_note }}</template>
        </div>
      </li>
    </ul>
  </section>

  <EcModal :open="open" title="Interrupting or cancelling studies" @update:open="(v: boolean) => (open = v)">
    <div class="form">
      <EcSegmented v-model="type" :options="types" label="Request" />
      <EcField label="Last day attending" for="last-day">
        <DatePicker v-model="lastDay" input-id="last-day" date-format="dd-mm-yy" show-icon fluid :max-date="new Date()" />
      </EcField>
      <EcField v-if="type === 'Interruption'" label="Returning in" for="return-year">
        <Select v-model="returnYear" input-id="return-year" :options="state?.return_years ?? []" fluid />
      </EcField>
      <EcField label="Reason" for="studies-reason">
        <InputText id="studies-reason" v-model="reason" fluid />
      </EcField>
      <p v-if="type === 'Cancellation'" class="sub">To study again after cancelling, you apply again.</p>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="open = false" />
      <EcButton label="Send" variant="primary" :loading="busy" :disabled="!ready" @click="send" />
    </template>
  </EcModal>
</template>

<style scoped>
.studies {
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
