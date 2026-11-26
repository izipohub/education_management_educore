<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatDate, formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Waiver, approveWaiver, listWaivers, rejectWaiver, waiverWhat } from "./waivers";

/** Fee waivers: requests waiting for the Bursar, and those decided. A waiver is requested from the student's
 * clearance page; a row opens it there. */
type Tab = "waiting" | "approved" | "other";
const route = useRoute();
const router = useRouter();
const toast = useToast();
const tab = ref<Tab>((route.query.tab as Tab) || "waiting");
const search = ref("");
const rows = ref<Waiver[]>([]);
const loading = ref(false);
const error = ref("");

async function load() {
  loading.value = true;
  try {
    rows.value = (await listWaivers()).rows;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(tab, () => void router.replace({ query: tab.value === "waiting" ? {} : { tab: tab.value } }));

const inTab = (w: Waiver, t: Tab) => (t === "waiting" ? w.status === "Requested" : t === "approved" ? w.status === "Approved" : !["Requested", "Approved"].includes(w.status));
const matching = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((w) => !q || `${w.student_name} ${w.student}`.toLowerCase().includes(q));
});
const tabs = computed(() => [
  { label: "Waiting", value: "waiting" as Tab, count: matching.value.filter((w) => inTab(w, "waiting")).length },
  { label: "Approved", value: "approved" as Tab, count: matching.value.filter((w) => inTab(w, "approved")).length },
  { label: "Rejected or withdrawn", value: "other" as Tab, count: matching.value.filter((w) => inTab(w, "other")).length },
]);
const shown = computed(() => matching.value.filter((w) => inTab(w, tab.value)) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as Waiver;
const columns = computed<Column[]>(() => [
  { key: "student_name", label: "Student" },
  { key: "waive", label: "Waived" },
  { key: "reason", label: "Reason", wide: true },
  { key: "status", label: "Status" },
  ...(rows.value.some((w) => w.can_decide) && tab.value === "waiting" ? [{ key: "decide", label: "", align: "right" as const }] : []),
]);

const busy = ref(false);
const deciding = ref<{ waiver: Waiver; approve: boolean } | null>(null);
const note = ref("");
function decide(w: Waiver, approve: boolean) {
  deciding.value = { waiver: w, approve };
  note.value = "";
}
async function confirm() {
  const d = deciding.value!;
  busy.value = true;
  try {
    const done = d.approve ? await approveWaiver(d.waiver.name, note.value || undefined) : await rejectWaiver(d.waiver.name, note.value);
    rows.value = rows.value.map((w) => (w.name === done.name ? done : w));
    toast.add({
      severity: "success",
      summary: d.approve ? "Waiver approved" : "Waiver rejected",
      detail: d.approve ? (done.credit_note ? `${formatMoney(done.amount)} taken off ${done.student_name}'s fees` : `Taken off when ${done.academic_year} is invoiced`) : undefined,
      life: 4000,
    });
    deciding.value = null;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Fee waivers" subtitle="Requested by Finance from a student's clearance page, decided by the Bursar">
      <EcTabs v-model="tab" :tabs="tabs" label="Fee waivers" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="shown"
      row-key="name"
      :to="(r) => ({ name: 'clearance-student', params: { name: String(r.student) } })"
      :loading="loading"
      noun="waivers"
      :empty-title="tab === 'waiting' ? 'No waiver waiting for the Bursar' : tab === 'approved' ? 'No waiver approved' : 'None'"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name or student number" aria-label="Search students" fluid size="small" />
        </IconField>
      </template>
      <template #cell-student_name="{ row: r }">
        <span class="who">{{ row(r).student_name }}</span>
        <span class="sub">{{ row(r).student }} · {{ row(r).academic_year }}</span>
      </template>
      <template #cell-waive="{ row: r }">
        <span class="ec-nowrap">{{ waiverWhat(row(r), formatMoney) }}</span>
        <span v-if="row(r).credit_note" class="sub">{{ formatMoney(row(r).amount) }} taken off</span>
      </template>
      <template #cell-reason="{ row: r }">
        {{ row(r).reason }}
        <span class="sub">{{ row(r).requested_by_name || row(r).requested_by }}, {{ formatDate(row(r).requested_on) }}<template v-if="row(r).decision_note"> · {{ row(r).decision_note }}</template></span>
      </template>
      <template #cell-status="{ row: r }"><StatusTag kind="waiver" :value="row(r).status" /></template>
      <template #cell-decide="{ row: r }">
        <span v-if="row(r).can_decide" class="decide">
          <EcButton label="Reject" size="sm" variant="ghost" @click="decide(row(r), false)" />
          <EcButton label="Approve" size="sm" @click="decide(row(r), true)" />
        </span>
      </template>
    </DataTable>
  </section>

  <EcModal
    :open="deciding !== null"
    :title="deciding?.approve ? 'Approve the waiver' : 'Reject the waiver'"
    :description="deciding ? `${deciding.waiver.student_name}, ${deciding.waiver.academic_year}: ${waiverWhat(deciding.waiver, formatMoney)}` : ''"
    @update:open="(v: boolean) => !v && (deciding = null)"
  >
    <EcField :label="deciding?.approve ? 'Note (optional)' : 'Why it is rejected'" for="waiver-note" :hint="deciding?.approve ? 'A credit note takes it off the year\'s invoice' : 'Finance sees this'">
      <Textarea id="waiver-note" v-model="note" rows="2" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="deciding = null" />
      <EcButton
        :label="deciding?.approve ? 'Approve' : 'Reject'"
        variant="primary"
        :loading="busy"
        :disabled="!deciding?.approve && !note.trim()"
        @click="confirm"
      />
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

.decide {
  display: inline-flex;
  gap: 0.375rem;
}
</style>
