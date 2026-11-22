<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import DatePicker from "primevue/datepicker";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { formatDate, formatMoney, fromIsoDate, toIsoDate } from "@/core/format";
import { type EnrolmentsPage, type Offer, enrol, listEnrolments } from "./api";

const toast = useToast();

type View = "waiting" | "enrolled";
const view = ref<View>("waiting");
const academicYear = ref<string | undefined>();
const search = ref("");
const page = ref<EnrolmentsPage | null>(null);
const loading = ref(false);
const loadError = ref("");

const viewOptions = computed(() => [
  { label: `Waiting to enrol (${page.value?.waiting.length ?? 0})`, value: "waiting" },
  { label: `Enrolled (${page.value?.enrolled.length ?? 0})`, value: "enrolled" },
]);

let adoptingYear = false;
async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await listEnrolments({ academic_year: academicYear.value, search: search.value.trim() || undefined });
    if (!academicYear.value && page.value.academic_year) {
      adoptingYear = true;
      academicYear.value = page.value.academic_year;
    }
  } catch (error) {
    loadError.value = error instanceof Error ? error.message : String(error);
  } finally {
    loading.value = false;
  }
}

let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(load, 300);
});
watch(academicYear, () => {
  if (adoptingYear) {
    adoptingYear = false;
    return;
  }
  void load();
});
onMounted(load);

// --- enrol ---------------------------------------------------------------------------------------------

const enrolling = ref<Offer | null>(null);
const email = ref("");
const enrollmentDay = ref<Date | null>(null);
const saving = ref(false);
const dialogError = ref("");
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const canConfirm = computed(() => EMAIL.test(email.value.trim()) && Boolean(enrollmentDay.value) && !saving.value);
const enrollmentDate = computed(() => (enrollmentDay.value ? toIsoDate(enrollmentDay.value) : ""));

function startEnrol(offer: Offer) {
  enrolling.value = offer;
  email.value = offer.email ?? "";
  enrollmentDay.value = fromIsoDate(offer.enrollment_date);
  dialogError.value = "";
}

async function confirmEnrol() {
  if (!enrolling.value || !canConfirm.value) return;
  const offer = enrolling.value;
  saving.value = true;
  dialogError.value = "";
  try {
    const result = await enrol(offer.name, email.value.trim(), enrollmentDate.value);
    enrolling.value = null;
    const fees = result.invoice ? `, invoiced ${formatMoney(result.invoice.grand_total)}` : ", not invoiced (no fees set)";
    toast.add({
      severity: "success",
      summary: `${offer.applicant} enrolled`,
      detail: `Student ${result.student}${fees}`,
      life: 6000,
    });
    await load();
  } catch (error) {
    // kept in the dialog, so the officer can correct the email and try again
    dialogError.value = error instanceof Error ? error.message : String(error);
  } finally {
    saving.value = false;
  }
}

function invoiceSeverity(status: string) {
  return status === "Paid" ? "success" : status === "Overdue" ? "danger" : status === "Partly Paid" ? "warn" : "info";
}
</script>

