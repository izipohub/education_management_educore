<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import ReviewPanel from "./ReviewPanel.vue";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { ApiError } from "@/core/api/client";
import { eligibilityLabel, offerLabel } from "@/core/status";
import { formatDate, shortUser } from "@/core/format";
import {
  type Action,
  type Application,
  type ApplicationsPage,
  NEEDS_REASON,
  type Places,
  OCCASIONAL,
  STATUSES,
  type Status,
  decide,
  listApplications,
} from "./api";

const toast = useToast();

const status = ref<Status>("Applied");
const academicYear = ref<string | undefined>();
const search = ref("");
const page = ref<ApplicationsPage | null>(null);
const loading = ref(false);
const loadError = ref("");
/** applicant names with an action in flight */
const busy = ref(new Set<string>());

const statusOptions = computed(() =>
  STATUSES.filter((s) => !OCCASIONAL.includes(s) || (page.value?.counts[s] ?? 0) > 0 || s === status.value).map((s) => ({
    label: `${s} (${page.value?.counts[s] ?? 0})`,
    value: s,
  })),
);

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await listApplications({
      status: status.value,
      academic_year: academicYear.value,
      search: search.value.trim() || undefined,
    });
    // first load: the server chose the year (the newest with applications); show it without reloading
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

/** set while the year chosen by the server is put in the selector, so that does not load again */
let adoptingYear = false;
let searchTimer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(load, 300);
});
watch([status, academicYear], () => {
  if (adoptingYear) {
    adoptingYear = false;
    return;
  }
  void load();
});
onMounted(load);

function places(row: Application): Places | undefined {
  return page.value?.capacity[`${row.offering}|${row.academic_year}`];
}

/** the application open in the review panel */
const reviewing = ref<string | null>(null);

/** why Approve is unavailable on this row, or undefined when it is not */
function approveBlocked(row: Application): string | undefined {
  if (isFull(row)) return "All places on this offering are offered";
  if (row.blockers.length) return `Not ready: ${row.blockers.join("; ")}`;
  return undefined;
}

function isFull(row: Application) {
  const p = places(row);
  return Boolean(p?.capacity && p.taken >= p.capacity);
}

function placesSeverity(p: Places | undefined) {
  if (!p?.capacity) return "secondary";
  if (p.taken >= p.capacity) return "danger";
  return p.taken / p.capacity >= 0.9 ? "warn" : "success";
}

// --- actions ------------------------------------------------------------------------------------------

const reasonFor = ref<{ row: Application; action: Action } | null>(null);
const reason = ref("");
/** approving an online application makes an offer: conditions are optional */
const offering = computed(() => reasonFor.value?.action === "Approve");

/** which of the applicant's choices is offered: the one under decision unless the officer picks another */
const offerChoice = ref("");

function start(row: Application, action: Action) {
  if (NEEDS_REASON.includes(action) || (action === "Approve" && row.online)) {
    reasonFor.value = { row, action };
    reason.value = "";
    offerChoice.value = row.offering;
  } else {
    void run(row, action);
  }
}

async function confirmWithReason() {
  if (!reasonFor.value || (!offering.value && !reason.value.trim())) return;
  const { row, action } = reasonFor.value;
  reasonFor.value = null;
  if (action === "Approve") await run(row, action, undefined, reason.value.trim() || undefined, offerChoice.value);
  else await run(row, action, reason.value.trim());
}

const eligibilitySeverity = (value: string | null) =>
  value === "Meets requirements" ? "success" : value === "Does not meet requirements" ? "danger" : "warn";

const OFFER_SEVERITY: Record<string, string> = { "Awaiting response": "warn", Accepted: "success", Declined: "danger", Lapsed: "secondary" };

const PAST_TENSE: Record<Action, string> = {
  Approve: "approved",
  Reject: "rejected",
  "Withdraw Offer": "offer withdrawn",
  Reconsider: "reopened",
};

async function run(row: Application, action: Action, why?: string, conditions?: string, offering?: string) {
  busy.value.add(row.name);
  try {
    await decide(row.name, action, why, conditions, offering);
    toast.add({ severity: "success", summary: `${row.applicant}: ${PAST_TENSE[action]}`, life: 4000 });
    await load();
  } catch (error) {
    const detail = error instanceof ApiError ? error.message : String(error);
    toast.add({ severity: "error", summary: `${action} failed`, detail, life: 8000 });
  } finally {
    busy.value.delete(row.name);
  }
}

function actionSeverity(action: Action) {
  return action === "Approve" ? undefined : action === "Reconsider" ? "secondary" : "danger";
}
</script>

