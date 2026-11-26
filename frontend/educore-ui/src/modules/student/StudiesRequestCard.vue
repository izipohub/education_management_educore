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
import { type MyStudiesRequests, type RequestType, describeRequest, myStudiesRequests, requestStudiesChange } from "@/modules/records/studiesRequests";

/** Interrupting or cancelling studies, or moving to another campus: the student's request to the Registry, and its outcome */
const toast = useToast();
const state = ref<MyStudiesRequests | null>(null);
const open = ref(false);
const type = ref<RequestType>("Interruption");
const lastDay = ref<Date>(new Date());
const returnYear = ref<string | null>(null);
const toOffering = ref<string | null>(null);
const fromYear = ref<string | null>(null);
const reason = ref("");
const busy = ref(false);

onMounted(async () => {
  state.value = await myStudiesRequests().catch(() => null);
});

const types = computed(() => [
  { value: "Interruption" as RequestType, label: "Interrupt studies" },
  { value: "Cancellation" as RequestType, label: "Cancel studies" },
  ...(state.value?.transfer_offerings.length ? [{ value: "Campus transfer" as RequestType, label: "Move campus" }] : []),
]);
const offerings = computed(() =>
  (state.value?.transfer_offerings ?? []).map((o) => ({ value: o.name, label: `${o.campus}, ${o.mode_of_study.toLowerCase()}` })),
);
const ready = computed(() => {
  if (!reason.value.trim()) return false;
  if (type.value === "Campus transfer") return Boolean(toOffering.value && fromYear.value);
  return Boolean(lastDay.value && (type.value === "Cancellation" || returnYear.value));
});
function start() {
  type.value = "Interruption";
  lastDay.value = new Date();
  returnYear.value = state.value?.return_years[0] ?? null;
  toOffering.value = state.value?.transfer_offerings[0]?.name ?? null;
  fromYear.value = state.value?.transfer_years[0] ?? null;
  reason.value = "";
  open.value = true;
}
async function send() {
  busy.value = true;
  try {
    const moving = type.value === "Campus transfer";
    state.value = await requestStudiesChange(
      type.value,
      moving ? null : toIsoDate(lastDay.value),
      reason.value.trim(),
      type.value === "Interruption" ? returnYear.value : null,
      moving ? { to_offering: toOffering.value!, from_year: fromYear.value! } : undefined,
    );
    open.value = false;
    toast.add({ severity: "success", summary: "Sent to the Registry", life: 3000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not sent", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
const describe = describeRequest;
</script>

<template>
  <section v-if="state && (state.requests.length || state.can_request)" class="block studies">
    <div class="head">
      <h2>Interrupting, cancelling or moving campus</h2>
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
          <template v-if="r.last_day">Last day {{ formatDate(r.last_day) }} · </template>{{ r.reason }}<template v-if="r.review_note"> · Registry: {{ r.review_note }}</template>
        </div>
      </li>
    </ul>
  </section>

  <EcModal :open="open" title="Your studies" @update:open="(v: boolean) => (open = v)">
    <div class="form">
      <EcSegmented v-model="type" :options="types" label="Request" />
      <template v-if="type === 'Campus transfer'">
        <EcField label="Move to" for="move-to" :hint="`The same programme; you are at ${state?.campus ?? ''} now`">
          <Select v-model="toOffering" input-id="move-to" :options="offerings" option-label="label" option-value="value" fluid />
        </EcField>
        <EcField label="Starting from" for="move-from" hint="The first year you register at the new campus">
          <Select v-model="fromYear" input-id="move-from" :options="state?.transfer_years ?? []" fluid />
        </EcField>
      </template>
      <EcField v-if="type !== 'Campus transfer'" label="Last day attending" for="last-day">
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
