<script setup lang="ts">
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { formatDate, formatMoney, fromIsoDate, shortUser, toIsoDate } from "@/core/format";
import DatePicker from "primevue/datepicker";
import { type Review, extendOffer, getReview, verifyDocument, waiveFee } from "./api";

const props = defineProps<{ name: string | null }>();
const emit = defineEmits<{ close: []; changed: [] }>();
const toast = useToast();

const review = ref<Review | null>(null);
const error = ref("");
const busy = ref(false);
const rejecting = ref<string | null>(null);
const rejectReason = ref("");
const waiving = ref(false);
const waiveReason = ref("");
const extending = ref(false);
const newDeadline = ref<Date | null>(null);
/** sections shown in full; the rest show one line and "View all" */
const expanded = ref(new Set<string>());
const toggle = (section: string) => {
  const next = new Set(expanded.value);
  if (next.has(section)) next.delete(section);
  else next.add(section);
  expanded.value = next;
};
const shows = (section: string) => expanded.value.has(section);
/** e.g. "6 documents awaiting verification · Application fee outstanding" */
const blockerSummary = computed(() => {
  const list = review.value?.blockers ?? [];
  const pending = (b: string) => b.endsWith(": verification outstanding");
  const documents = list.filter(pending).length;
  return [documents ? `${documents} ${documents === 1 ? "document" : "documents"} awaiting verification` : "", ...list.filter((b) => !pending(b))]
    .filter(Boolean)
    .join(" · ");
});