<template>
  <section class="registry">
    <header class="head">
      <div>
        <h1>Enrolment</h1>
        <p class="intro">Admitted applicants on your campuses. Enrolling creates the student record, their login and the year's fees.</p>
      </div>
      <div class="filters">
        <Select v-model="academicYear" :options="page?.academic_years ?? []" placeholder="Academic year" aria-label="Academic year" class="year" />
        <InputText v-model="search" placeholder="Search name or number" aria-label="Search" />
      </div>
    </header>

    <SelectButton v-model="view" :options="viewOptions" option-label="label" option-value="value" :allow-empty="false" aria-label="View" class="tabs" />

    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <DataTable v-if="view === 'waiting'" :value="page?.waiting ?? []" :loading="loading" data-key="name" striped-rows class="table">
      <template #empty><p class="empty">No admitted applicants waiting to be enrolled.</p></template>
      <Column header="Applicant">
        <template #body="{ data }">
          <div class="strong">{{ data.applicant }}</div>
          <div class="sub">
            {{ data.name }} · offered <span class="nowrap">{{ formatDate(data.decided_on) }}</span>
          </div>
        </template>
      </Column>
      <Column header="Programme offering">
        <template #body="{ data }">
          <div>{{ data.program }}</div>
          <div class="sub">{{ data.offering }} · {{ data.campus }} · {{ data.mode_of_study }}</div>
        </template>
      </Column>
      <Column header="Fees for the year">
        <template #body="{ data }">
          <span v-if="data.fees !== null" class="nowrap">{{ formatMoney(data.fees) }}</span>
          <Tag v-else severity="warn" value="No fees set" />
        </template>
      </Column>
      <Column header="">
        <template #body="{ data }">
          <div class="actions">
            <div v-if="data.needs_acceptance" class="awaiting">
              <Tag severity="warn" value="Awaiting acceptance" class="nowrap" />
              <span v-if="data.offer_deadline" class="sub nowrap">by {{ formatDate(data.offer_deadline) }}</span>
            </div>
            <Button v-else-if="page?.can_enrol" label="Enrol" size="small" @click="startEnrol(data)" />
          </div>
        </template>
      </Column>
    </DataTable>

    <DataTable v-else :value="page?.enrolled ?? []" :loading="loading" data-key="name" striped-rows class="table">
      <template #empty><p class="empty">No students enrolled from this year's applications yet.</p></template>
      <Column header="Student">
        <template #body="{ data }">
          <div class="strong">{{ data.applicant }}</div>
          <div class="sub">{{ data.student }} · {{ data.student_login }}</div>
        </template>
      </Column>
      <Column header="Programme offering">
        <template #body="{ data }">
          <div>{{ data.program }}</div>
          <div class="sub">{{ data.offering }} · {{ data.campus }}</div>
        </template>
      </Column>
      <Column header="Enrolled from">
        <template #body="{ data }"><span class="nowrap">{{ formatDate(data.enrollment_date) }}</span></template>
      </Column>
      <Column header="Fees">
        <template #body="{ data }">
          <template v-if="data.invoice">
            <div class="nowrap">{{ formatMoney(data.invoice.grand_total) }}</div>
            <Tag
              :severity="invoiceSeverity(data.invoice.status)"
              :value="data.invoice.outstanding_amount > 0 ? `${data.invoice.status}: ${formatMoney(data.invoice.outstanding_amount)} owing` : data.invoice.status"
            />
          </template>
          <span v-else class="sub">Not invoiced</span>
        </template>
      </Column>
    </DataTable>

    <Dialog
      :visible="enrolling !== null"
      modal
      :header="enrolling ? `Enrol ${enrolling.applicant}` : ''"
      :style="{ width: 'min(32rem, calc(100vw - 32px))' }"
      @update:visible="(open: boolean) => !open && (enrolling = null)"
    >
      <template v-if="enrolling">
        <p class="summary">
          {{ enrolling.program }}<br />
          <span class="sub">{{ enrolling.offering }} · {{ enrolling.campus }} · {{ enrolling.mode_of_study }}</span>
        </p>
        <div class="field">
          <label for="enrol-email">Student's email (their login)</label>
          <InputText id="enrol-email" v-model="email" type="email" autocomplete="off" fluid :invalid="Boolean(email) && !EMAIL.test(email.trim())" />
        </div>
        <div class="field">
          <label for="enrol-date">Enrolled from</label>
          <!-- DD-MM-YYYY whatever the browser's locale (AGENT.md 9) -->
          <DatePicker v-model="enrollmentDay" input-id="enrol-date" date-format="dd-mm-yy" show-icon fluid />
        </div>
        <p class="fees">
          <template v-if="enrolling.fees !== null">
            The student will be invoiced <strong>{{ formatMoney(enrolling.fees) }}</strong> for {{ enrolling.academic_year }}.
          </template>
          <template v-else>No fees are set for this offering in {{ enrolling.academic_year }}: the enrolment will not be invoiced.</template>
        </p>
        <Message v-if="dialogError" severity="error" :closable="false" role="alert">{{ dialogError }}</Message>
      </template>
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="enrolling = null" />
        <Button label="Enrol" :loading="saving" :disabled="!canConfirm" @click="confirmEnrol" />
      </template>
    </Dialog>
  </section>
</template>

<style scoped>
.head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

.intro {
  margin: 0;
  color: #6b7280;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.year {
  min-width: 9rem;
}

.tabs {
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.table {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  overflow: hidden;
}

.strong {
  font-weight: 600;
}

.awaiting {
  display: grid;
  justify-items: end;
  gap: 0.2rem;
}

.sub {
  font-size: 0.8rem;
  color: #6b7280;
}

.nowrap {
  white-space: nowrap;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.empty {
  margin: 1rem 0;
  text-align: center;
  color: #6b7280;
}

.summary {
  margin: 0 0 1rem;
}

.field {
  display: grid;
  gap: 0.4rem;
  margin-bottom: 1rem;
}

.field label {
  font-size: 0.875rem;
}

.fees {
  margin: 0 0 1rem;
}
</style>
