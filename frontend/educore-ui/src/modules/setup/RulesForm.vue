<script setup lang="ts">
import Button from "primevue/button";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import ToggleSwitch from "primevue/toggleswitch";
import { computed, reactive, watch } from "vue";
import type { Settings } from "./api";

const props = defineProps<{ settings: Settings; countries: string[]; saving: boolean }>();
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
</script>

<template>
  <div class="rules">
    <section class="card group">
      <h2>Applications</h2>
      <div class="grid">
        <div class="field">
          <label id="home-label" for="home">Home country</label>
          <Select v-model="form.home_country" input-id="home" aria-labelledby="home-label" :options="countries" filter fluid />
          <small class="sub">Applicants from elsewhere are international.</small>
        </div>
        <div class="field">
          <label for="choices">Programme choices allowed</label>
          <InputNumber v-model="form.max_choices" input-id="choices" :min="1" :max="10" fluid />
        </div>
      </div>
      <div class="switches">
        <label class="switch"><ToggleSwitch v-model="needsDocuments" input-id="needs-docs" /> <span>Approve only once required documents are verified</span></label>
        <label class="switch"><ToggleSwitch v-model="needsFee" input-id="needs-fee" /> <span>Approve only once the fee is paid or waived</span></label>
      </div>
    </section>

    <section class="card group">
      <h2>Offers and emails</h2>
      <div class="grid">
        <div class="field">
          <label for="days">Days to accept an offer</label>
          <InputNumber v-model="form.offer_response_days" input-id="days" :min="1" :max="365" fluid />
        </div>
        <div class="field">
          <label for="reminder">Reminder, days before the deadline</label>
          <InputNumber v-model="form.offer_reminder_days" input-id="reminder" :min="0" :max="60" fluid />
          <small class="sub">0: no reminder.</small>
        </div>
      </div>
      <div class="switches">
        <label class="switch"><ToggleSwitch v-model="needsAcceptance" input-id="needs-acceptance" /> <span>Enrol online applicants only once they accept</span></label>
        <label class="switch"><ToggleSwitch v-model="notify" input-id="notify" /> <span>Email applicants</span></label>
      </div>
    </section>

    <section class="card group">
      <h2>Application fee</h2>
      <div class="grid">
        <div class="field">
          <label for="fee-home">Home applicants (N$)</label>
          <InputNumber v-model="form.fee_namibian" input-id="fee-home" :min="0" :min-fraction-digits="2" fluid />
        </div>
        <div class="field">
          <label for="fee-intl">International applicants (N$)</label>
          <InputNumber v-model="form.fee_international" input-id="fee-intl" :min="0" :min-fraction-digits="2" fluid />
        </div>
        <div class="field"><label for="bank">Bank</label><InputText id="bank" v-model="form.eft_bank_name" fluid /></div>
        <div class="field"><label for="acc-name">Account name</label><InputText id="acc-name" v-model="form.eft_account_name" fluid /></div>
        <div class="field"><label for="acc-no">Account number</label><InputText id="acc-no" v-model="form.eft_account_number" fluid /></div>
        <div class="field"><label for="branch">Branch code</label><InputText id="branch" v-model="form.eft_branch_code" fluid /></div>
      </div>
    </section>

    <section class="card group">
      <h2>Documents and points</h2>
      <div class="grid">
        <div class="field">
          <label for="cert">Certified copies valid for (months)</label>
          <InputNumber v-model="form.certification_max_age_months" input-id="cert" :min="0" :max="120" fluid />
          <small class="sub">0: no limit.</small>
        </div>
        <div class="field">
          <label for="size">Largest upload (MB)</label>
          <InputNumber v-model="form.max_file_size_mb" input-id="size" :min="1" :max="50" fluid />
        </div>
        <div class="field">
          <label for="best">Subjects counted for points</label>
          <InputNumber v-model="form.best_subjects" input-id="best" :min="1" :max="12" fluid />
        </div>
      </div>
    </section>

    <!-- only once something changed: nothing sits over the form otherwise -->
    <div v-if="changed || saving" class="save-bar">
      <Button label="Undo changes" text :disabled="!changed || saving" @click="Object.assign(form, settings)" />
      <Button label="Save" :loading="saving" @click="emit('save', { ...form })" />
    </div>
  </div>
</template>

<style scoped>
.rules {
  display: grid;
  gap: 1rem;
}

.card {
  padding: 1.25rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
}

.group {
  display: grid;
  gap: 0.9rem;
}

h2 {
  margin: 0;
  font-size: 1rem;
}

.grid {
  display: grid;
  align-items: start;
  grid-template-columns: repeat(auto-fill, minmax(15rem, 1fr));
  gap: 0.9rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

label {
  font-size: 0.875rem;
}

.sub {
  font-size: 0.8rem;
  color: #6b7280;
}

.switches {
  display: grid;
  gap: 0.6rem;
}

.switch {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  cursor: pointer;
}

/* always in reach on a long form */
.save-bar {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  box-shadow: 0 -2px 8px rgb(0 0 0 / 0.05);
}
</style>
