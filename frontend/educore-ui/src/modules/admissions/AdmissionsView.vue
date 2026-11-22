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
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { ApiError } from "@/core/api/client";
import { formatDate, shortUser } from "@/core/format";
import {
  type Action,
  type Application,
  type ApplicationsPage,
  NEEDS_REASON,
  type Places,
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
  STATUSES.map((s) => ({ label: `${s} (${page.value?.counts[s] ?? 0})`, value: s })),
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

function start(row: Application, action: Action) {
  if (NEEDS_REASON.includes(action)) {
    reasonFor.value = { row, action };
    reason.value = "";
  } else {
    void run(row, action);
  }
}

async function confirmWithReason() {
  if (!reasonFor.value || !reason.value.trim()) return;
  const { row, action } = reasonFor.value;
  reasonFor.value = null;
  await run(row, action, reason.value.trim());
}

const PAST_TENSE: Record<Action, string> = {
  Approve: "approved",
  Reject: "rejected",
  "Withdraw Offer": "offer withdrawn",
  Reconsider: "reopened",
};

async function run(row: Application, action: Action, why?: string) {
  busy.value.add(row.name);
  try {
    await decide(row.name, action, why);
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
            <Button
              v-for="action in data.actions"
              :key="action"
              :label="action"
              size="small"
              :severity="actionSeverity(action)"
              :outlined="action !== 'Approve'"
              :loading="busy.has(data.name)"
              :disabled="action === 'Approve' && isFull(data)"
              :title="action === 'Approve' && isFull(data) ? 'All places on this offering are offered' : undefined"
              @click="start(data, action)"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <Dialog
      :visible="reasonFor !== null"
      modal
      :header="reasonFor ? `${reasonFor.action}: ${reasonFor.row.applicant}` : ''"
      :style="{ width: 'min(32rem, calc(100vw - 32px))' }"
      @update:visible="(open: boolean) => !open && (reasonFor = null)"
    >
      <label for="reason" class="reason-label">Reason (kept on the application)</label>
      <Textarea id="reason" v-model="reason" rows="4" fluid auto-resize />
      <template #footer>
        <Button label="Cancel" severity="secondary" text @click="reasonFor = null" />
        <Button :label="reasonFor?.action ?? ''" severity="danger" :disabled="!reason.trim()" @click="confirmWithReason" />
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

.reason-label {
  display: block;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}
</style>
