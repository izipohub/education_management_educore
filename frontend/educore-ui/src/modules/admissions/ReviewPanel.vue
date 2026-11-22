<script setup lang="ts">
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";
import { ref, watch } from "vue";
import { formatDate, formatMoney, shortUser } from "@/core/format";
import { type Review, getReview, verifyDocument, waiveFee } from "./api";

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

watch(
  () => props.name,
  async (name) => {
    review.value = null;
    error.value = "";
    rejecting.value = null;
    waiving.value = false;
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
          <Tag v-else severity="warn" value="Not ready yet" />
          <span class="sub">{{ review.pathway }}<template v-if="review.international"> (international)</template> · {{ review.intake }}<template v-if="review.submitted_on"> · submitted {{ formatDate(review.submitted_on) }}</template></span>
        </div>
        <ul v-if="review.blockers.length" class="blockers">
          <li v-for="b in review.blockers" :key="b">{{ b }}</li>
        </ul>
      </section>

      <section class="block">
        <h3>Applicant</h3>
        <dl class="facts">
          <div><dt>Email</dt><dd>{{ review.personal.email }}</dd></div>
          <div><dt>Date of birth</dt><dd>{{ formatDate(review.personal.date_of_birth) }}<span v-if="review.age !== null" class="sub"> · {{ review.age }} on 1 January</span></dd></div>
          <div><dt>Gender</dt><dd>{{ review.personal.gender }}</dd></div>
          <div><dt>Nationality</dt><dd>{{ review.personal.nationality }}</dd></div>
          <div><dt>Mobile</dt><dd>{{ review.personal.mobile }}</dd></div>
          <div><dt>Town</dt><dd>{{ review.personal.city }}</dd></div>
        </dl>
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
        <table class="results">
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
        <table class="results">
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
        <div v-for="job in review.employment" :key="job.employer + job.from_date" class="job">
          <strong>{{ job.position }}</strong>, {{ job.employer }}
          <span class="sub"> · {{ formatDate(job.from_date) }} to {{ job.to_date ? formatDate(job.to_date) : "now" }}</span>
          <p v-if="job.duties" class="sub">{{ job.duties }}</p>
        </div>
      </section>

      <section v-if="review.referees.length" class="block">
        <h3>Referees</h3>
        <div v-for="ref in review.referees" :key="ref.email" class="job">
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
