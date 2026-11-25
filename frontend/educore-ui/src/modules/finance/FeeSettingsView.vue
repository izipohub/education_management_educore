<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import MultiSelect from "primevue/multiselect";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SettingRow from "@/core/ui/SettingRow.vue";
import { type FeeSettings, getFeeSettings, saveFeeSettings } from "./api";

/**
 * What applicants and students pay, and where it is booked: application fees and the ERPNext accounts, the
 * deposit and balance allowed before registering, and each year's late registration fee. The Bursar changes
 * them; finance officers read them. The Registrar's screens show them, read only.
 */
const toast = useToast();
const saved = ref<FeeSettings | null>(null);
const form = ref<FeeSettings | null>(null);
const error = ref("");
const saving = ref(false);

/** the funding routes that pay no application fee (NSFAF, NTA), as the Bursar chooses them */
const feeFree = ref<string[]>([]);
const freeOf = (d: FeeSettings) => d.funding_routes.filter((r) => !r.pays_application_fee).map((r) => r.name);
function take(data: FeeSettings) {
  saved.value = data;
  form.value = JSON.parse(JSON.stringify(data));
  feeFree.value = freeOf(data);
}
onMounted(async () => {
  try {
    take(await getFeeSettings());
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

const editable = computed(() => Boolean(saved.value?.can_edit));
const changed = computed(() => {
  if (!saved.value || !form.value) return false;
  const pick = (d: FeeSettings) => JSON.stringify([d.application, d.registration, d.late_fees, d.regional_countries]);
  return pick(saved.value) !== pick(form.value) || JSON.stringify([...feeFree.value].sort()) !== JSON.stringify(freeOf(saved.value).sort());
});
const bank = computed(() => form.value?.bank_accounts.find((b) => b.name === form.value?.application.fee_bank_account));
const percent = computed(() => form.value?.registration.deposit_type === "Percent of the year's fees");
const depositLabel = computed(() => (percent.value ? "Deposit, share of the year's fees" : "Deposit amount"));

async function save() {
  if (!form.value) return;
  saving.value = true;
  try {
    take(
      await saveFeeSettings({
        application: form.value.application,
        registration: form.value.registration,
        late_fees: form.value.late_fees,
        regional_countries: form.value.regional_countries,
        fee_free_routes: feeFree.value,
      }),
    );
    toast.add({ severity: "success", summary: "Fee settings saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
const undo = () => saved.value && take(saved.value);
</script>

<template>
  <section class="fee-settings">
    <PageHeader title="Fee settings" :subtitle="editable ? 'What applicants and students pay, and where it is booked' : 'Set by the Bursar'" />

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-else-if="!form" class="card"><EcSkeleton shape="lines" :rows="6" label="Loading" /></div>

    <template v-else>
      <EcPanel title="Application fees" note="N$, non-refundable">
        <table class="fees">
          <thead>
            <tr><th scope="col"></th><th scope="col">Online</th><th scope="col">Paper form</th></tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Local applicants</th>
              <td><InputNumber v-model="form.application.fee_namibian" :min="0" :min-fraction-digits="2" :disabled="!editable" aria-label="Online fee, local applicants" fluid /></td>
              <td><InputNumber v-model="form.application.fee_paper_local" :min="0" :min-fraction-digits="2" :disabled="!editable" aria-label="Paper fee, local applicants" fluid /></td>
            </tr>
            <tr>
              <th scope="row">Regional applicants</th>
              <td><InputNumber v-model="form.application.fee_regional" :min="0" :min-fraction-digits="2" :disabled="!editable" placeholder="As international" aria-label="Online fee, regional applicants" fluid /></td>
              <td><InputNumber v-model="form.application.fee_paper_regional" :min="0" :min-fraction-digits="2" :disabled="!editable" placeholder="As international" aria-label="Paper fee, regional applicants" fluid /></td>
            </tr>
            <tr>
              <th scope="row">International applicants</th>
              <td><InputNumber v-model="form.application.fee_international" :min="0" :min-fraction-digits="2" :disabled="!editable" aria-label="Online fee, international applicants" fluid /></td>
              <td><InputNumber v-model="form.application.fee_paper_international" :min="0" :min-fraction-digits="2" :disabled="!editable" aria-label="Paper fee, international applicants" fluid /></td>
            </tr>
          </tbody>
        </table>
        <div class="rows">
          <SettingRow label="Regional countries" :help="`Their citizens pay the regional fee (${form.regional_countries.length})`" for="regional">
            <MultiSelect v-model="form.regional_countries" input-id="regional" :options="form.countries" filter display="comma" :max-selected-labels="3" :disabled="!editable" placeholder="None" fluid />
          </SettingRow>
          <SettingRow label="No application fee for" help="Funding routes whose applicants pay none" for="fee-free">
            <MultiSelect v-model="feeFree" input-id="fee-free" :options="form.funding_routes.map((r) => r.name)" display="chip" :disabled="!editable" placeholder="Every route pays" fluid />
          </SettingRow>
          <SettingRow label="Bank account" for="bank">
            <Select v-model="form.application.fee_bank_account" input-id="bank" :options="form.bank_accounts" option-label="label" option-value="name" placeholder="Choose an account" :disabled="!editable" show-clear fluid />
          </SettingRow>
          <dl v-if="bank" class="shown" aria-label="Shown to applicants">
            <p class="caption">Shown to applicants</p>
            <div><dt>Bank</dt><dd>{{ bank.bank }}</dd></div>
            <div><dt>Account holder</dt><dd>{{ bank.holder }}</dd></div>
            <div><dt>Account number</dt><dd>{{ bank.account_number || "Not set in ERPNext" }}</dd></div>
            <div><dt>Branch code</dt><dd>{{ bank.branch_code || "Not set in ERPNext" }}</dd></div>
          </dl>
          <SettingRow label="Income account" for="income">
            <Select v-model="form.application.fee_income_account" input-id="income" :options="form.income_accounts" placeholder="Choose an account" :disabled="!editable" filter show-clear fluid />
          </SettingRow>
        </div>
      </EcPanel>

      <EcPanel title="Before registering">
        <SettingRow label="Outstanding balance allowed" help="Fees owed from earlier years above this block registration" for="outstanding">
          <InputNumber v-model="form.registration.max_outstanding" input-id="outstanding" :min="0" :min-fraction-digits="2" prefix="N$ " :disabled="!editable" fluid />
        </SettingRow>
        <SettingRow label="Registration deposit" for="deposit-type">
          <Select v-model="form.registration.deposit_type" input-id="deposit-type" :options="form.deposit_types" :disabled="!editable" fluid />
        </SettingRow>
        <SettingRow v-if="form.registration.deposit_type !== 'None'" :label="depositLabel" for="deposit">
          <InputNumber v-if="percent" v-model="form.registration.deposit_value" input-id="deposit" :min="0" :max="100" suffix=" %" show-buttons :disabled="!editable" fluid />
          <InputNumber v-else v-model="form.registration.deposit_value" input-id="deposit" :min="0" :min-fraction-digits="2" prefix="N$ " :disabled="!editable" fluid />
        </SettingRow>
      </EcPanel>

      <EcPanel title="Late registration fee" note="Per academic year; the dates are the Registrar's">
        <p v-if="!form.late_fees.length" class="ec-muted none">No registration periods yet</p>
        <SettingRow
          v-for="p in form.late_fees"
          :key="p.name"
          :label="p.academic_year"
          :help="p.late_until ? `Late registration until ${formatDate(p.late_until)}` : 'No late registration this year'"
          :for="`late-${p.name}`"
        >
          <InputNumber v-model="p.late_fee" :input-id="`late-${p.name}`" :min="0" :min-fraction-digits="2" prefix="N$ " :disabled="!editable" fluid />
        </SettingRow>
      </EcPanel>

      <div v-if="editable && (changed || saving)" class="save-bar">
        <span class="ec-muted">Unsaved changes</span>
        <EcButton label="Undo" variant="ghost" :disabled="saving" @click="undo" />
        <EcButton label="Save" variant="primary" :loading="saving" @click="save" />
      </div>
    </template>
  </section>
</template>

<style scoped>
.fee-settings {
  display: grid;
  gap: 1rem;
  max-width: 52rem;
}

.fees {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.fees th {
  padding: 0 0.5rem 0.5rem 0;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-align: left;
}

.fees tbody th {
  padding: 0.35rem 1rem 0.35rem 0;
  color: var(--ec-text);
  font-size: 0.875rem;
  white-space: nowrap;
}

.fees td {
  padding: 0.35rem 0.5rem 0.35rem 0;
}

.rows {
  margin-top: 1.1rem;
  padding-top: 0.9rem;
  border-top: 1px solid var(--ec-border-soft);
}

.shown {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
  gap: 0.5rem 1rem;
  margin: 0 0 0.9rem;
  padding: 0.75rem 0.9rem;
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface-muted);
}

.caption {
  grid-column: 1 / -1;
  margin: 0;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 600;
}

.shown dt {
  color: var(--ec-muted);
  font-size: 0.75rem;
}

.shown dd {
  margin: 0.1rem 0 0;
  font-size: 0.85rem;
}

.none {
  margin: 0;
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