watch(
  () => props.name,
  async (name) => {
    review.value = null;
    error.value = "";
    rejecting.value = null;
    waiving.value = false;
    extending.value = false;
    expanded.value = new Set();
    if (!name) return;
    try {
      review.value = await getReview(name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

async function act(run: () => Promise<Review>, message: string) {
  busy.value = true;
  try {
    review.value = await run();
    toast.add({ severity: "success", summary: message, life: 2500 });
    emit("changed");
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}

function verify(documentType: string) {
  void act(() => verifyDocument(props.name!, documentType, "Verified"), `${documentType}: verified`);
}

async function confirmReject() {
  if (!rejecting.value || !rejectReason.value.trim()) return;
  const documentType = rejecting.value;
  await act(() => verifyDocument(props.name!, documentType, "Rejected", rejectReason.value.trim()), `${documentType}: rejected`);
  rejecting.value = null;
  rejectReason.value = "";
}

function startExtend() {
  extending.value = true;
  newDeadline.value = review.value?.offer?.deadline ? fromIsoDate(review.value.offer.deadline) : null;
}
async function confirmExtend() {
  if (!newDeadline.value) return;
  await act(() => extendOffer(props.name!, toIsoDate(newDeadline.value!)), "Deadline extended");
  extending.value = false;
}
const offerSeverity = (status: string | null) =>
  status === "Accepted" ? "success" : status === "Awaiting response" ? "warn" : status === "Declined" ? "danger" : "secondary";

async function confirmWaive() {
  if (!waiveReason.value.trim()) return;
  await act(() => waiveFee(props.name!, waiveReason.value.trim()), "Fee waived");
  waiving.value = false;
  waiveReason.value = "";
}

const docSeverity = (status: string) => (status === "Verified" ? "success" : status === "Rejected" ? "danger" : "secondary");
const eligibilitySeverity = (value: string | null) =>
  value === "Meets requirements" ? "success" : value === "Does not meet requirements" ? "danger" : "warn";
const feeSeverity = (status: string | null) => (status === "Paid" || status === "Waived" ? "success" : "warn");
</script>

<template>
  <Drawer
    :visible="name !== null"
    position="right"
    :header="review ? `${review.applicant} · ${review.name}` : 'Application'"
    :pt="{ root: { style: 'width: min(42rem, 100vw)' } }"
    @update:visible="(open: boolean) => !open && emit('close')"
  >
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-else-if="!review" class="loading"><ProgressSpinner style="width: 2rem; height: 2rem" aria-label="Loading" /></div>

    <div v-else class="review">
      <section class="block">
        <div class="state">
          <Tag v-if="review.ready" severity="success" value="Ready for a decision" />
          <Tag v-else severity="warn" value="Incomplete" />
          <span class="sub">{{ review.pathway }}<template v-if="review.international"> (international)</template> · {{ review.intake }}<template v-if="review.submitted_on"> · submitted {{ formatDate(review.submitted_on) }}</template></span>
        </div>
        <p v-if="review.blockers.length > 2 && !shows('blockers')" class="blockers summary">
          {{ blockerSummary }}
          <Button label="View all" text size="small" @click="toggle('blockers')" />
        </p>
        <ul v-else-if="review.blockers.length" class="blockers">
          <li v-for="b in review.blockers" :key="b">{{ b }}</li>
        </ul>
      </section>

      <section v-if="review.offer" class="block">
        <h3>Offer</h3>
        <div class="fee">
          <Tag :severity="offerSeverity(review.offer.status)" :value="review.offer.status ?? 'Offered'" />
          <span v-if="review.offer.status === 'Awaiting response' && review.offer.deadline" class="sub">respond by {{ formatDate(review.offer.deadline) }}</span>
          <span v-else-if="review.offer.responded_on" class="sub">{{ formatDate(review.offer.responded_on) }}</span>
          <Button
            v-if="review.can_review && review.offer.status === 'Awaiting response' && !extending"
            label="Extend deadline"
            size="small"
            text
            @click="startExtend"
          />
        </div>
        <div v-if="extending" class="inline-form">
          <DatePicker v-model="newDeadline" date-format="dd-mm-yy" show-icon :min-date="new Date()" aria-label="New deadline" />
          <Button label="Save" size="small" :disabled="!newDeadline || busy" @click="confirmExtend" />
          <Button label="Cancel" size="small" text @click="extending = false" />
        </div>
        <p v-if="review.offer.conditions" class="sub">Conditions: {{ review.offer.conditions }}</p>
        <p v-if="review.offer.decline_reason" class="sub">Reason given: {{ review.offer.decline_reason }}</p>
      </section>

      <section class="block">
        <h3>Applicant</h3>
        <dl class="facts">
          <div><dt>Email</dt><dd>{{ review.personal.email }}</dd></div>
          <div><dt>Date of birth</dt><dd>{{ formatDate(review.personal.date_of_birth) }}<span v-if="review.age !== null" class="sub"> · {{ review.age }} on 1 January</span></dd></div>
          <template v-if="shows('applicant')">
            <div><dt>Gender</dt><dd>{{ review.personal.gender }}</dd></div>
            <div><dt>Nationality</dt><dd>{{ review.personal.nationality }}</dd></div>
            <div><dt>Mobile</dt><dd>{{ review.personal.mobile }}</dd></div>
            <div><dt>Town</dt><dd>{{ review.personal.city }}</dd></div>
          </template>
        </dl>
        <Button :label="shows('applicant') ? 'Hide details' : 'Show details'" text size="small" @click="toggle('applicant')" />
      </section>

      <section v-if="review.school" class="block">
        <h3>School and results <span v-if="review.points !== null" class="sub">· {{ review.points }} points</span></h3>
        <p>
          {{ review.school.school_name }}<template v-if="review.school.town">, {{ review.school.town }}</template>
          <span class="sub"> · centre {{ review.school.centre_number || "—" }} · exam no. {{ review.exam_number || "—" }} ({{ review.exam_year || "—" }})</span>
        </p>
        <Message v-if="review.school.added_by_applicant" severity="warn" :closable="false">
          The applicant typed this school in: it is not on the school list yet.
        </Message>
        <p class="sub">
          {{ review.results.length }} subjects
          <Button :label="shows('results') ? 'Hide' : `View all (${review.results.length})`" text size="small" @click="toggle('results')" />
        </p>
        <table v-if="shows('results')" class="results">
          <tbody>
            <tr v-for="r in review.results" :key="`${r.subject}-${r.level}`">
              <td>{{ r.subject }}</td>
              <td>{{ r.level }}</td>
              <td>{{ r.grade }}</td>
              <td class="num">{{ r.points ?? "?" }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="review.previous_student_number" class="block">
        <h3>Earlier studies here</h3>
        <p>Student number {{ review.previous_student_number }}</p>
      </section>

      <section v-if="review.prior_qualifications.length" class="block">
        <h3>Qualifications after school</h3>
        <p>
          {{ review.prior_qualifications[0]!.qualification }}
          <span class="sub">
            · {{ review.prior_qualifications[0]!.nqf_level ? `NQF ${review.prior_qualifications[0]!.nqf_level}` : "NQF ?" }}
            <template v-if="review.prior_qualifications[0]!.average != null"> · {{ review.prior_qualifications[0]!.average }}%</template>
          </span>
          <Button :label="shows('prior') ? 'Hide' : `View all (${review.prior_qualifications.length})`" text size="small" @click="toggle('prior')" />
        </p>
        <table v-if="shows('prior')" class="results">
          <tbody>
            <tr v-for="q in review.prior_qualifications" :key="q.qualification + q.institution">
              <td>{{ q.qualification }}<br /><span class="sub">{{ q.institution }}<template v-if="q.country">, {{ q.country }}</template></span></td>
              <td>{{ q.nqf_level ? `NQF ${q.nqf_level}` : "NQF ?" }}</td>
              <td>{{ q.year_completed ?? "not finished" }}</td>
              <td class="num">{{ q.average != null ? `${q.average}%` : "" }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section v-if="review.employment.length" class="block">
        <h3>Work <span v-if="review.work_years" class="sub">· {{ review.work_years }} years</span></h3>
        <p>
          {{ review.employment[0]!.position }}, {{ review.employment[0]!.employer }}
          <Button :label="shows('work') ? 'Hide' : `View all (${review.employment.length})`" text size="small" @click="toggle('work')" />
        </p>
        <div v-for="job in shows('work') ? review.employment : []" :key="job.employer + job.from_date" class="job">
          <strong>{{ job.position }}</strong>, {{ job.employer }}
          <span class="sub"> · {{ formatDate(job.from_date) }} to {{ job.to_date ? formatDate(job.to_date) : "now" }}</span>
          <p v-if="job.duties" class="sub">{{ job.duties }}</p>
        </div>
      </section>

      <section v-if="review.referees.length" class="block">
        <h3>Referees</h3>
        <p>
          {{ review.referees.map((r) => r.full_name).join(", ") }}
          <Button :label="shows('referees') ? 'Hide' : 'Contact details'" text size="small" @click="toggle('referees')" />
        </p>
        <div v-for="ref in shows('referees') ? review.referees : []" :key="ref.email" class="job">
          <strong>{{ ref.full_name }}</strong><template v-if="ref.position">, {{ ref.position }}</template><template v-if="ref.institution">, {{ ref.institution }}</template>
          <p class="sub"><a :href="`mailto:${ref.email}`">{{ ref.email }}</a><template v-if="ref.phone"> · {{ ref.phone }}</template></p>
        </div>
      </section>

      <section class="block">
        <h3>Choices</h3>
        <div v-for="c in review.choices" :key="c.offering" class="choice">
          <span>{{ c.rank }}. {{ c.program }} <span class="sub">({{ c.offering }})</span></span>
          <Tag :severity="eligibilitySeverity(c.eligibility)" :value="c.eligibility ?? 'Not assessed'" />
          <span class="sub">{{ c.eligibility_note }}</span>
        </div>
      </section>

      <section class="block">
        <h3>Documents <span class="sub">· {{ review.documents_verified }} of {{ review.documents_required }} required verified</span></h3>
        <p v-for="missing in review.missing_documents" :key="missing" class="missing">Not uploaded: {{ missing }}</p>
        <article v-for="d in review.documents" :key="d.document_type" class="document">
          <div class="doc-head">
            <strong>{{ d.document_type }}</strong>
            <Tag :severity="docSeverity(d.status)" :value="d.status" />
            <Tag v-if="!d.required" severity="secondary" value="Optional" />
          </div>
          <p class="sub">
            <a v-if="d.file_url" :href="d.file_url" target="_blank" rel="noopener">Open {{ d.file_name }}</a>
            <template v-if="d.certified_on"> · certified {{ formatDate(d.certified_on) }}</template>
            <template v-if="d.verified_by"> · checked by {{ shortUser(d.verified_by) }}</template>
          </p>
          <Message v-if="d.certification_problem" severity="warn" :closable="false">{{ d.certification_problem }}</Message>
          <p v-if="d.rejection_reason" class="reason">Rejected: {{ d.rejection_reason }}</p>
          <div v-if="review.can_review && review.status === 'Applied'" class="doc-actions">
            <Button label="Verify" size="small" :disabled="busy || d.status === 'Verified'" @click="verify(d.document_type)" />
            <Button label="Reject" size="small" severity="danger" outlined :disabled="busy" @click="rejecting = d.document_type" />
          </div>
          <div v-if="rejecting === d.document_type" class="inline-form">
            <InputText v-model="rejectReason" placeholder="Why? The applicant sees this" fluid :aria-label="`Reason for rejecting ${d.document_type}`" />
            <Button label="Reject" size="small" severity="danger" :disabled="!rejectReason.trim() || busy" @click="confirmReject" />
            <Button label="Cancel" size="small" text @click="rejecting = null" />
          </div>
        </article>
      </section>

      <section v-if="review.online" class="block">
        <h3>Application fee</h3>
        <div class="fee">
          <span>{{ formatMoney(review.fee.amount) }}</span>
          <Tag :severity="feeSeverity(review.fee.status)" :value="review.fee.status ?? 'Unpaid'" />
          <span v-if="review.fee.paid_on" class="sub">paid {{ formatDate(review.fee.paid_on) }} · {{ review.fee.voucher }}</span>
        </div>
        <p v-if="review.fee.note" class="sub note">{{ review.fee.note }}</p>
        <template v-if="review.can_review && review.fee.status === 'Unpaid'">
          <Button v-if="!waiving" label="Waive the fee" size="small" text @click="waiving = true" />
          <div v-else class="inline-form">
            <InputText v-model="waiveReason" placeholder="Reason, e.g. the scheme it falls under" fluid aria-label="Reason for waiving the fee" />
            <Button label="Waive" size="small" :disabled="!waiveReason.trim() || busy" @click="confirmWaive" />
            <Button label="Cancel" size="small" text @click="waiving = false" />
          </div>
        </template>
      </section>
    </div>
  </Drawer>
</template>

<style scoped>
.loading {
  display: flex;
  justify-content: center;
  padding: 2rem;
}

.review {
  display: grid;
  gap: 1.25rem;
}

h3 {
  margin: 0 0 0.5rem;
  font-size: 0.95rem;
}

.sub {
  font-size: 0.8rem;
  font-weight: 400;
  color: #6b7280;
}

p {
  margin: 0 0 0.4rem;
}

.state,
.choice,
.doc-head,
.fee,
.doc-actions,
.inline-form {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.blockers.summary {
  padding-left: 0;
}

.blockers {
  margin: 0.5rem 0 0;
  padding-left: 1.1rem;
  color: #b45309;
  font-size: 0.9rem;
}

.facts {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem 1rem;
  margin: 0;
}

.facts dt {
  font-size: 0.75rem;
  color: #6b7280;
}

.facts dd {
  margin: 0;
}

.results {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.results td {
  padding: 0.25rem 0.4rem;
  border-bottom: 1px solid #f3f4f6;
}

.num {
  text-align: right;
}

.choice,
.job {
  margin-bottom: 0.4rem;
}

.document {
  padding: 0.75rem 0;
  border-top: 1px solid #f3f4f6;
}

.doc-actions,
.inline-form {
  margin-top: 0.4rem;
}

.reason,
.missing {
  color: #b91c1c;
  font-size: 0.9rem;
}

.note {
  margin-top: 0.4rem;
}
</style>
