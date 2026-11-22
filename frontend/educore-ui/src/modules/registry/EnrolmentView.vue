<script setup lang="ts">
import { Search } from "@lucide/vue";
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { formatDate, formatMoney, fromIsoDate, toIsoDate } from "@/core/format";
import DetailPane from "@/core/ui/DetailPane.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SplitView from "@/core/ui/SplitView.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Enrolled, type EnrolmentsPage, type Offer, enrol, listEnrolments } from "./api";

const toast = useToast();

type View = "waiting" | "enrolled";
const view = ref<View>("waiting");
const academicYear = ref<string | undefined>();
const search = ref("");
const page = ref<EnrolmentsPage | null>(null);
const loading = ref(false);
const loadError = ref("");
const selected = ref<string | null>(null);

const viewOptions = computed(() => [
  { label: `To enrol ${page.value?.waiting.length ?? 0}`, value: "waiting" },
  { label: `Enrolled ${page.value?.enrolled.length ?? 0}`, value: "enrolled" },
]);
const items = computed(() => ((view.value === "waiting" ? page.value?.waiting : page.value?.enrolled) ?? []) as unknown as Record<string, unknown>[]);
const offer = computed(() => (view.value === "waiting" ? (page.value?.waiting.find((o) => o.name === selected.value) ?? null) : null));
const enrolled = computed(() => (view.value === "enrolled" ? (page.value?.enrolled.find((e) => e.name === selected.value) ?? null) : null));
const asOffer = (item: Record<string, unknown>) => item as unknown as Offer;
const asEnrolled = (item: Record<string, unknown>) => item as unknown as Enrolled;

function keepSelection() {
  if (!items.value.some((i) => i.name === selected.value)) selected.value = (items.value[0]?.name as string) ?? null;
}

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
    keepSelection();
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
watch(view, keepSelection);
onMounted(load);

// --- enrolling the selected applicant ---------------------------------------------------------------------
const email = ref("");
const enrollmentDay = ref<Date | null>(null);
const saving = ref(false);
const formError = ref("");
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
watch(
  offer,
  (o) => {
    email.value = o?.email ?? "";
    enrollmentDay.value = o ? fromIsoDate(o.enrollment_date) : null;
    formError.value = "";
  },
  { immediate: true },
);
const canEnrol = computed(
  () => Boolean(page.value?.can_enrol && offer.value && !offer.value.needs_acceptance && EMAIL.test(email.value.trim()) && enrollmentDay.value),
);

async function confirmEnrol() {
  const o = offer.value;
  if (!o || !canEnrol.value) return;
  saving.value = true;
  formError.value = "";
  try {
    const result = await enrol(o.name, email.value.trim(), toIsoDate(enrollmentDay.value!));
    const fees = result.invoice ? `, invoiced ${formatMoney(result.invoice.grand_total)}` : ", not invoiced (no fees set)";
    toast.add({ severity: "success", summary: `${o.applicant} enrolled`, detail: `Student ${result.student}${fees}`, life: 6000 });
    await load();
  } catch (error) {
    // kept beside the form, so the officer can correct the email and try again
    formError.value = error instanceof Error ? error.message : String(error);
  } finally {
    saving.value = false;
  }
}

const invoiceSeverity = (status: string) => (status === "Paid" ? "success" : status === "Overdue" ? "danger" : status === "Partly Paid" ? "warn" : "info");
</script>

