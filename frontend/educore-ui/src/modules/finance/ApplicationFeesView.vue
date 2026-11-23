<script setup lang="ts">
import { Search } from "@lucide/vue";
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
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type ApplicationFee, type FeeStatus, type FeesPage, listFees, waiveFee } from "./api";

/** Application fees for Finance: outstanding, paid and waived; waiving one needs a reason */
const toast = useToast();
const status = ref<FeeStatus>("Unpaid");
const search = ref("");
const page = ref<FeesPage | null>(null);
const loading = ref(false);
const loadError = ref("");

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await listFees(status.value, search.value.trim() || undefined);
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(status, load);
let timer: ReturnType<typeof setTimeout> | undefined;
watch(search, () => {
  clearTimeout(timer);
  timer = setTimeout(load, 300);
});

const tabs = computed(() =>
  (["Unpaid", "Paid", "Waived"] as FeeStatus[]).map((s) => ({ label: s === "Unpaid" ? "Outstanding" : s, value: s, count: page.value?.counts[s] ?? 0 })),
);
const rows = computed(() => (page.value?.rows ?? []) as unknown as Record<string, unknown>[]);
const row = (r: Record<string, unknown>) => r as unknown as ApplicationFee;
const columns = computed<Column[]>(() => [
  { key: "applicant", label: "Applicant" },
  { key: "channel", label: "Application", wide: true },
  { key: "campus", label: "Campus", wide: true },
  { key: "amount", label: "Fee", align: "right" },
  status.value === "Unpaid" ? { key: "action", label: "", align: "right" } : { key: "note", label: "Note", wide: true },
]);

const waiving = ref<ApplicationFee | null>(null);
const reason = ref("");
const busy = ref(false);
async function confirmWaive() {
  const fee = waiving.value;
  if (!fee || !reason.value.trim()) return;
  busy.value = true;
  try {
    await waiveFee(fee.name, reason.value.trim());
    toast.add({ severity: "success", summary: `${fee.applicant}: fee waived`, life: 3000 });
    waiving.value = null;
    reason.value = "";
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not waived", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Application fees" subtitle="Paid by EFT, matched from the bank statement, or at a campus cashier">
      <EcTabs v-model="status" :tabs="tabs" label="Status" class="tabs" />
    </PageHeader>

    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <DataTable :columns="columns" :rows="rows" row-key="name" :loading="loading" noun="fees" :empty-title="status === 'Unpaid' ? 'No fees outstanding' : `No ${status.toLowerCase()} fees`">
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name or application number" aria-label="Search fees" fluid size="small" />
        </IconField>
      </template>

      <template #cell-applicant="{ row: r }">
        <span class="who">{{ row(r).applicant }}</span>
        <span class="sub">{{ row(r).name }}<template v-if="row(r).application_date"> · {{ formatDate(row(r).application_date) }}</template></span>
      </template>
      <template #cell-channel="{ row: r }">{{ row(r).online ? "Online" : "Paper" }}<span v-if="row(r).international" class="sub">International</span></template>
      <template #cell-campus="{ row: r }">{{ row(r).campus?.replace(" Campus", "") }}</template>
      <template #cell-amount="{ row: r }"><span class="ec-nowrap">{{ formatMoney(row(r).amount) }}</span></template>
      <template #cell-note="{ row: r }"><span class="ec-muted">{{ row(r).note }}</span></template>
      <template #cell-action="{ row: r }">
        <EcButton label="Waive" size="sm" variant="ghost" @click="(waiving = row(r)), (reason = '')" />
      </template>
    </DataTable>
  </section>

  <EcModal :open="waiving !== null" :title="`Waive the fee: ${waiving?.applicant ?? ''}`" @update:open="(v: boolean) => !v && (waiving = null)">
    <EcField label="Reason" for="waive-reason" hint="Kept on the application, e.g. the scheme it falls under">
      <InputText id="waive-reason" v-model="reason" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="waiving = null" />
      <EcButton :label="`Waive ${waiving ? formatMoney(waiving.amount) : ''}`" variant="primary" :loading="busy" :disabled="!reason.trim()" @click="confirmWaive" />
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
  white-space: nowrap;
}
</style>
