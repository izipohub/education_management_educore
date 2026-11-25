<script setup lang="ts">
import { RefreshCw, Search } from "@lucide/vue";
import AutoComplete from "primevue/autocomplete";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { formatDate, formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type ReceivedPayment, type WaitingDeposit, assignDeposit, findPayingSponsors, findStudents, listStudentPayments, matchStudentPayments } from "./api";

/**
 * Student fees received from the bank statement (matched by student number), and deposits waiting to be
 * assigned to a student because no student number could be read from them.
 */
const toast = useToast();
type View = "received" | "waiting";
const view = ref<View>("received");
const search = ref("");
const received = ref<ReceivedPayment[]>([]);
const waiting = ref<WaitingDeposit[]>([]);
const waitingCount = ref(0);
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  error.value = "";
  try {
    if (view.value === "received") {
      const page = await listStudentPayments<ReceivedPayment>("received", search.value.trim() || undefined);
      received.value = page.rows;
      waitingCount.value = page.counts.waiting;
    } else {
      const page = await listStudentPayments<WaitingDeposit>("waiting", search.value.trim() || undefined);
      waiting.value = page.rows;
      waitingCount.value = page.counts.waiting;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(view, load);
let timer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(timer);
  timer = setTimeout(load, 300);
});

const tabs = computed(() => [
  { label: "Received", value: "received" as View },
  { label: "To assign", value: "waiting" as View, count: waitingCount.value },
]);
const columns = computed<Column[]>(() =>
  view.value === "received"
    ? [
        { key: "student_name", label: "Student" },
        { key: "posting_date", label: "Date" },
        { key: "reference_no", label: "Bank reference", wide: true },
        { key: "paid_amount", label: "Amount", align: "right" },
        { key: "unallocated_amount", label: "In advance", align: "right", wide: true },
      ]
    : [
        { key: "description", label: "Bank line" },
        { key: "date", label: "Date" },
        { key: "amount", label: "Amount", align: "right" },
        { key: "action", label: "", align: "right" },
      ],
);
const rows = computed(() => ((view.value === "received" ? received.value : waiting.value) as unknown) as Record<string, unknown>[]);
const rec = (r: Record<string, unknown>) => r as unknown as ReceivedPayment;
const wait = (r: Record<string, unknown>) => r as unknown as WaitingDeposit;

// matching now, rather than on the hour
const matching = ref(false);
async function matchNow() {
  matching.value = true;
  try {
    const { matched } = await matchStudentPayments();
    toast.add({ severity: "success", summary: matched ? `${matched} payments matched` : "Nothing new to match", life: 3000 });
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not matched", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    matching.value = false;
  }
}

// assigning a deposit to a student, or to a sponsor (educore.finance.sponsors)
type Payer = "student" | "sponsor";
const payer = ref<Payer>("student");
const payers = [
  { value: "student" as Payer, label: "Student" },
  { value: "sponsor" as Payer, label: "Sponsor" },
];
const assigning = ref<WaitingDeposit | null>(null);
const chosen = ref<{ name: string; label: string; who: string } | null>(null);
const suggestions = ref<{ name: string; label: string; who: string }[]>([]);
watch(payer, () => (chosen.value = null));
async function searchStudents(event: { query: string }) {
  if (payer.value === "sponsor") {
    const found = await findPayingSponsors(event.query).catch(() => []);
    suggestions.value = found.map((s) => ({ name: s.name, who: s.sponsor_name, label: `${s.sponsor_name} · ${s.name}` }));
    return;
  }
  const found = await findStudents(event.query).catch(() => []);
  suggestions.value = found.map((s) => ({ name: s.name, who: s.student_name, label: `${s.student_name} · ${s.name}` }));
}
const busy = ref(false);
async function confirmAssign() {
  if (!assigning.value || !chosen.value) return;
  busy.value = true;
  try {
    await assignDeposit(assigning.value.name, { [payer.value]: chosen.value.name });
    toast.add({ severity: "success", summary: `${formatMoney(assigning.value.amount)} recorded for ${chosen.value.who}`, life: 3000 });
    assigning.value = null;
    chosen.value = null;
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not recorded", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Student payments" subtitle="Fees paid by EFT with the student number as the reference, from the bank statement">
      <template #actions>
        <EcButton label="Match now" :icon="RefreshCw" :loading="matching" @click="matchNow" />
      </template>
      <EcTabs v-model="view" :tabs="tabs" label="View" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable :columns="columns" :rows="rows" row-key="name" :loading="loading" :noun="view === 'received' ? 'payments' : 'deposits'" :empty-title="view === 'received' ? 'No student payments yet' : 'Nothing to assign'">
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" :placeholder="view === 'received' ? 'Student or reference' : 'Text on the bank line'" aria-label="Search" fluid size="small" />
        </IconField>
      </template>

      <template #cell-student_name="{ row: r }">
        <span class="who">{{ rec(r).student_name }}</span>
        <span class="sub">{{ rec(r).student }}</span>
      </template>
      <template #cell-posting_date="{ row: r }"><span class="ec-nowrap">{{ formatDate(rec(r).posting_date) }}</span></template>
      <template #cell-paid_amount="{ row: r }"><span class="ec-nowrap">{{ formatMoney(rec(r).paid_amount) }}</span></template>
      <template #cell-unallocated_amount="{ row: r }"><span class="ec-nowrap">{{ rec(r).unallocated_amount ? formatMoney(rec(r).unallocated_amount) : "" }}</span></template>

      <template #cell-description="{ row: r }">
        <span class="who">{{ wait(r).description || wait(r).reference_number || wait(r).name }}</span>
        <span v-if="wait(r).numbers_found.length" class="sub">{{ wait(r).numbers_found.join(", ") }}: not a student number on record</span>
      </template>
      <template #cell-date="{ row: r }"><span class="ec-nowrap">{{ formatDate(wait(r).date) }}</span></template>
      <template #cell-amount="{ row: r }"><span class="ec-nowrap">{{ formatMoney(wait(r).amount) }}</span></template>
      <template #cell-action="{ row: r }">
        <EcButton label="Assign" size="sm" variant="ghost" @click="(assigning = wait(r)), (chosen = null), (payer = 'student')" />
      </template>
    </DataTable>
  </section>

  <EcModal :open="assigning !== null" :title="`Assign ${assigning ? formatMoney(assigning.amount) : ''}`" :description="assigning?.description ?? undefined" @update:open="(v: boolean) => !v && (assigning = null)">
    <EcSegmented v-model="payer" :options="payers" label="Paid by" class="payer" />
    <EcField :label="payer === 'student' ? 'Student' : 'Sponsor'" for="assign-student" :hint="payer === 'student' ? 'Name, student number or ID number' : 'Name or sponsor number'">
      <AutoComplete v-model="chosen" input-id="assign-student" :suggestions="suggestions" option-label="label" fluid @complete="searchStudents" />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="assigning = null" />
      <EcButton label="Record payment" variant="primary" :loading="busy" :disabled="!chosen || typeof chosen !== 'object'" @click="confirmAssign" />
    </template>
  </EcModal>
</template>

<style scoped>
.list-page {
  display: grid;
  gap: 1rem;
}

.tabs {
  flex: 1;
}

.payer {
  margin-bottom: 0.75rem;
}

.search {
  flex: 1;
  max-width: 22rem;
}

.who {
  display: block;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 400;
}
</style>