<template>
  <PageHeader title="Enrolment" subtitle="Admitted applicants on your campuses. Enrolling creates the student, their login and the year's fees.">
    <SelectButton v-model="view" :options="viewOptions" option-label="label" option-value="value" :allow-empty="false" aria-label="View" />
    <Select v-model="academicYear" :options="page?.academic_years ?? []" placeholder="Year" aria-label="Academic year" class="year" />
  </PageHeader>

  <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

  <SplitView
    v-model:selected="selected"
    :items="items"
    item-key="name"
    :loading="loading"
    list-label="Applicants"
    :empty-title="view === 'waiting' ? 'Nobody waiting to enrol' : 'Nobody enrolled yet'"
    placeholder="Select an applicant"
  >
    <template #filters>
      <IconField class="search">
        <InputIcon><Search :size="15" /></InputIcon>
        <InputText v-model="search" placeholder="Search name or number" aria-label="Search" fluid size="small" />
      </IconField>
    </template>

    <template #item="{ item }">
      <div class="item">
        <div class="item-top">
          <span class="who">{{ asOffer(item).applicant }}</span>
          <span class="ec-muted ec-nowrap">{{ asOffer(item).offering }}</span>
        </div>
        <div class="item-bottom">
          <template v-if="view === 'waiting'">
            <span class="ec-muted">Offered {{ formatDate(asOffer(item).decided_on) }}</span>
            <StatusTag v-if="asOffer(item).needs_acceptance" kind="offer" :value="asOffer(item).offer_status" />
          </template>
          <template v-else>
            <span class="ec-muted">{{ asEnrolled(item).student }}</span>
            <Tag v-if="asEnrolled(item).invoice" :severity="invoiceSeverity(asEnrolled(item).invoice!.status)" :value="asEnrolled(item).invoice!.status" class="small-tag" />
          </template>
        </div>
      </div>
    </template>

    <template #detail>
      <DetailPane v-if="offer" :title="offer.applicant" :subtitle="`${offer.name} · offered ${formatDate(offer.decided_on)}`">
        <template #tags><StatusTag v-if="offer.online" kind="offer" :value="offer.offer_status" /></template>
        <template v-if="offer.needs_acceptance" #notice>
          <div class="notice">Waiting for the applicant to accept<template v-if="offer.offer_deadline">, by {{ formatDate(offer.offer_deadline) }}</template>.</div>
        </template>

        <DetailSection title="Programme" :summary="offer.program">
          <p class="ec-muted">{{ offer.offering }} · {{ offer.campus }} · {{ offer.mode_of_study }} · {{ offer.academic_year }}</p>
        </DetailSection>
        <DetailSection title="Fees" :summary="offer.fees !== null ? formatMoney(offer.fees) : 'No fees set for this offering'" />
        <DetailSection v-if="page?.can_enrol && !offer.needs_acceptance" title="Enrol">
          <div class="form">
            <div class="field">
              <label for="enrol-email">Student's email (their login)</label>
              <InputText id="enrol-email" v-model="email" type="email" autocomplete="off" fluid :invalid="Boolean(email) && !EMAIL.test(email.trim())" />
            </div>
            <div class="field">
              <label for="enrol-date">Enrolled from</label>
              <DatePicker v-model="enrollmentDay" input-id="enrol-date" date-format="dd-mm-yy" show-icon fluid />
            </div>
          </div>
          <Message v-if="formError" severity="error" :closable="false" role="alert">{{ formError }}</Message>
        </DetailSection>

        <template v-if="page?.can_enrol && !offer.needs_acceptance" #actions>
          <Button label="Enrol" :loading="saving" :disabled="!canEnrol" @click="confirmEnrol" />
        </template>
      </DetailPane>

      <DetailPane v-else-if="enrolled" :title="enrolled.applicant" :subtitle="[enrolled.student, enrolled.student_login].filter(Boolean).join(' · ')">
        <template #tags>
          <Tag v-if="enrolled.invoice" :severity="invoiceSeverity(enrolled.invoice.status)" :value="enrolled.invoice.status" class="small-tag" />
        </template>
        <DetailSection title="Programme" :summary="enrolled.program">
          <p class="ec-muted">{{ enrolled.offering }} · {{ enrolled.campus }} · {{ enrolled.academic_year }}</p>
        </DetailSection>
        <DetailSection title="Enrolled from" :summary="formatDate(enrolled.enrollment_date)" />
        <DetailSection title="Fees">
          <template #summary>
            <template v-if="enrolled.invoice">
              <span>{{ formatMoney(enrolled.invoice.grand_total) }}</span>
              <span v-if="enrolled.invoice.outstanding_amount > 0" class="ec-muted">{{ formatMoney(enrolled.invoice.outstanding_amount) }} owing</span>
            </template>
            <span v-else class="ec-muted">Not invoiced</span>
          </template>
        </DetailSection>
      </DetailPane>
    </template>
  </SplitView>
</template>

<style scoped>
.year {
  width: 7.5rem;
}

.search {
  flex: 1;
}

.item {
  display: grid;
  gap: 0.3rem;
}

.item-top,
.item-bottom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.item-top {
  justify-content: space-between;
}

.who {
  font-weight: 600;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.small-tag {
  font-size: 0.75rem;
  padding: 0.15rem 0.5rem;
}

.notice {
  padding: 0.55rem 0.75rem;
  border-radius: var(--ec-radius-sm);
  background: #fffbeb;
  color: var(--ec-warn);
  font-size: 0.85rem;
}

.form {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

label {
  font-size: 0.8125rem;
  color: var(--ec-muted);
}

p {
  margin: 0;
}
</style>
