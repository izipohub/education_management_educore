<script setup lang="ts">
import { Paperclip } from "@lucide/vue";
import DatePicker from "primevue/datepicker";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, reactive, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { formatDate, formatMoney, toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import {
  type DisciplinaryCase,
  MINOR_SANCTIONS,
  SANCTIONS,
  decideAppeal,
  decideCase,
  dismissCase,
  evidenceUrl,
  getCase,
  investigateCase,
  scheduleHearing,
} from "./discipline";

/**
 * One disciplinary case: the report, the investigation, the hearing, the decision and any appeal, with the next step
 * for Student Affairs (look into it, dismiss, decide a minor case, send it to a hearing, record the committee's
 * decision) or the Registrar (decide the appeal). Confidential.
 */
const props = defineProps<{ name: string }>();
const route = useRoute();
const toast = useToast();
const c = ref<DisciplinaryCase | null>(null);
const error = ref("");
const busy = ref(false);

watch(
  () => props.name,
  async () => {
    try {
      c.value = await getCase(props.name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);
const subtitle = computed(() => (c.value ? [c.value.student, c.value.campus?.replace(" Campus", ""), `incident ${formatDate(c.value.incident_date)}`].filter(Boolean).join(" · ") : ""));
const handling = computed(() => Boolean(c.value?.can_handle));

async function act(run: () => Promise<DisciplinaryCase>, done: string) {
  busy.value = true;
  try {
    c.value = await run();
    toast.add({ severity: "success", summary: done, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not done", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

// dismissing: no case to answer
const dismissing = ref(false);
const dismissNote = ref("");
async function confirmDismiss() {
  if (await act(() => dismissCase(props.name, dismissNote.value.trim()), "Dismissed")) dismissing.value = false;
}

// the hearing (serious)
const hearing = reactive({ open: false, charge: "", on: null as Date | null, venue: "", committee: "", note: "" });
function openHearing() {
  Object.assign(hearing, {
    open: true,
    charge: c.value?.charge ?? "",
    on: c.value?.hearing_on ? new Date(c.value.hearing_on.replace(" ", "T")) : null,
    venue: c.value?.hearing_venue ?? "",
    committee: c.value?.committee ?? "",
    note: c.value?.investigation_note ?? "",
  });
}
const hearingReady = computed(() => Boolean(hearing.charge.trim() && hearing.on && hearing.venue.trim()));
function stamp(d: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${toIsoDate(d)} ${pad(d.getHours())}:${pad(d.getMinutes())}:00`;
}
async function confirmHearing() {
  const ok = await act(
    () => scheduleHearing(props.name, { charge: hearing.charge.trim(), hearing_on: stamp(hearing.on!), venue: hearing.venue.trim(), committee: hearing.committee.trim(), note: hearing.note.trim() }),
    "Hearing set; the student is told",
  );
  if (ok) hearing.open = false;
}

// the decision: minor (Student Affairs) or after the hearing (the committee's, recorded)
const decision = reactive({ open: false, finding: "Responsible", sanction: null as string | null, fine: 0, from: null as Date | null, until: null as Date | null, reasons: "", record: "" });
const afterHearing = computed(() => c.value?.status === "Hearing");
const sanctionOptions = computed(() => (afterHearing.value ? SANCTIONS : MINOR_SANCTIONS));
function openDecision() {
  Object.assign(decision, { open: true, finding: "Responsible", sanction: null, fine: 0, from: new Date(), until: null, reasons: "", record: c.value?.hearing_note ?? "" });
}
const decisionReady = computed(
  () =>
    Boolean(decision.reasons.trim()) &&
    (decision.finding === "Not responsible" ||
      (Boolean(decision.sanction) && (decision.sanction !== "Fine" || decision.fine > 0) && (decision.sanction !== "Suspension" || Boolean(decision.from && decision.until)))),
);
async function confirmDecision() {
  const ok = await act(
    () =>
      decideCase(props.name, {
        finding: decision.finding,
        reasons: decision.reasons.trim(),
        sanction: decision.finding === "Responsible" ? decision.sanction : null,
        fine: decision.fine,
        suspended_from: decision.from ? toIsoDate(decision.from) : null,
        suspended_until: decision.until ? toIsoDate(decision.until) : null,
        hearing_note: decision.record.trim(),
      }),
    "Decided; the student is told",
  );
  if (ok) decision.open = false;
}

// the appeal (Registrar)
const appeal = reactive({ open: false, outcome: "Upheld", sanction: null as string | null, fine: 0, from: null as Date | null, until: null as Date | null, note: "" });
const appealReady = computed(
  () =>
    Boolean(appeal.note.trim()) &&
    (appeal.outcome !== "Changed" || (Boolean(appeal.sanction) && (appeal.sanction !== "Fine" || appeal.fine > 0) && (appeal.sanction !== "Suspension" || Boolean(appeal.from && appeal.until)))),
);
async function confirmAppeal() {
  const ok = await act(
    () =>
      decideAppeal(props.name, {
        outcome: appeal.outcome,
        note: appeal.note.trim(),
        sanction: appeal.outcome === "Changed" ? appeal.sanction : null,
        fine: appeal.fine,
        suspended_from: appeal.from ? toIsoDate(appeal.from) : null,
        suspended_until: appeal.until ? toIsoDate(appeal.until) : null,
      }),
    "Appeal decided; the student is told",
  );
  if (ok) appeal.open = false;
}
const findings = [
  { value: "Responsible", label: "Responsible" },
  { value: "Not responsible", label: "Not responsible" },
];
const outcomes = [
  { value: "Upheld", label: "Upheld" },
  { value: "Changed", label: "Changed" },
  { value: "Overturned", label: "Overturned" },
];
</script>

<template>
  <RecordPage :back="{ to: { name: 'discipline', query: route.query }, label: 'Discipline' }" :title="c?.student_name" :subtitle="subtitle" :error="error">
    <template v-if="c" #tags>
      <StatusTag kind="discipline" :value="c.status" />
    </template>
    <template v-if="c" #actions>
      <template v-if="handling && c.status === 'Reported'">
        <EcButton label="Dismiss" variant="ghost" :disabled="busy" @click="(dismissing = true), (dismissNote = '')" />
        <EcButton label="Look into it" variant="primary" :loading="busy" @click="act(() => investigateCase(name), 'Yours to investigate')" />
      </template>
      <template v-else-if="handling && c.status === 'Investigating'">
        <EcButton label="Dismiss" variant="ghost" :disabled="busy" @click="(dismissing = true), (dismissNote = '')" />
        <EcButton label="Send to a hearing" :disabled="busy" @click="openHearing" />
        <EcButton label="Decide (minor)" variant="primary" :disabled="busy" @click="openDecision" />
      </template>
      <template v-else-if="handling && c.status === 'Hearing'">
        <EcButton label="Change the hearing" variant="ghost" :disabled="busy" @click="openHearing" />
        <EcButton label="Record the decision" variant="primary" :disabled="busy" @click="openDecision" />
      </template>
      <EcButton v-else-if="c.can_decide_appeal" label="Decide the appeal" variant="primary" :disabled="busy" @click="Object.assign(appeal, { open: true, outcome: 'Upheld', sanction: null, fine: 0, from: new Date(), until: null, note: '' })" />
    </template>

    <template v-if="c">
      <EcPanel title="Report" :note="`${c.reported_by ?? ''} · ${formatDate(c.reported_on)}`">
        <p class="text">{{ c.incident }}</p>
        <a v-if="c.evidence" :href="evidenceUrl(c.name)" class="doc" target="_blank" rel="noopener"><Paperclip :size="13" /> Evidence</a>
      </EcPanel>

      <EcPanel v-if="c.investigation_note || c.investigated_by" title="Investigation" :note="c.investigated_by ?? undefined">
        <p class="text">{{ c.investigation_note || "Under way" }}</p>
      </EcPanel>

      <EcPanel v-if="c.charge" title="Hearing" :note="c.hearing_on ? `${formatDate(c.hearing_on)} ${c.hearing_on.slice(11, 16)} · ${c.hearing_venue}` : undefined">
        <dl class="ec-facts stacked">
          <div><dt>Charge</dt><dd>{{ c.charge }}</dd></div>
          <div v-if="c.committee"><dt>Committee</dt><dd>{{ c.committee }}</dd></div>
          <div v-if="c.hearing_note"><dt>Record of the hearing</dt><dd class="text">{{ c.hearing_note }}</dd></div>
        </dl>
      </EcPanel>

      <EcPanel v-if="c.outcome" title="Decision" :note="`${c.level ?? ''} · ${c.decided_by ?? ''} · ${formatDate(c.decided_on)}`">
        <p class="outcome">{{ c.outcome }}</p>
        <p class="text">{{ c.decision_note }}</p>
        <p v-if="c.fine" class="ec-muted small">Fine {{ formatMoney(c.fine) }} · {{ c.fine_unpaid ? "not paid" : "paid" }}</p>
        <p v-if="c.appeal_until && c.status === 'Decided'" class="ec-muted small">The student may appeal until {{ formatDate(c.appeal_until) }}</p>
      </EcPanel>

      <EcPanel v-if="c.appeal_reason" title="Appeal" :note="formatDate(c.appealed_on)">
        <p class="text">{{ c.appeal_reason }}</p>
        <p v-if="c.appeal_outcome" class="appeal-outcome"><strong>{{ c.appeal_outcome }}</strong> · {{ c.appeal_decided_by }}: {{ c.appeal_note }}</p>
      </EcPanel>
    </template>

    <template v-if="c" #aside>
      <EcPanel title="The student">
        <dl class="ec-facts stacked">
          <div><dt>Student number</dt><dd>{{ c.student }}</dd></div>
          <div><dt>Campus</dt><dd>{{ c.campus }}</dd></div>
          <div><dt>Earlier cases found responsible</dt><dd>{{ c.earlier || "None" }}</dd></div>
        </dl>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal v-model:open="dismissing" title="Dismiss the case" description="No case to answer. The student was never told of it">
    <EcField label="Why" for="dismiss-note">
      <Textarea id="dismiss-note" v-model="dismissNote" rows="3" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="dismissing = false" />
      <EcButton label="Dismiss" variant="primary" :loading="busy" :disabled="!dismissNote.trim()" @click="confirmDismiss" />
    </template>
  </EcModal>

  <EcModal v-model:open="hearing.open" title="Disciplinary hearing" description="A serious case, to the committee. The student is emailed the charge and the hearing" size="md">
    <div class="form">
      <EcField label="Charge" for="h-charge" hint="As the student is told, e.g. cheating in a test (rule 4.2)">
        <Textarea id="h-charge" v-model="hearing.charge" rows="2" auto-resize fluid />
      </EcField>
      <div class="pair">
        <EcField label="Date and time" for="h-on">
          <DatePicker v-model="hearing.on" input-id="h-on" show-time hour-format="24" date-format="dd-mm-yy" :min-date="new Date()" fluid />
        </EcField>
        <EcField label="Venue" for="h-venue">
          <InputText id="h-venue" v-model="hearing.venue" fluid />
        </EcField>
      </div>
      <EcField label="Committee" for="h-committee" hint="Who sits on it">
        <InputText id="h-committee" v-model="hearing.committee" fluid />
      </EcField>
      <EcField label="Investigation" for="h-note" hint="What Student Affairs found, for the committee">
        <Textarea id="h-note" v-model="hearing.note" rows="3" auto-resize fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="hearing.open = false" />
      <EcButton label="Set the hearing" variant="primary" :loading="busy" :disabled="!hearingReady" @click="confirmHearing" />
    </template>
  </EcModal>

  <EcModal
    v-model:open="decision.open"
    :title="afterHearing ? 'The committee\'s decision' : 'Decide a minor case'"
    :description="afterHearing ? 'Recorded for the committee; the student is told and may appeal' : 'A warning, a written warning or a fine; a suspension or an expulsion needs a hearing'"
    size="md"
  >
    <div class="form">
      <EcSegmented v-model="decision.finding" :options="findings" label="Finding" />
      <template v-if="decision.finding === 'Responsible'">
        <EcField label="Sanction" for="d-sanction">
          <Select v-model="decision.sanction" input-id="d-sanction" :options="sanctionOptions" placeholder="Choose" aria-label="Sanction" fluid />
        </EcField>
        <EcField v-if="decision.sanction === 'Fine'" label="Fine" for="d-fine" hint="Invoiced to the student's fee account">
          <InputNumber v-model="decision.fine" input-id="d-fine" :min="0" prefix="N$ " :min-fraction-digits="2" fluid />
        </EcField>
        <div v-if="decision.sanction === 'Suspension'" class="pair">
          <EcField label="From" for="d-from"><DatePicker v-model="decision.from" input-id="d-from" date-format="dd-mm-yy" fluid /></EcField>
          <EcField label="Until" for="d-until"><DatePicker v-model="decision.until" input-id="d-until" date-format="dd-mm-yy" :min-date="decision.from ?? undefined" fluid /></EcField>
        </div>
        <p v-if="decision.sanction === 'Suspension' || decision.sanction === 'Expulsion'" class="ec-muted small">The student cannot register while it lasts.</p>
      </template>
      <EcField label="Reasons" for="d-reasons" hint="Sent to the student">
        <Textarea id="d-reasons" v-model="decision.reasons" rows="3" auto-resize fluid />
      </EcField>
      <EcField v-if="afterHearing" label="Record of the hearing" for="d-record">
        <Textarea id="d-record" v-model="decision.record" rows="3" auto-resize fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="decision.open = false" />
      <EcButton label="Decide" variant="primary" :loading="busy" :disabled="!decisionReady" @click="confirmDecision" />
    </template>
  </EcModal>

  <EcModal v-model:open="appeal.open" title="Decide the appeal" :description="c?.appeal_reason ?? undefined" size="md">
    <div class="form">
      <EcSegmented v-model="appeal.outcome" :options="outcomes" label="Outcome" />
      <template v-if="appeal.outcome === 'Changed'">
        <EcField label="New sanction" for="a-sanction">
          <Select v-model="appeal.sanction" input-id="a-sanction" :options="SANCTIONS" placeholder="Choose" aria-label="New sanction" fluid />
        </EcField>
        <EcField v-if="appeal.sanction === 'Fine'" label="Fine" for="a-fine">
          <InputNumber v-model="appeal.fine" input-id="a-fine" :min="0" prefix="N$ " :min-fraction-digits="2" fluid />
        </EcField>
        <div v-if="appeal.sanction === 'Suspension'" class="pair">
          <EcField label="From" for="a-from"><DatePicker v-model="appeal.from" input-id="a-from" date-format="dd-mm-yy" fluid /></EcField>
          <EcField label="Until" for="a-until"><DatePicker v-model="appeal.until" input-id="a-until" date-format="dd-mm-yy" fluid /></EcField>
        </div>
      </template>
      <p v-if="appeal.outcome !== 'Upheld' && c?.fine_unpaid" class="ec-muted small">The unpaid fine is cancelled.</p>
      <EcField label="Reasons" for="a-note" hint="Sent to the student">
        <Textarea id="a-note" v-model="appeal.note" rows="3" auto-resize fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="appeal.open = false" />
      <EcButton label="Decide" variant="primary" :loading="busy" :disabled="!appealReady" @click="confirmAppeal" />
    </template>
  </EcModal>
</template>

<style scoped>
.text {
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
  margin: 0 0 0.4rem;
  font-weight: 600;
}

.small {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
}

.appeal-outcome {
  margin: 0.75rem 0 0;
  padding-top: 0.75rem;
  border-top: 1px solid var(--ec-border-soft);
}

.form {
  display: grid;
  gap: 0.75rem;
}

.pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
</style>
