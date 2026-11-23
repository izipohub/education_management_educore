<script setup lang="ts">
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { formatDate, formatMoney, fromIsoDate, shortUser, toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Action, type Review, decide, extendOffer, getReview, verifyDocument, waiveFee } from "./api";

/** One application on its own page: the record in panels, where it stands beside it, the decisions on top */
const props = defineProps<{ name: string }>();
const route = useRoute();
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
watch(
  () => props.name,
  () => {
    review.value = null;
    void load();
  },
  { immediate: true },
);

async function act(run: () => Promise<unknown>, message: string, reload = false) {
  busy.value = true;
  try {
    const result = await run();
    if (reload) await load();
    else review.value = result as Review;
    toast.add({ severity: "success", summary: message, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

const back = computed(() => ({ to: { name: "admissions", query: route.query }, label: "Admissions" }));

// --- where it stands --------------------------------------------------------------------------------------
const pendingDoc = (b: string) => b.endsWith(": verification outstanding");
const outstanding = computed(() => {
  const r = review.value;
  if (!r || r.status !== "Applied") return [];
  const documents = r.blockers.filter(pendingDoc).length;
  return [documents ? `${documents} ${documents === 1 ? "document" : "documents"} to verify` : "", ...r.blockers.filter((b) => !pendingDoc(b))].filter(Boolean);
});
const places = computed(() => review.value?.places ?? null);
const full = computed(() => Boolean(places.value?.capacity && places.value.taken >= places.value.capacity));
const canCheck = computed(() => Boolean(review.value?.can_review && review.value.status === "Applied"));

// --- documents ----------------------------------------------------------------------------------------------
const verify = (doc: string) => act(() => verifyDocument(props.name, doc, "Verified"), `${doc}: verified`);
const rejecting = ref<string | null>(null);
const rejectReason = ref("");
async function confirmReject() {
  const doc = rejecting.value;
  if (!doc || !rejectReason.value.trim()) return;
  if (await act(() => verifyDocument(props.name, doc, "Rejected", rejectReason.value.trim()), `${doc}: rejected`)) {
    rejecting.value = null;
    rejectReason.value = "";
  }
}

// --- fee and offer ------------------------------------------------------------------------------------------
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
  newDeadline.value = review.value?.offer?.deadline ? fromIsoDate(review.value.offer.deadline) : null;
  extending.value = true;
}
async function confirmExtend() {
  if (newDeadline.value && (await act(() => extendOffer(props.name, toIsoDate(newDeadline.value!)), "Deadline extended"))) {
    extending.value = false;
  }
}

// --- decisions ----------------------------------------------------------------------------------------------
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
/** why Make offer is unavailable (the Outstanding panel lists the same) */
const approveBlocked = computed(() => (full.value ? "All places on this offering are offered" : review.value?.ready === false ? outstanding.value.join(" · ") : ""));
const subtitle = computed(() => {
  const r = review.value;
  return r ? [r.name, r.pathway, r.international ? "International" : "", r.intake].filter(Boolean).join(" · ") : "";
});
</script>

<template>
  <RecordPage :back="back" :title="review?.applicant" :subtitle="subtitle" :error="error" :outstanding="outstanding">
    <template #tags><StatusTag v-if="review" kind="application" :value="review.status" /></template>

    <template v-if="review?.actions.length" #actions>
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

    <template v-if="review">
      <EcPanel title="Programme choices" flush>
        <table class="ec-table">
          <thead>
            <tr><th>#</th><th>Programme</th><th>Campus</th><th>Requirements</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in review.choices" :key="c.offering">
              <td class="rank">{{ c.rank }}</td>
              <td>
                {{ c.program }}
                <div class="ec-muted">{{ c.offering }}</div>
                <div v-if="c.eligibility_note" class="ec-muted">{{ c.eligibility_note }}</div>
              </td>
              <td>{{ c.campus?.replace(" Campus", "") }}</td>
              <td><StatusTag kind="eligibility" :value="c.eligibility" /></td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel v-if="review.online" title="Documents" :note="`${review.documents_verified} of ${review.documents_required} verified`" flush>
        <table class="ec-table">
          <thead>
            <tr><th>Document</th><th>Certified</th><th class="num">Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="m in review.missing_documents" :key="m">
              <td>{{ m }}</td>
              <td class="ec-muted">Not uploaded</td>
              <td class="num"><StatusTag kind="document" value="Pending" /></td>
            </tr>
            <tr v-for="d in review.documents" :key="d.document_type">
              <td>
                <a v-if="d.file_url" :href="d.file_url" target="_blank" rel="noopener">{{ d.document_type }}</a>
                <template v-else>{{ d.document_type }}</template>
                <span v-if="!d.required" class="ec-muted"> · optional</span>
                <div v-if="d.certification_problem" class="ec-muted">{{ d.certification_problem }}</div>
                <div v-if="d.rejection_reason" class="ec-muted">Rejected: {{ d.rejection_reason }}</div>
                <div v-if="d.verified_by" class="ec-muted">{{ d.status }} by {{ shortUser(d.verified_by) }}<template v-if="d.verified_on">, {{ formatDate(d.verified_on) }}</template></div>
              </td>
              <td class="ec-nowrap">{{ d.certified_on ? formatDate(d.certified_on) : "Not given" }}</td>
              <td class="num">
                <div v-if="canCheck && d.status !== 'Verified'" class="row-actions">
                  <EcButton label="Reject" size="sm" variant="quiet-danger" :disabled="busy" @click="(rejecting = d.document_type), (rejectReason = '')" />
                  <EcButton label="Verify" size="sm" :disabled="busy" @click="verify(d.document_type)" />
                </div>
                <StatusTag v-else kind="document" :value="d.status" />
              </td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel v-if="review.school" title="School results" :note="review.points !== null ? `${review.points} points` : undefined" flush>
        <p class="panel-line ec-muted">
          {{ review.school.school_name }} · centre {{ review.school.centre_number || "not given" }} · exam no. {{ review.exam_number || "not given" }}
          ({{ review.exam_year || "year not given" }})<template v-if="review.school.added_by_applicant"> · school typed in by the applicant</template>
        </p>
        <table class="ec-table">
          <thead>
            <tr><th>Subject</th><th>Level</th><th>Grade</th><th class="num">Points</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in review.results" :key="`${r.subject}-${r.level}`">
              <td>{{ r.subject }}</td>
              <td>{{ r.level }}</td>
              <td>{{ r.grade }}</td>
              <td class="num">{{ r.points ?? "?" }}</td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel v-if="review.prior_qualifications.length" title="Qualifications" flush>
        <table class="ec-table">
          <thead>
            <tr><th>Qualification</th><th>NQF</th><th>Completed</th><th class="num">Average</th></tr>
          </thead>
          <tbody>
            <tr v-for="q in review.prior_qualifications" :key="q.qualification + q.institution">
              <td>
                {{ q.qualification }}
                <div class="ec-muted">{{ q.institution }}<template v-if="q.country">, {{ q.country }}</template></div>
              </td>
              <td>{{ q.nqf_level ?? "?" }}</td>
              <td>{{ q.year_completed ?? "Not finished" }}</td>
              <td class="num">{{ q.average != null ? `${q.average}%` : "" }}</td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel v-if="review.employment.length" title="Work experience" :note="review.work_years ? `${review.work_years} years` : undefined" flush>
        <table class="ec-table">
          <thead>
            <tr><th>Position</th><th>Period</th></tr>
          </thead>
          <tbody>
            <tr v-for="job in review.employment" :key="job.employer + job.from_date">
              <td>
                {{ job.position }}, {{ job.employer }}
                <div v-if="job.duties" class="ec-muted">{{ job.duties }}</div>
              </td>
              <td class="ec-nowrap">{{ formatDate(job.from_date) }} to {{ job.to_date ? formatDate(job.to_date) : "now" }}</td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel v-if="review.referees.length" title="Referees" flush>
        <table class="ec-table">
          <tbody>
            <tr v-for="r in review.referees" :key="r.email">
              <td>
                {{ r.full_name }}
                <div class="ec-muted"><template v-if="r.position">{{ r.position }}</template><template v-if="r.institution">, {{ r.institution }}</template></div>
              </td>
              <td><a :href="`mailto:${r.email}`">{{ r.email }}</a><div v-if="r.phone" class="ec-muted">{{ r.phone }}</div></td>
            </tr>
          </tbody>
        </table>
      </EcPanel>
    </template>

    <template v-if="review" #aside>
      <EcPanel title="Summary">
        <dl class="ec-facts stacked">
          <div><dt>First choice</dt><dd>{{ review.choices[0]?.program ?? "None" }}</dd></div>
          <div v-if="places?.capacity">
            <dt>Places offered</dt>
            <dd>{{ places.taken }} of {{ places.capacity }}<template v-if="full"> · Full</template></dd>
          </div>
          <div><dt>Intake</dt><dd>{{ review.intake }}</dd></div>
          <div v-if="review.pathway"><dt>Entry pathway</dt><dd>{{ review.pathway }}</dd></div>
          <div v-if="review.submitted_on"><dt>Submitted</dt><dd>{{ formatDate(review.submitted_on) }}</dd></div>
          <div v-if="review.previous_student_number"><dt>Earlier student number</dt><dd>{{ review.previous_student_number }}</dd></div>
        </dl>
      </EcPanel>

      <EcPanel v-if="review.offer" title="Offer">
        <template #note><StatusTag kind="offer" :value="review.offer.status" /></template>
        <dl class="ec-facts stacked">
          <div v-if="review.offer.status === 'Awaiting response' && review.offer.deadline"><dt>Respond by</dt><dd>{{ formatDate(review.offer.deadline) }}</dd></div>
          <div v-if="review.offer.responded_on"><dt>Responded</dt><dd>{{ formatDate(review.offer.responded_on) }}</dd></div>
          <div v-if="review.offer.conditions"><dt>Conditions</dt><dd>{{ review.offer.conditions }}</dd></div>
          <div v-if="review.offer.decline_reason"><dt>Reason given</dt><dd>{{ review.offer.decline_reason }}</dd></div>
        </dl>
        <template v-if="review.can_review && review.offer.status === 'Awaiting response'" #footer>
          <EcButton label="Extend deadline" size="sm" variant="ghost" @click="startExtend" />
        </template>
      </EcPanel>

      <EcPanel v-if="review.online" title="Application fee">
        <template #note><StatusTag kind="fee" :value="review.fee.status" /></template>
        <dl class="ec-facts stacked">
          <div><dt>Amount</dt><dd>{{ formatMoney(review.fee.amount) }}</dd></div>
          <div v-if="review.fee.paid_on"><dt>Paid</dt><dd>{{ formatDate(review.fee.paid_on) }}</dd></div>
          <div v-if="review.fee.note"><dt>Note</dt><dd>{{ review.fee.note }}</dd></div>
        </dl>
        <template v-if="review.can_review && review.fee.status === 'Unpaid'" #footer>
          <EcButton label="Waive the fee" size="sm" variant="ghost" @click="waiving = true" />
        </template>
      </EcPanel>

      <EcPanel title="Applicant">
        <dl class="ec-facts stacked">
          <div><dt>Email</dt><dd>{{ review.personal.email }}</dd></div>
          <div><dt>Mobile</dt><dd>{{ review.personal.mobile || "Not given" }}</dd></div>
          <div>
            <dt>Date of birth</dt>
            <dd>{{ formatDate(review.personal.date_of_birth) }}<template v-if="review.age !== null"> · {{ review.age }} years</template></dd>
          </div>
          <div><dt>Gender</dt><dd>{{ review.personal.gender || "Not given" }}</dd></div>
          <div><dt>Nationality</dt><dd>{{ review.personal.nationality || "Not given" }}</dd></div>
          <div><dt>Town</dt><dd>{{ review.personal.city || "Not given" }}</dd></div>
        </dl>
      </EcPanel>
    </template>
  </RecordPage>

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
    <EcField :label="offering ? 'Offer conditions (optional)' : 'Reason'" for="decision-text" :hint="offering ? 'Shown in the offer letter' : 'Kept on the application'">
      <Textarea id="decision-text" v-model="decisionText" rows="3" fluid auto-resize />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="deciding = null" />
      <EcButton
        :label="deciding === 'Approve' ? 'Make offer' : (deciding ?? '')"
        :variant="offering ? 'primary' : 'danger'"
        :loading="busy"
        :disabled="!offering && !decisionText.trim()"
        @click="confirmDecision"
      />
    </template>
  </EcModal>

  <EcModal :open="rejecting !== null" :title="`Reject ${rejecting ?? ''}`" @update:open="(v: boolean) => !v && (rejecting = null)">
    <EcField label="Reason" for="reject-reason" hint="Shown to the applicant">
      <InputText id="reject-reason" v-model="rejectReason" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="rejecting = null" />
      <EcButton label="Reject" variant="danger" :loading="busy" :disabled="!rejectReason.trim()" @click="confirmReject" />
    </template>
  </EcModal>

  <EcModal :open="waiving" title="Waive the application fee" @update:open="(v: boolean) => (waiving = v)">
    <EcField label="Reason" for="waive-reason" hint="For example, the scheme it falls under">
      <InputText id="waive-reason" v-model="waiveReason" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="waiving = false" />
      <EcButton label="Waive" variant="primary" :loading="busy" :disabled="!waiveReason.trim()" @click="confirmWaive" />
    </template>
  </EcModal>

  <EcModal :open="extending" title="Extend the offer deadline" @update:open="(v: boolean) => (extending = v)">
    <EcField label="New deadline" for="new-deadline">
      <DatePicker v-model="newDeadline" input-id="new-deadline" date-format="dd-mm-yy" show-icon fluid :min-date="new Date()" />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="extending = false" />
      <EcButton label="Save" variant="primary" :loading="busy" :disabled="!newDeadline" @click="confirmExtend" />
    </template>
  </EcModal>
</template>

<style scoped>
.rank {
  width: 2rem;
  color: var(--ec-muted);
}

.row-actions {
  display: inline-flex;
  gap: 0.25rem;
}

.panel-line {
  margin: 0;
  padding: 0.75rem 1.25rem 0.25rem;
}

.choices {
  display: grid;
  gap: 0.4rem;
  margin: 0 0 0.75rem;
  padding: 0;
  border: 0;
}

.label {
  margin-bottom: 0.35rem;
  font-size: 0.875rem;
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

.grow {
  flex: 1;
  min-width: 0;
}
</style>
