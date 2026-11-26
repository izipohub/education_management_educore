<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import Select from "primevue/select";
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
import { type Hold, type StudentClearance, getClearance, liftHold, placeHold } from "./clearance";
import { WAIVE_KINDS, type WaiveKind, type Waiver, requestWaiver, waiverWhat, withdrawWaiver } from "./waivers";

/** One student's financial clearance: what stops it, their invoices and sponsors, the holds placed and lifted, and
 * the fee waivers requested for them (decided by the Bursar on the Fee waivers page) */
const props = defineProps<{ name: string }>();
const route = useRoute();
const toast = useToast();
const data = ref<StudentClearance | null>(null);
const error = ref("");
const busy = ref(false);

watch(
  () => props.name,
  async () => {
    data.value = null;
    error.value = "";
    try {
      data.value = await getClearance(props.name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

const back = computed(() => ({ to: { name: "clearance", query: route.query }, label: "Financial clearance" }));
const subtitle = computed(() => (data.value ? [data.value.name, data.value.campus].filter(Boolean).join(" · ") : ""));

async function act(run: () => Promise<StudentClearance>, done: string) {
  busy.value = true;
  try {
    data.value = await run();
    toast.add({ severity: "success", summary: done, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

const placing = ref(false);
const reason = ref("");
async function place() {
  if (await act(() => placeHold(props.name, reason.value), "Hold placed")) placing.value = false;
}
// a fee waiver: the page reloads after, since an approved waiver changes what is owed
const requesting = ref(false);
const waiverYear = ref<string | null>(null);
const waive = ref<WaiveKind>("Percent of fees");
const waiverValue = ref<number | null>(null);
const waiverReason = ref("");
function openRequest() {
  requesting.value = true;
  waiverYear.value = data.value?.waiver_years[0] ?? null;
  waive.value = "Percent of fees";
  waiverValue.value = null;
  waiverReason.value = "";
}
const canRequest = computed(
  () => !!waiverYear.value && !!waiverReason.value.trim() && (waive.value === "Late registration fee" || (waiverValue.value ?? 0) > 0),
);
async function request() {
  const ok = await act(async () => {
    await requestWaiver({
      student_id: props.name,
      academic_year: waiverYear.value!,
      waive: waive.value,
      value: waive.value === "Late registration fee" ? undefined : (waiverValue.value ?? undefined),
      reason: waiverReason.value,
    });
    return getClearance(props.name);
  }, "Waiver requested: the Bursar decides");
  if (ok) requesting.value = false;
}
const withdrawing = ref<Waiver | null>(null);
const withdrawNote = ref("");
async function withdraw() {
  const w = withdrawing.value!;
  const ok = await act(async () => {
    await withdrawWaiver(w.name, withdrawNote.value);
    return getClearance(props.name);
  }, "Waiver withdrawn");
  if (ok) withdrawing.value = null;
}

const lifting = ref<Hold | null>(null);
const note = ref("");
async function lift() {
  if (lifting.value && (await act(() => liftHold(lifting.value!.name, note.value), "Hold lifted"))) lifting.value = null;
}
</script>

<template>
  <RecordPage :back="back" :title="data?.student_name" :subtitle="subtitle" :error="error" :outstanding="data?.reasons ?? []">
    <template #tags>
      <span v-if="data" class="state">{{ data.cleared ? "Cleared" : "Not cleared" }}</span>
    </template>
    <template v-if="data" #actions>
      <EcButton label="Request a fee waiver" variant="ghost" @click="openRequest" />
      <EcButton label="Place a hold" @click="(placing = true), (reason = '')" />
    </template>

    <template v-if="data">
      <EcPanel title="Holds" :flush="data.history.length > 0">
        <table v-if="data.history.length" class="ec-table">
          <tbody>
            <tr v-for="h in data.history" :key="h.name">
              <td>
                {{ h.reason }}
                <div class="ec-muted">
                  Placed {{ formatDate(h.placed_on) }} by {{ h.placed_by }}<template v-if="h.status === 'Lifted'"> · lifted {{ formatDate(h.lifted_on) }}: {{ h.lift_note }}</template>
                </div>
              </td>
              <td class="num">
                <EcButton v-if="h.status === 'Active'" label="Lift" size="sm" variant="ghost" @click="(lifting = h), (note = '')" />
                <span v-else class="ec-muted">Lifted</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No holds</p>
      </EcPanel>

      <EcPanel title="Invoices" :note="data.owing ? `${formatMoney(data.owing)} owing` : 'Nothing owing'" :flush="data.invoices.length > 0">
        <table v-if="data.invoices.length" class="ec-table">
          <thead>
            <tr><th>Invoice</th><th>Date</th><th class="num">Amount</th><th class="num">Owing</th></tr>
          </thead>
          <tbody>
            <tr v-for="i in data.invoices" :key="i.name">
              <td>
                {{ i.name }}
                <div v-if="i.is_return && i.remarks" class="ec-muted">{{ i.remarks }}</div>
              </td>
              <td class="ec-nowrap">{{ formatDate(i.posting_date) }}</td>
              <td class="num ec-nowrap">{{ formatMoney(i.grand_total) }}</td>
              <td class="num ec-nowrap">{{ i.outstanding_amount > 0 ? formatMoney(i.outstanding_amount) : "" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No invoices</p>
      </EcPanel>
      <EcPanel v-if="data.waivers.length" title="Fee waivers" :flush="true">
        <table class="ec-table">
          <tbody>
            <tr v-for="w in data.waivers" :key="w.name">
              <td>
                {{ w.academic_year }}: {{ waiverWhat(w, formatMoney) }}<template v-if="w.credit_note">, {{ formatMoney(w.amount) }} taken off</template>
                <div class="ec-muted">{{ w.reason }}<template v-if="w.decision_note"> · {{ w.decision_note }}</template></div>
              </td>
              <td class="num ec-nowrap">
                <StatusTag kind="waiver" :value="w.status" />
                <EcButton v-if="w.status === 'Requested' || (w.status === 'Approved' && w.can_withdraw)" label="Withdraw" size="sm" variant="ghost" @click="(withdrawing = w), (withdrawNote = '')" />
              </td>
            </tr>
          </tbody>
        </table>
      </EcPanel>
    </template>

    <template v-if="data" #aside>
      <EcPanel title="Sponsors">
        <dl v-if="data.sponsors.length" class="ec-facts stacked">
          <div v-for="s in data.sponsors" :key="`${s.sponsor_name}-${s.academic_year}`"><dt>{{ s.academic_year }}</dt><dd>{{ s.sponsor_name }}<template v-if="s.amount"> · {{ formatMoney(s.amount) }}</template></dd></div>
        </dl>
        <p v-else class="none ec-muted">None</p>
      </EcPanel>
      <EcPanel title="Contact">
        <p class="none">{{ data.student_email_id || "No email recorded" }}</p>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal :open="placing" title="Place a hold" :description="`${data?.student_name ?? ''}: blocks registration and clearance until lifted`" @update:open="(v: boolean) => (placing = v)">
    <EcField label="Reason" for="hold-reason" hint="Shown to the student and the registry">
      <Textarea id="hold-reason" v-model="reason" rows="3" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="placing = false" />
      <EcButton label="Place hold" variant="primary" :loading="busy" :disabled="!reason.trim()" @click="place" />
    </template>
  </EcModal>

  <EcModal :open="requesting" title="Request a fee waiver" :description="`${data?.student_name ?? ''}: the Bursar approves or rejects it`" size="md" @update:open="(v: boolean) => (requesting = v)">
    <div class="form">
      <EcField label="Academic year" for="waiver-year">
        <Select v-model="waiverYear" input-id="waiver-year" :options="data?.waiver_years ?? []" fluid />
      </EcField>
      <EcField label="Waive" for="waiver-kind">
        <Select v-model="waive" input-id="waiver-kind" :options="[...WAIVE_KINDS]" fluid />
      </EcField>
      <EcField v-if="waive !== 'Late registration fee'" :label="waive === 'Amount' ? 'Amount (N$)' : 'Percent of the year\'s fees'" for="waiver-value">
        <InputNumber v-model="waiverValue" input-id="waiver-value" :min="0" :max="waive === 'Amount' ? undefined : 100" :max-fraction-digits="2" fluid />
      </EcField>
      <EcField label="Reason" for="waiver-reason" hint="The Bursar decides on this">
        <Textarea id="waiver-reason" v-model="waiverReason" rows="2" auto-resize fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="requesting = false" />
      <EcButton label="Request" variant="primary" :loading="busy" :disabled="!canRequest" @click="request" />
    </template>
  </EcModal>

  <EcModal
    :open="withdrawing !== null"
    title="Withdraw the waiver"
    :description="withdrawing?.status === 'Approved' ? 'The student owes the waived amount again' : withdrawing?.reason"
    @update:open="(v: boolean) => !v && (withdrawing = null)"
  >
    <EcField label="Why it is withdrawn" for="withdraw-note">
      <Textarea id="withdraw-note" v-model="withdrawNote" rows="2" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="withdrawing = null" />
      <EcButton label="Withdraw" variant="primary" :loading="busy" :disabled="!withdrawNote.trim()" @click="withdraw" />
    </template>
  </EcModal>

  <EcModal :open="lifting !== null" title="Lift the hold" :description="lifting?.reason" @update:open="(v: boolean) => !v && (lifting = null)">
    <EcField label="Why it is lifted" for="lift-note">
      <Textarea id="lift-note" v-model="note" rows="2" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="lifting = null" />
      <EcButton label="Lift hold" variant="primary" :loading="busy" :disabled="!note.trim()" @click="lift" />
    </template>
  </EcModal>
</template>

<style scoped>
.none {
  margin: 0;
}

.form {
  display: grid;
  gap: 0.875rem;
}

.state {
  color: var(--ec-muted);
  font-size: 0.8125rem;
}
</style>