<template>
  <section class="admissions">
    <header class="head">
      <div>
        <h1>Admissions</h1>
        <p class="intro">Applications for the campuses you work on. Approving offers a place; places are limited per offering.</p>
      </div>
      <div class="filters">
        <Select
          v-model="academicYear"
          :options="page?.academic_years ?? []"
          placeholder="Academic year"
          aria-label="Academic year"
          class="year"
        />
        <InputText v-model="search" placeholder="Search name or number" aria-label="Search applications" />
      </div>
    </header>

    <SelectButton v-model="status" :options="statusOptions" option-label="label" option-value="value" :allow-empty="false" aria-label="Status" class="tabs" />

    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <DataTable :value="page?.rows ?? []" :loading="loading" data-key="name" striped-rows class="table">
      <template #empty>
        <p class="empty">No {{ status.toLowerCase() }} applications{{ academicYear ? ` for ${academicYear}` : "" }}.</p>
      </template>

      <Column header="Applicant">
        <template #body="{ data }">
          <div class="applicant">{{ data.applicant }}</div>
          <div class="sub">
            {{ data.name }} · applied <span class="nowrap">{{ formatDate(data.application_date) }}</span>
          </div>
        </template>
      </Column>

      <Column header="Programme offering">
        <template #body="{ data }">
          <div>{{ data.program }}</div>
          <div class="sub">{{ data.offering }} · {{ data.campus }} · {{ data.mode_of_study }}</div>
        </template>
      </Column>

      <Column v-if="status === 'Applied'" header="Documents and fee">
        <template #body="{ data }">
          <template v-if="data.online">
            <Tag
              :severity="data.documents_verified === data.documents_required ? 'success' : data.documents_rejected.length ? 'danger' : 'secondary'"
              :value="`Documents ${data.documents_verified}/${data.documents_required}`"
            />
            <Tag :severity="data.fee_status === 'Unpaid' ? 'warn' : 'success'" :value="`Fee ${(data.fee_status ?? 'Unpaid').toLowerCase()}`" class="fee-tag" />
          </template>
          <span v-else class="sub">Paper application</span>
        </template>
      </Column>

      <Column header="Places offered">
        <template #body="{ data }">
          <Tag
            v-if="places(data)?.capacity"
            :severity="placesSeverity(places(data))"
            :value="`${places(data)?.taken} of ${places(data)?.capacity}`"
          />
          <span v-else class="sub">No limit</span>
        </template>
      </Column>

      <Column v-if="status === 'Approved'" header="Offer">
        <template #body="{ data }">
          <template v-if="data.offer_status">
            <Tag :severity="OFFER_SEVERITY[data.offer_status]" :value="offerLabel(data.offer_status)" />
            <div v-if="data.offer_status === 'Awaiting response' && data.offer_deadline" class="sub nowrap">by {{ formatDate(data.offer_deadline) }}</div>
          </template>
          <span v-else class="sub">In person</span>
        </template>
      </Column>

      <Column v-if="status !== 'Applied'" header="Decision">
        <template #body="{ data }">
          <div v-if="data.decided_by">
            {{ shortUser(data.decided_by) }} · <span class="nowrap">{{ formatDate(data.decided_on) }}</span>
          </div>
          <div v-if="data.decision_reason" class="sub reason">{{ data.decision_reason }}</div>
        </template>
      </Column>

      <Column header="" class="actions-col">
        <template #body="{ data }">
          <div class="actions">
            <Button label="Review" size="small" text @click="reviewing = data.name" />
            <Button
              v-for="action in data.actions"
              :key="action"
              :label="action"
              size="small"
              :severity="actionSeverity(action)"
              :outlined="action !== 'Approve'"
              :loading="busy.has(data.name)"
              :disabled="action === 'Approve' && Boolean(approveBlocked(data))"
              :title="action === 'Approve' ? approveBlocked(data) : undefined"
              @click="start(data, action)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <ReviewPanel :name="reviewing" @close="reviewing = null" @changed="load" />

    <Dialog
      :visible="reasonFor !== null"
      modal
      :header="reasonFor ? `${offering ? 'Offer a place' : reasonFor.action}: ${reasonFor.row.applicant}` : ''"
      :style="{ width: 'min(32rem, calc(100vw - 32px))' }"
      @update:visible="(open: boolean) => !open && (reasonFor = null)"
    >
      <template v-if="offering">
        <fieldset v-if="(reasonFor?.row.choices.length ?? 0) > 1" class="choices">
          <legend class="reason-label">Programme to offer</legend>
          <label v-for="c in reasonFor?.row.choices" :key="c.offering" class="choice-option">
            <input v-model="offerChoice" type="radio" name="offer-choice" :value="c.offering" />
            <span class="choice-name">{{ c.rank }}. {{ c.program }} <span class="sub">{{ c.campus }}</span></span>
            <Tag :severity="eligibilitySeverity(c.eligibility)" :value="eligibilityLabel(c.eligibility)" class="nowrap" />
          </label>
        </fieldset>
        <label for="reason" class="reason-label">Offer conditions (optional, shown in the offer letter)</label>
      </template>
      <label v-else for="reason" class="reason-label">Reason (kept on the application)</label>
      <Textarea id="reason" v-model="reason" rows="4" fluid auto-resize />
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="reasonFor = null" />
        <Button
          :label="offering ? 'Make offer' : (reasonFor?.action ?? '')"
          :severity="offering ? undefined : 'danger'"
          :disabled="!offering && !reason.trim()"
          @click="confirmWithReason"
        />
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

.applicant {
  font-weight: 600;
}

.sub {
  font-size: 0.8rem;
  color: #6b7280;
}

.reason {
  max-width: 22rem;
}

.nowrap {
  white-space: nowrap;
}

.fee-tag {
  margin-left: 0.35rem;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.4rem;
}

.empty {
  margin: 1rem 0;
  text-align: center;
  color: #6b7280;
}

.choices {
  display: grid;
  gap: 0.4rem;
  margin: 0 0 1rem;
  padding: 0;
  border: 0;
}

.choice-option {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.6rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
}

.choice-option {
  flex-wrap: nowrap;
}

.choice-name {
  flex: 1;
}

.choice-option input {
  accent-color: var(--color-brand-navy);
}

.reason-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}
</style>
