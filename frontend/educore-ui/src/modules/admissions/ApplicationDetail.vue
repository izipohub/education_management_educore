<script setup lang="ts">
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { formatDate, formatMoney, fromIsoDate, shortUser, toIsoDate } from "@/core/format";
import DetailPane from "@/core/ui/DetailPane.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Action, type Places, type Review, decide, extendOffer, getReview, verifyDocument, waiveFee } from "./api";

/** One application, docked beside the admissions queue: what is outstanding first, details on request */
const props = defineProps<{ name: string; places?: Places }>();
const emit = defineEmits<{ changed: [] }>();
const toast = useToast();

const review = ref<Review | null>(null);
const error = ref("");
const busy = ref(false);

async function load() {
  error.value = "";
  try {
    review.value = await getReview(props.name);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}

async function act(run: () => Promise<unknown>, message: string, reload = false) {
  busy.value = true;
  try {
    const result = await run();
    if (reload) await load();
    else review.value = result as Review;
    toast.add({ severity: "success", summary: message, life: 2500 });
    emit("changed");
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

// --- what is outstanding --------------------------------------------------------------------------------
const pendingDoc = (b: string) => b.endsWith(": verification outstanding");
const outstanding = computed(() => {
  const list = review.value?.blockers ?? [];
  const documents = list.filter(pendingDoc).length;
  return [documents ? `${documents} ${documents === 1 ? "document" : "documents"} to verify` : "", ...list.filter((b) => !pendingDoc(b))].filter(Boolean);
});
const full = computed(() => Boolean(props.places?.capacity && props.places.taken >= props.places.capacity));

// --- documents ------------------------------------------------------------------------------------------
const rejecting = ref<string | null>(null);
const rejectReason = ref("");
const verify = (doc: string) => act(() => verifyDocument(props.name, doc, "Verified"), `${doc}: verified`);
async function confirmReject() {
  if (!rejecting.value || !rejectReason.value.trim()) return;
  const doc = rejecting.value;
  if (await act(() => verifyDocument(props.name, doc, "Rejected", rejectReason.value.trim()), `${doc}: rejected`)) {
    rejecting.value = null;
    rejectReason.value = "";
  }
}
const canCheck = computed(() => Boolean(review.value?.can_review && review.value.status === "Applied"));

// --- fee and offer --------------------------------------------------------------------------------------
const waiving = ref(false);
const waiveReason = ref("");
async function confirmWaive() {
  if (!waiveReason.value.trim()) return;
  if (await act(() => waiveFee(props.name, waiveReason.value.trim()), "Fee waived")) {
    waiving.value = false;
    waiveReason.value = "";
  }
}
const extending = ref(false);
const newDeadline = ref<Date | null>(null);
function startExtend() {
  extending.value = true;
  newDeadline.value = review.value?.offer?.deadline ? fromIsoDate(review.value.offer.deadline) : null;
}
async function confirmExtend() {
  if (newDeadline.value && (await act(() => extendOffer(props.name, toIsoDate(newDeadline.value!)), "Deadline extended"))) {
    extending.value = false;
  }
}

// --- decisions ------------------------------------------------------------------------------------------
const deciding = ref<Action | null>(null);
const decisionText = ref("");
const offerChoice = ref("");
const offering = computed(() => deciding.value === "Approve");
const PAST: Record<Action, string> = { Approve: "Offer made", Reject: "Rejected", "Withdraw Offer": "Offer withdrawn", Reconsider: "Reopened" };

function start(action: Action) {
  if (action === "Reconsider") {
    void act(() => decide(props.name, action), PAST[action], true);
    return;
  }
  deciding.value = action;
  decisionText.value = "";
  offerChoice.value = review.value?.choices[0]?.offering ?? "";
}
async function confirmDecision() {
  const action = deciding.value;
  if (!action || (!offering.value && !decisionText.value.trim())) return;
  const text = decisionText.value.trim() || undefined;
  const ok = await act(
    () => (offering.value ? decide(props.name, action, undefined, text, offerChoice.value) : decide(props.name, action, text)),
    PAST[action],
    true,
  );
  if (ok) deciding.value = null;
}
const actionLabel = (action: Action) => (action === "Approve" ? "Make offer" : action);
/** why Make offer is unavailable (the sections show the details: documents to verify, the fee) */
const approveBlocked = computed(() =>
  full.value ? "All places on this offering are offered" : review.value?.ready === false ? outstanding.value.join(" · ") : "",
);

// last: it runs at once, and resets the state declared above
watch(
  () => props.name,
  () => {
    review.value = null;
    rejecting.value = null;
    waiving.value = false;
    extending.value = false;
    void load();
  },
  { immediate: true },
);
</script>

<template>
  <Message v-if="error" severity="error" :closable="false" class="error">{{ error }}</Message>
  <EcSkeleton v-else-if="!review" shape="pane" :rows="5" label="Loading the application" />

  <DetailPane
    v-else
    :title="review.applicant"
    :subtitle="[review.name, review.pathway, review.international ? 'international' : '', review.intake].filter(Boolean).join(' · ')"
  >
    <template #tags>
      <StatusTag kind="application" :value="review.status" />
    </template>


    <DetailSection v-if="review.offer" title="Offer" :collapsible="Boolean(review.offer.conditions || review.can_review)">
      <template #summary>
        <StatusTag kind="offer" :value="review.offer.status" />
        <span v-if="review.offer.status === 'Awaiting response' && review.offer.deadline" class="ec-muted">by {{ formatDate(review.offer.deadline) }}</span>
        <span v-else-if="review.offer.responded_on" class="ec-muted">{{ formatDate(review.offer.responded_on) }}</span>
      </template>
      <p v-if="review.offer.conditions">Conditions: {{ review.offer.conditions }}</p>
      <p v-if="review.offer.decline_reason">Reason given: {{ review.offer.decline_reason }}</p>
      <template v-if="review.can_review && review.offer.status === 'Awaiting response'">
        <EcButton v-if="!extending" label="Extend deadline" size="sm" variant="ghost" @click="startExtend" />
        <div v-else class="inline-form">
          <DatePicker v-model="newDeadline" date-format="dd-mm-yy" show-icon :min-date="new Date()" aria-label="New deadline" />
          <EcButton label="Save" size="sm" :disabled="!newDeadline || busy" @click="confirmExtend" />
          <EcButton label="Cancel" size="sm" variant="ghost" @click="extending = false" />
        </div>
      </template>
    </DetailSection>

    <DetailSection v-if="places?.capacity" title="Places">
      <template #summary>
        <span :class="{ danger: full }">{{ places.taken }} of {{ places.capacity }} offered</span>
        <span class="ec-muted">{{ review.choices[0]?.offering }}</span>
      </template>
    </DetailSection>

    <DetailSection title="Choices" :collapsible="review.choices.length > 1">
      <template #summary>
        <span>{{ review.choices[0]?.program }}</span>
        <StatusTag kind="eligibility" :value="review.choices[0]?.eligibility" />
        <span v-if="review.choices.length > 1" class="ec-muted">+{{ review.choices.length - 1 }}</span>
      </template>
      <template v-if="review.choices.length > 1">
        <div v-for="c in review.choices" :key="c.offering" class="line">
          <span class="grow">{{ c.rank }}. {{ c.program }} <span class="ec-muted">{{ c.offering }}</span></span>
          <StatusTag kind="eligibility" :value="c.eligibility" />
          <div v-if="c.eligibility_note" class="ec-muted full">{{ c.eligibility_note }}</div>
        </div>
      </template>
      <p v-else-if="review.choices[0]?.eligibility_note" class="ec-muted">{{ review.choices[0].eligibility_note }}</p>
    </DetailSection>

    <DetailSection v-if="review.online" title="Documents" collapsible :open="canCheck">
      <template #summary>
        <span>{{ review.documents_verified }} of {{ review.documents_required }} verified</span>
        <span v-if="review.missing_documents.length" class="danger">{{ review.missing_documents.length }} not uploaded</span>
      </template>
      <p v-for="m in review.missing_documents" :key="m" class="danger">Not uploaded: {{ m }}</p>
      <div v-for="d in review.documents" :key="d.document_type" class="doc">
        <div class="doc-row">
          <div class="grow">
            <div>{{ d.document_type }}<span v-if="!d.required" class="ec-muted"> · optional</span></div>
            <div class="ec-muted">
              <a v-if="d.file_url" :href="d.file_url" target="_blank" rel="noopener">Open file</a>
              <template v-if="d.certified_on"> · certified {{ formatDate(d.certified_on) }}</template>
              <template v-if="d.verified_by"> · {{ shortUser(d.verified_by) }}</template>
            </div>
          </div>
          <div v-if="canCheck && d.status !== 'Verified' && rejecting !== d.document_type" class="doc-actions">
            <EcButton label="Verify" size="sm" :disabled="busy" @click="verify(d.document_type)" />
            <EcButton label="Reject" size="sm" variant="quiet-danger" :disabled="busy" @click="(rejecting = d.document_type), (rejectReason = '')" />
          </div>
          <StatusTag v-else kind="document" :value="d.status" />
        </div>
        <p v-if="d.certification_problem" class="warn">{{ d.certification_problem }}</p>
        <p v-if="d.rejection_reason" class="danger">Rejected: {{ d.rejection_reason }}</p>
        <div v-if="rejecting === d.document_type" class="inline-form">
          <InputText v-model="rejectReason" placeholder="Reason, shown to the applicant" fluid size="small" :aria-label="`Reason for rejecting ${d.document_type}`" />
          <EcButton label="Reject" size="sm" variant="danger" :disabled="!rejectReason.trim() || busy" @click="confirmReject" />
          <EcButton label="Cancel" size="sm" variant="ghost" @click="rejecting = null" />
        </div>
      </div>
    </DetailSection>

    <DetailSection v-if="review.online" title="Fee" :collapsible="Boolean(review.fee.note) || (review.can_review && review.fee.status === 'Unpaid')">
      <template #summary>
        <span>{{ formatMoney(review.fee.amount) }}</span>
        <StatusTag kind="fee" :value="review.fee.status" />
        <span v-if="review.fee.paid_on" class="ec-muted">{{ formatDate(review.fee.paid_on) }}</span>
      </template>
      <p v-if="review.fee.note" class="ec-muted">{{ review.fee.note }}</p>
      <template v-if="review.can_review && review.fee.status === 'Unpaid'">
        <EcButton v-if="!waiving" label="Waive the fee" size="sm" variant="ghost" @click="waiving = true" />
        <div v-else class="inline-form">
          <InputText v-model="waiveReason" placeholder="Reason, e.g. the scheme it falls under" fluid aria-label="Reason for waiving the fee" />
          <EcButton label="Waive" size="sm" :disabled="!waiveReason.trim() || busy" @click="confirmWaive" />
          <EcButton label="Cancel" size="sm" variant="ghost" @click="waiving = false" />
        </div>
      </template>
    </DetailSection>

    <DetailSection title="Applicant" collapsible>
      <template #summary>
        <span>{{ review.personal.email }}</span>
        <span v-if="review.age !== null" class="ec-muted">{{ review.age }} years</span>
      </template>
      <dl class="facts">
        <div><dt>Date of birth</dt><dd>{{ formatDate(review.personal.date_of_birth) }}</dd></div>
        <div><dt>Gender</dt><dd>{{ review.personal.gender || "Not given" }}</dd></div>
        <div><dt>Nationality</dt><dd>{{ review.personal.nationality || "Not given" }}</dd></div>
        <div><dt>Mobile</dt><dd>{{ review.personal.mobile || "Not given" }}</dd></div>
        <div><dt>Town</dt><dd>{{ review.personal.city || "Not given" }}</dd></div>
      </dl>
    </DetailSection>

    <DetailSection v-if="review.school" title="Results" collapsible>
      <template #summary>
        <span>{{ review.school.school_name }}</span>
        <span v-if="review.points !== null" class="ec-muted">{{ review.points }} points</span>
      </template>
      <p class="ec-muted">
        Centre {{ review.school.centre_number || "not given" }} · exam no. {{ review.exam_number || "not given" }}
        ({{ review.exam_year || "year not given" }})
      </p>
      <p v-if="review.school.added_by_applicant" class="warn">Typed in by the applicant: not on the school list yet.</p>
      <table class="table">
        <tbody>
          <tr v-for="r in review.results" :key="`${r.subject}-${r.level}`">
            <td>{{ r.subject }}</td>
            <td>{{ r.level }}</td>
            <td>{{ r.grade }}</td>
            <td class="num">{{ r.points ?? "?" }}</td>
          </tr>
        </tbody>
      </table>
    </DetailSection>

    <DetailSection v-if="review.prior_qualifications.length" title="Qualifications" collapsible>
      <template #summary>
        <span>{{ review.prior_qualifications[0]!.qualification }}</span>
        <span class="ec-muted">
          NQF {{ review.prior_qualifications[0]!.nqf_level ?? "?" }}<template v-if="review.prior_qualifications[0]!.average != null"> · {{ review.prior_qualifications[0]!.average }}%</template>
        </span>
      </template>
      <div v-for="q in review.prior_qualifications" :key="q.qualification + q.institution" class="line">
        <span class="grow">{{ q.qualification }} <span class="ec-muted">{{ q.institution }}<template v-if="q.country">, {{ q.country }}</template></span></span>
        <span class="ec-muted">NQF {{ q.nqf_level ?? "?" }} · {{ q.year_completed ?? "not finished" }}<template v-if="q.average != null"> · {{ q.average }}%</template></span>
      </div>
    </DetailSection>

    <DetailSection v-if="review.employment.length" title="Work" collapsible>
      <template #summary>
        <span>{{ review.employment[0]!.position }}, {{ review.employment[0]!.employer }}</span>
        <span v-if="review.work_years" class="ec-muted">{{ review.work_years }} years</span>
      </template>
      <div v-for="job in review.employment" :key="job.employer + job.from_date" class="doc">
        <div>{{ job.position }}, {{ job.employer }}</div>
        <div class="ec-muted">{{ formatDate(job.from_date) }} to {{ job.to_date ? formatDate(job.to_date) : "now" }}<template v-if="job.duties"> · {{ job.duties }}</template></div>
      </div>
    </DetailSection>

    <DetailSection v-if="review.referees.length" title="Referees" collapsible>
      <template #summary><span>{{ review.referees.map((r) => r.full_name).join(", ") }}</span></template>
      <div v-for="r in review.referees" :key="r.email" class="doc">
        <div>{{ r.full_name }}<span class="ec-muted"><template v-if="r.position">, {{ r.position }}</template><template v-if="r.institution">, {{ r.institution }}</template></span></div>
        <div class="ec-muted"><a :href="`mailto:${r.email}`">{{ r.email }}</a><template v-if="r.phone"> · {{ r.phone }}</template></div>
      </div>
    </DetailSection>

    <DetailSection v-if="review.previous_student_number" title="Earlier studies" :summary="`Student number ${review.previous_student_number}`" />

    <template v-if="review.actions.length" #actions>
      <EcButton
        v-for="action in review.actions.filter((a) => a !== 'Approve')"
        :key="action"
        :label="action"
        :variant="action === 'Reconsider' ? 'secondary' : 'danger'"
        :disabled="busy"
        @click="start(action)"
      />
      <EcButton
        v-if="review.actions.includes('Approve')"
        label="Make offer"
        variant="primary"
        :disabled="busy || Boolean(approveBlocked)"
        :title="approveBlocked || undefined"
        @click="start('Approve')"
      />
    </template>
  </DetailPane>

  <EcModal
    :open="deciding !== null"
    :title="deciding ? `${offering ? 'Offer a place' : deciding}: ${review?.applicant}` : ''"
    :description="offering ? 'The applicant is asked to accept or decline in the portal.' : undefined"
    @update:open="(v: boolean) => !v && (deciding = null)"
  >
    <fieldset v-if="offering && (review?.choices.length ?? 0) > 1" class="choices">
      <legend class="label">Programme to offer</legend>
      <label v-for="c in review?.choices" :key="c.offering" class="choice-option">
        <input v-model="offerChoice" type="radio" name="offer-choice" :value="c.offering" />
        <span class="grow">{{ c.rank }}. {{ c.program }} <span class="ec-muted">{{ c.campus }}</span></span>
        <StatusTag kind="eligibility" :value="c.eligibility" />
      </label>
    </fieldset>
    <EcField
      :label="offering ? 'Offer conditions (optional)' : 'Reason'"
      for="decision-text"
      :hint="offering ? 'Shown in the offer letter' : 'Kept on the application'"
    >
      <Textarea id="decision-text" v-model="decisionText" rows="3" fluid auto-resize />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="deciding = null" />
      <EcButton
        :label="deciding ? actionLabel(deciding) : ''"
        :variant="offering ? 'primary' : 'danger'"
        :loading="busy"
        :disabled="!offering && !decisionText.trim()"
        @click="confirmDecision"
      />
    </template>
  </EcModal>
</template>

<style scoped>
.error {
  margin: 1rem;
}

p {
  margin: 0 0 0.4rem;
}

.line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  padding: 0.35rem 0;
}

.grow {
  flex: 1;
  min-width: 0;
}

.full {
  flex-basis: 100%;
}

.doc {
  padding: 0.5rem 0;
  border-top: 1px solid var(--ec-border-soft);
}

.doc:first-of-type {
  border-top: 0;
}

.doc-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.doc-actions {
  display: flex;
  gap: 0.25rem;
}

.inline-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-top: 0.4rem;
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(10rem, 1fr));
  gap: 0.5rem 1rem;
  margin: 0;
}

.facts dt {
  font-size: 0.75rem;
  color: var(--ec-muted);
}

.facts dd {
  margin: 0;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table td {
  padding: 0.3rem 0.4rem;
  border-top: 1px solid var(--ec-border-soft);
}

.num {
  text-align: right;
}

.danger {
  color: var(--ec-danger);
}

.warn {
  color: var(--ec-warn);
}

.label {
  font-size: 0.875rem;
}

.choices {
  display: grid;
  gap: 0.4rem;
  margin: 0 0 0.75rem;
  padding: 0;
  border: 0;
}

.choice-option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius-sm);
  cursor: pointer;
}

.choice-option input {
  accent-color: var(--ec-accent);
}
</style>
