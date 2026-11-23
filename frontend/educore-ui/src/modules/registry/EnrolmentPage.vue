<script setup lang="ts">
import { proofOfRegistrationUrl } from "@/core/documents";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { formatDate, formatMoney, fromIsoDate, toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type EnrolmentRecord, enrol, getEnrolment } from "./api";

/** One admitted applicant on its own page: registering them, or what their registration created */
const props = defineProps<{ name: string }>();
const route = useRoute();
const toast = useToast();

const record = ref<EnrolmentRecord | null>(null);
const error = ref("");
const offer = computed(() => record.value?.waiting ?? null);
const enrolled = computed(() => record.value?.enrolled ?? null);

const email = ref("");
const enrollmentDay = ref<Date | null>(null);
const saving = ref(false);
const formError = ref("");
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

async function load() {
  error.value = "";
  try {
    record.value = await getEnrolment(props.name);
    const o = record.value.waiting;
    email.value = o?.email ?? "";
    enrollmentDay.value = o ? fromIsoDate(o.enrollment_date) : null;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch(
  () => props.name,
  () => {
    record.value = null;
    void load();
  },
  { immediate: true },
);

const back = computed(() => ({ to: { name: "registrations", query: { ...route.query, group: "first-year" } }, label: "Registration · first-year students" }));
const canRegister = computed(() => Boolean(record.value?.can_enrol && offer.value && !offer.value.needs_acceptance));
/** the login is the email given on the application; only an application captured without one asks for it here */
const askEmail = computed(() => !offer.value?.email);
const ready = computed(() => canRegister.value && (!askEmail.value || EMAIL.test(email.value.trim())) && Boolean(enrollmentDay.value));
const outstanding = computed(() =>
  offer.value?.needs_acceptance
    ? [`Applicant to accept the offer${offer.value.offer_deadline ? `, by ${formatDate(offer.value.offer_deadline)}` : ""}`]
    : [],
);

async function confirmEnrol() {
  const o = offer.value;
  if (!o || !ready.value) return;
  saving.value = true;
  formError.value = "";
  try {
    const result = await enrol(o.name, askEmail.value ? email.value.trim() : undefined, toIsoDate(enrollmentDay.value!));
    const fees = result.invoice ? `, invoiced ${formatMoney(result.invoice.grand_total)}` : ", not invoiced (no fees set)";
    toast.add({ severity: "success", summary: `${o.applicant} registered`, detail: `Student ${result.student}${fees}`, life: 6000 });
    await load();
  } catch (e) {
    // kept beside the form, so the officer can correct the email and try again
    formError.value = e instanceof Error ? e.message : String(e);
  } finally {
    saving.value = false;
  }
}

const title = computed(() => offer.value?.applicant ?? enrolled.value?.applicant);
const subtitle = computed(() =>
  offer.value
    ? `${offer.value.name} · offered ${formatDate(offer.value.decided_on)}`
    : enrolled.value
      ? [enrolled.value.student, enrolled.value.name].filter(Boolean).join(" · ")
      : "",
);
</script>

<template>
  <RecordPage :back="back" :title="title" :subtitle="subtitle" :error="error" :outstanding="outstanding">
    <template #tags>
      <span v-if="offer" class="state">To register</span>
      <span v-else-if="enrolled" class="state">Registered</span>
    </template>

    <template v-if="offer">
      <EcPanel v-if="canRegister" title="Register">
        <div class="form">
          <div v-if="!askEmail" class="login">
            <span class="ec-muted">Login</span>
            <span>{{ offer.email }}</span>
            <span class="ec-muted">from the application</span>
          </div>
          <EcField
            v-else
            label="Student's email (their login)"
            for="enrol-email"
            hint="Not given on the application"
            :error="email && !EMAIL.test(email.trim()) ? 'Not a valid email address' : undefined"
          >
            <InputText id="enrol-email" v-model="email" type="email" autocomplete="off" fluid :invalid="Boolean(email) && !EMAIL.test(email.trim())" />
          </EcField>
          <EcField label="Registered from" for="enrol-date">
            <DatePicker v-model="enrollmentDay" input-id="enrol-date" date-format="dd-mm-yy" show-icon fluid />
          </EcField>
        </div>
        <Message v-if="formError" severity="error" :closable="false" role="alert" class="form-error">{{ formError }}</Message>
        <template #footer>
          <EcButton label="Register" variant="primary" :loading="saving" :disabled="!ready" @click="confirmEnrol" />
        </template>
      </EcPanel>

      <EcPanel title="Programme">
        <dl class="ec-facts">
          <div><dt>Programme</dt><dd>{{ offer.program }}</dd></div>
          <div><dt>Offering</dt><dd>{{ offer.offering }}</dd></div>
          <div><dt>Campus</dt><dd>{{ offer.campus }}</dd></div>
          <div><dt>Mode of study</dt><dd>{{ offer.mode_of_study }}</dd></div>
          <div><dt>Academic year</dt><dd>{{ offer.academic_year }}</dd></div>
        </dl>
      </EcPanel>
    </template>

    <template v-else-if="enrolled">
      <EcPanel title="Programme">
        <dl class="ec-facts">
          <div><dt>Programme</dt><dd>{{ enrolled.program }}</dd></div>
          <div><dt>Offering</dt><dd>{{ enrolled.offering }}</dd></div>
          <div><dt>Campus</dt><dd>{{ enrolled.campus }}</dd></div>
          <div><dt>Academic year</dt><dd>{{ enrolled.academic_year }}</dd></div>
          <div><dt>Registered from</dt><dd>{{ formatDate(enrolled.enrollment_date) }}</dd></div>
          <div v-if="enrolled.enrollment">
            <dt>Programme enrolment</dt>
            <dd>{{ enrolled.enrollment }} · <a :href="proofOfRegistrationUrl(enrolled.enrollment)" target="_blank" rel="noopener">Proof of registration (PDF)</a></dd>
          </div>
        </dl>
      </EcPanel>
    </template>

    <template #aside>
      <template v-if="offer">
        <EcPanel title="Summary">
          <dl class="ec-facts stacked">
            <div v-if="offer.online">
              <dt>Offer</dt>
              <dd><StatusTag kind="offer" :value="offer.offer_status" /></dd>
            </div>
            <div v-else><dt>Application</dt><dd>Paper</dd></div>
            <div><dt>Offered</dt><dd>{{ formatDate(offer.decided_on) }}</dd></div>
            <div><dt>Year's fees</dt><dd>{{ offer.fees !== null ? formatMoney(offer.fees) : "No fees set for this offering" }}</dd></div>
            <div v-if="offer.email"><dt>Email</dt><dd>{{ offer.email }}</dd></div>
          </dl>
        </EcPanel>
      </template>
      <template v-else-if="enrolled">
        <EcPanel title="Student">
          <dl class="ec-facts stacked">
            <div><dt>Student number</dt><dd>{{ enrolled.student ?? "Not created" }}</dd></div>
            <div v-if="enrolled.student_login"><dt>Login</dt><dd>{{ enrolled.student_login }}</dd></div>
          </dl>
        </EcPanel>
        <EcPanel title="Fees">
          <dl v-if="enrolled.invoice" class="ec-facts stacked">
            <div><dt>Invoiced</dt><dd>{{ formatMoney(enrolled.invoice.grand_total) }}</dd></div>
            <div><dt>Owing</dt><dd>{{ formatMoney(enrolled.invoice.outstanding_amount) }}</dd></div>
            <div><dt>Invoice</dt><dd>{{ enrolled.invoice.name }} · {{ enrolled.invoice.status }}</dd></div>
          </dl>
          <p v-else class="ec-muted none">Not invoiced</p>
        </EcPanel>
      </template>
    </template>
  </RecordPage>
</template>

<style scoped>
.state {
  color: var(--ec-muted);
  font-size: 0.8125rem;
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 16rem), 1fr));
  gap: 0.75rem 1rem;
}

.login {
  display: grid;
  align-content: start;
  gap: 0.2rem;
  font-size: 0.875rem;
}

.login .ec-muted:first-child {
  font-size: 0.8125rem;
  font-weight: 600;
}

.form-error {
  margin-top: 0.75rem;
}

.none {
  margin: 0;
}
</style>
