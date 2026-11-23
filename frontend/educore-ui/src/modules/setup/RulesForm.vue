<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import Select from "primevue/select";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, reactive, watch } from "vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import SettingRow from "@/core/ui/SettingRow.vue";
import type { BankAccountChoice, Settings } from "./api";

/**
 * The university's admission settings, one row per setting, grouped in sections with a short list of the
 * sections beside them. The fee account and income account are picked from ERPNext; applicants are shown that
 * account's bank, number and branch.
 */
const props = defineProps<{
  settings: Settings;
  countries: string[];
  bankAccounts: BankAccountChoice[];
  incomeAccounts: string[];
  saving: boolean;
}>();
const emit = defineEmits<{ save: [Partial<Settings>] }>();

/** a copy to edit; Save sends it, Undo goes back to what is saved */
const form = reactive({ ...props.settings });
watch(
  () => props.settings,
  (saved) => Object.assign(form, saved),
);
const changed = computed(() =>
  (Object.keys(form) as (keyof Settings)[]).some((key) => (form[key] ?? null) !== (props.settings[key] ?? null)),
);

/** switches are stored as 0/1 */
const flag = (key: keyof Settings) =>
  computed({ get: () => Boolean(form[key]), set: (on: boolean) => ((form[key] as number) = on ? 1 : 0) });
const needsDocuments = flag("approval_needs_verified_documents");
const needsFee = flag("approval_needs_fee");
const needsAcceptance = flag("enrolment_needs_acceptance");
const notify = flag("notify_applicants");

const bank = computed(() => props.bankAccounts.find((b) => b.name === form.fee_bank_account));

const SECTIONS = [
  { id: "s-applications", label: "Applications" },
  { id: "s-fees", label: "Application fees" },
  { id: "s-offers", label: "Offers" },
  { id: "s-documents", label: "Documents and points" },
];
function go(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}
</script>

