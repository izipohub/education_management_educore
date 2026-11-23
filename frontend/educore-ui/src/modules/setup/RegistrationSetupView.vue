<script setup lang="ts">
import { Plus } from "@lucide/vue";
import InputNumber from "primevue/inputnumber";
import Message from "primevue/message";
import ToggleSwitch from "primevue/toggleswitch";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { formatDate, formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import EcTabs from "@/core/ui/EcTabs.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SettingRow from "@/core/ui/SettingRow.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Period, type RegistrationSettings, type RegistrationSetup, getRegistrationSetup, saveRegistrationSettings } from "./registrationSetup";

/** Registration setup: each year's registration period (a list; a row opens its page) and the rules */
const route = useRoute();
const router = useRouter();
const toast = useToast();
type Tab = "periods" | "settings";
const tab = ref<Tab>(route.query.tab === "settings" ? "settings" : "periods");
watch(tab, (t) => void router.replace({ query: t === "periods" ? {} : { tab: t } }));
const tabs = computed(() => [
  { label: "Periods", value: "periods" as Tab, count: setup.value?.periods.length },
  { label: "Settings", value: "settings" as Tab },
]);

const setup = ref<RegistrationSetup | null>(null);
const error = ref("");
const saving = ref(false);
const form = reactive<RegistrationSettings>({ max_outstanding: 0, deposit_type: "None", deposit_value: 0, max_credits: 0, approval_needed: 1 });

onMounted(async () => {
  try {
    setup.value = await getRegistrationSetup();
    Object.assign(form, setup.value.settings);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

const changed = computed(() =>
  Boolean(setup.value) && (Object.keys(form) as (keyof RegistrationSettings)[]).some((k) => form[k] !== setup.value!.settings[k]),
);
const approval = computed({ get: () => Boolean(form.approval_needed), set: (on: boolean) => (form.approval_needed = on ? 1 : 0) });
const deposit = computed(() => {
  const st = setup.value?.settings;
  if (!st || st.deposit_type === "None") return "None";
  return st.deposit_type === "Amount" ? formatMoney(st.deposit_value) : `${st.deposit_value}% of the year's fees`;
});

async function save() {
  saving.value = true;
  try {
    setup.value = await saveRegistrationSettings({ ...form });
    Object.assign(form, setup.value.settings);
    toast.add({ severity: "success", summary: "Settings saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}

const rows = computed(() => (setup.value?.periods ?? []) as unknown as Record<string, unknown>[]);
const period = (r: Record<string, unknown>) => r as unknown as Period;
const columns: Column[] = [
  { key: "academic_year", label: "Academic year" },
  { key: "opens_on", label: "Opens" },
  { key: "closes_on", label: "Closes" },
  { key: "late_until", label: "Late until", wide: true },
  { key: "late_fee", label: "Late fee", align: "right", wide: true },
  { key: "registrations", label: "Registrations", align: "right", wide: true },
  { key: "state", label: "Status" },
];
</script>

<template>
  <section class="setup">
    <PageHeader title="Registration setup" subtitle="When students register, and the rules they register under">
      <EcTabs v-model="tab" :tabs="tabs" label="Section" class="tabs" />
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-else-if="!setup" class="card"><EcSkeleton shape="lines" :rows="6" label="Loading" /></div>

    <DataTable
      v-else-if="tab === 'periods'"
      :columns="columns"
      :rows="rows"
      row-key="name"
      :to="(r) => ({ name: 'registration-period', params: { name: String(r.name) } })"
      noun="periods"
      empty-title="No registration periods yet"
    >
      <template #toolbar>
        <EcButton label="Add a period" :icon="Plus" size="sm" :disabled="!setup.academic_years.length" @click="router.push({ name: 'registration-period', params: { name: 'new' } })" />
      </template>
      <template #cell-opens_on="{ row: r }"><span class="ec-nowrap">{{ formatDate(period(r).opens_on) }}</span></template>
      <template #cell-closes_on="{ row: r }"><span class="ec-nowrap">{{ formatDate(period(r).closes_on) }}</span></template>
      <template #cell-late_until="{ row: r }"><span class="ec-nowrap">{{ period(r).late_until ? formatDate(period(r).late_until) : "No late registration" }}</span></template>
      <template #cell-late_fee="{ row: r }"><span class="ec-nowrap">{{ period(r).late_fee ? formatMoney(period(r).late_fee) : "" }}</span></template>
      <template #cell-state="{ row: r }"><StatusTag kind="period" :value="period(r).state" /></template>
    </DataTable>

    <div v-else class="settings">
      <!-- the money is Finance's: shown here, set in Fee settings -->
      <EcPanel title="Fees before registering" note="Set by Finance">
        <SettingRow label="Outstanding balance allowed" help="Fees owed from earlier years above this block registration">
          <span class="value">{{ formatMoney(setup.settings.max_outstanding) }}</span>
        </SettingRow>
        <SettingRow label="Registration deposit">
          <span class="value">{{ deposit }}</span>
        </SettingRow>
      </EcPanel>

      <EcPanel title="Courses and approval">
        <SettingRow label="Most credits per year" help="0 for no limit" for="credits">
          <InputNumber v-model="form.max_credits" input-id="credits" :min="0" :max="400" show-buttons fluid />
        </SettingRow>
        <SettingRow label="Faculty officer approves" help="Off: a submitted registration is approved at once" for="approval">
          <ToggleSwitch v-model="approval" input-id="approval" />
        </SettingRow>
      </EcPanel>

      <div v-if="changed || saving" class="save-bar">
        <span class="ec-muted">Unsaved changes</span>
        <EcButton label="Undo" variant="ghost" :disabled="saving" @click="Object.assign(form, setup.settings)" />
        <EcButton label="Save" variant="primary" :loading="saving" @click="save" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.setup {
  display: grid;
  gap: 1rem;
}

.tabs {
  flex: 1;
}

.settings {
  display: grid;
  gap: 1rem;
  max-width: 52rem;
}

.value {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.save-bar {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--ec-surface);
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius);
  box-shadow: 0 -2px 8px rgb(0 0 0 / 0.05);
}

.save-bar .ec-muted {
  margin-right: auto;
}
</style>