<template>
  <div class="rules">
    <nav class="sections" aria-label="Settings sections">
      <button v-for="s in SECTIONS" :key="s.id" type="button" @click="go(s.id)">{{ s.label }}</button>
    </nav>

    <div class="panels">
      <EcPanel id="s-applications" title="Applications">
        <SettingRow label="Local applicants" help="Citizens and permanent residents of" for="home">
          <Select v-model="form.home_country" input-id="home" :options="countries" filter fluid />
        </SettingRow>
        <SettingRow label="Programme choices" for="choices">
          <InputNumber v-model="form.max_choices" input-id="choices" :min="1" :max="10" show-buttons fluid />
        </SettingRow>
        <SettingRow label="Documents verified before an offer" help="Online applications" for="needs-docs">
          <ToggleSwitch v-model="needsDocuments" input-id="needs-docs" />
        </SettingRow>
        <SettingRow label="Fee settled before an offer" help="Online applications" for="needs-fee">
          <ToggleSwitch v-model="needsFee" input-id="needs-fee" />
        </SettingRow>
      </EcPanel>

      <EcPanel id="s-fees" title="Application fees" note="N$, non-refundable">
        <table class="fees">
          <thead>
            <tr><th scope="col"></th><th scope="col">Online</th><th scope="col">Paper form</th></tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Local applicants</th>
              <td><InputNumber v-model="form.fee_namibian" :min="0" :min-fraction-digits="2" aria-label="Online fee, local applicants" fluid /></td>
              <td><InputNumber v-model="form.fee_paper_local" :min="0" :min-fraction-digits="2" aria-label="Paper fee, local applicants" fluid /></td>
            </tr>
            <tr>
              <th scope="row">International applicants</th>
              <td><InputNumber v-model="form.fee_international" :min="0" :min-fraction-digits="2" aria-label="Online fee, international applicants" fluid /></td>
              <td><InputNumber v-model="form.fee_paper_international" :min="0" :min-fraction-digits="2" aria-label="Paper fee, international applicants" fluid /></td>
            </tr>
          </tbody>
        </table>
        <div class="rows">
          <SettingRow label="Bank account" for="bank">
            <Select v-model="form.fee_bank_account" input-id="bank" :options="bankAccounts" option-label="label" option-value="name" placeholder="Choose an account" show-clear fluid />
          </SettingRow>
          <dl v-if="bank" class="shown" aria-label="Shown to applicants">
            <p class="caption">Shown to applicants</p>
            <div><dt>Bank</dt><dd>{{ bank.bank }}</dd></div>
            <div><dt>Account holder</dt><dd>{{ bank.holder }}</dd></div>
            <div><dt>Account number</dt><dd>{{ bank.account_number || "Not set in ERPNext" }}</dd></div>
            <div><dt>Branch code</dt><dd>{{ bank.branch_code || "Not set in ERPNext" }}</dd></div>
          </dl>
          <SettingRow label="Income account" for="income">
            <Select v-model="form.fee_income_account" input-id="income" :options="incomeAccounts" placeholder="Choose an account" filter show-clear fluid />
          </SettingRow>
        </div>
      </EcPanel>

      <EcPanel id="s-offers" title="Offers">
        <SettingRow label="Days to accept an offer" for="days">
          <InputNumber v-model="form.offer_response_days" input-id="days" :min="1" :max="365" show-buttons fluid />
        </SettingRow>
        <SettingRow label="Reminder before the deadline" help="Days before; 0 for none" for="reminder">
          <InputNumber v-model="form.offer_reminder_days" input-id="reminder" :min="0" :max="60" show-buttons fluid />
        </SettingRow>
        <SettingRow label="Register only accepted offers" help="Online applications" for="needs-acceptance">
          <ToggleSwitch v-model="needsAcceptance" input-id="needs-acceptance" />
        </SettingRow>
        <SettingRow label="Email applicants" for="notify">
          <ToggleSwitch v-model="notify" input-id="notify" />
        </SettingRow>
      </EcPanel>

      <EcPanel id="s-documents" title="Documents and points">
        <SettingRow label="Certified copies valid for" help="0 for no limit" for="cert">
          <InputNumber v-model="form.certification_max_age_months" input-id="cert" :min="0" :max="120" suffix=" months" show-buttons fluid />
        </SettingRow>
        <SettingRow label="Largest upload" for="size">
          <InputNumber v-model="form.max_file_size_mb" input-id="size" :min="1" :max="50" suffix=" MB" show-buttons fluid />
        </SettingRow>
        <SettingRow label="Subjects counted for points" help="Best subjects on the school results" for="best">
          <InputNumber v-model="form.best_subjects" input-id="best" :min="1" :max="12" show-buttons fluid />
        </SettingRow>
      </EcPanel>

      <!-- only once something changed: nothing sits over the form otherwise -->
      <div v-if="changed || saving" class="save-bar">
        <span class="ec-muted">Unsaved changes</span>
        <EcButton label="Undo" variant="ghost" :disabled="!changed || saving" @click="Object.assign(form, settings)" />
        <EcButton label="Save" variant="primary" :loading="saving" @click="emit('save', { ...form })" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.rules {
  display: grid;
  grid-template-columns: 12rem minmax(0, 52rem);
  gap: 1.5rem;
  align-items: start;
}

.sections {
  position: sticky;
  top: 0;
  display: grid;
  gap: 0.1rem;
}

.sections button {
  padding: 0.45rem 0.6rem;
  border: 0;
  border-radius: var(--ec-radius-sm);
  background: none;
  color: var(--ec-muted);
  font: inherit;
  font-size: 0.875rem;
  text-align: left;
  cursor: pointer;
}

.sections button:hover {
  background: var(--ec-surface);
  color: var(--ec-ink);
}

.panels {
  display: grid;
  gap: 1rem;
}

.panels > :deep(section) {
  scroll-margin-top: 0.5rem;
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

/* always in reach on a long form */
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

@media (max-width: 899px) {
  .rules {
    grid-template-columns: minmax(0, 1fr);
  }

  .sections {
    display: none;
  }
}
</style>
