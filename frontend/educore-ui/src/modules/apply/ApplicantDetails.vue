<script setup lang="ts">
import Checkbox from "primevue/checkbox";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { computed } from "vue";
import EcField from "@/core/ui/EcField.vue";
import PhoneField from "@/core/ui/PhoneField.vue";
import {
  type DetailsForm,
  FEE_PAYERS,
  GENDERS,
  KIN_RELATIONSHIPS,
  MARITAL_STATUSES,
  MINORITY_GROUPS,
  REGIONS,
  TITLES,
} from "./details";

/**
 * The applicant's particulars, in the groups Namibian universities' forms use: personal, identity and origin,
 * contact, next of kin, who pays the fees, and support needed. Citizens give their national ID and region of
 * origin; international applicants their passport and study permit. `staff`: worded for an officer typing in a
 * paper form ("the applicant" rather than "you").
 */
const props = withDefaults(
  defineProps<{
    international: boolean;
    dialCodes: { country: string; code: string }[];
    homeCountry: string;
    staff?: boolean;
  }>(),
  { staff: false },
);
const form = defineModel<DetailsForm>({ required: true });
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const badEmail = (v: string) => Boolean(v.trim()) && !EMAIL.test(v.trim());
const theyHave = computed(() => (props.staff ? "The applicant has" : "I have"));
const paidBySomeoneElse = computed(() => Boolean(form.value.educore_fee_payer) && form.value.educore_fee_payer !== "Self");
</script>

<template>
  <div class="details">
    <section class="group">
      <h3>Personal</h3>
      <div class="grid">
        <EcField label="Title" for="d-title"><Select v-model="form.educore_title" input-id="d-title" :options="TITLES" show-clear fluid /></EcField>
        <EcField label="First name(s)" for="d-first"><InputText id="d-first" v-model="form.first_name" fluid /></EcField>
        <EcField label="Middle name" for="d-middle"><InputText id="d-middle" v-model="form.middle_name" fluid /></EcField>
        <EcField label="Surname" for="d-last"><InputText id="d-last" v-model="form.last_name" fluid /></EcField>
        <EcField label="Previous surname" for="d-prev" hint="If changed, e.g. by marriage"><InputText id="d-prev" v-model="form.educore_previous_surname" fluid /></EcField>
        <EcField label="Date of birth" for="d-dob">
          <DatePicker v-model="form.date_of_birth" input-id="d-dob" date-format="dd-mm-yy" show-icon fluid :max-date="new Date()" />
        </EcField>
        <EcField label="Gender" for="d-gender"><Select v-model="form.gender" input-id="d-gender" :options="GENDERS" fluid /></EcField>
        <EcField label="Marital status" for="d-marital"><Select v-model="form.educore_marital_status" input-id="d-marital" :options="MARITAL_STATUSES" show-clear fluid /></EcField>
        <EcField label="Home language" for="d-lang"><InputText id="d-lang" v-model="form.educore_home_language" fluid /></EcField>
      </div>
    </section>

    <section class="group">
      <h3>Identity and origin</h3>
      <div class="grid">
        <EcField label="Nationality" for="d-nat">
          <InputText id="d-nat" v-model="form.nationality" fluid />
        </EcField>
        <template v-if="!international">
          <EcField label="National ID number" for="d-id"><InputText id="d-id" v-model="form.educore_national_id" inputmode="numeric" fluid /></EcField>
          <EcField label="Region of origin" for="d-region" hint="Where born and grew up">
            <Select v-model="form.educore_region_of_origin" input-id="d-region" :options="REGIONS" show-clear fluid />
          </EcField>
        </template>
        <template v-else>
          <EcField label="Passport number" for="d-passport"><InputText id="d-passport" v-model="form.educore_passport_number" fluid /></EcField>
          <EcField label="Passport expiry" for="d-passport-expiry">
            <DatePicker v-model="form.educore_passport_expiry" input-id="d-passport-expiry" date-format="dd-mm-yy" show-icon fluid />
          </EcField>
          <EcField label="Study permit number" for="d-permit" hint="Once issued"><InputText id="d-permit" v-model="form.educore_study_permit" fluid /></EcField>
        </template>
        <EcField label="Home town" for="d-town"><InputText id="d-town" v-model="form.educore_home_town" fluid /></EcField>
        <EcField v-if="!international" label="Designated minority group" for="d-minority" hint="For equity statistics">
          <Select v-model="form.educore_minority_group" input-id="d-minority" :options="MINORITY_GROUPS" show-clear fluid />
        </EcField>
      </div>
    </section>

    <section class="group">
      <h3>Contact</h3>
      <div class="grid">
        <slot name="email" />
        <EcField label="Mobile number" for="d-mobile"><PhoneField v-model="form.student_mobile_number" input-id="d-mobile" :dial-codes="dialCodes" :home-country="homeCountry" /></EcField>
        <EcField label="Other phone" for="d-phone2"><PhoneField v-model="form.educore_alternative_phone" input-id="d-phone2" :dial-codes="dialCodes" :home-country="homeCountry" /></EcField>
        <EcField label="Residential address" for="d-address"><InputText id="d-address" v-model="form.address_line_1" fluid /></EcField>
        <EcField label="Town / city" for="d-city"><InputText id="d-city" v-model="form.city" fluid /></EcField>
        <EcField label="Postal address" for="d-postal" hint="Not a school or hostel address">
          <InputText id="d-postal" v-model="form.educore_postal_address" fluid />
        </EcField>
      </div>
    </section>

    <section class="group">
      <h3>Next of kin</h3>
      <div class="grid">
        <EcField label="Relationship" for="d-kin-rel"><Select v-model="form.educore_kin_relationship" input-id="d-kin-rel" :options="KIN_RELATIONSHIPS" fluid /></EcField>
        <EcField label="Full name" for="d-kin-name"><InputText id="d-kin-name" v-model="form.educore_kin_name" fluid /></EcField>
        <EcField label="Phone" for="d-kin-phone"><PhoneField v-model="form.educore_kin_phone" input-id="d-kin-phone" :dial-codes="dialCodes" :home-country="homeCountry" /></EcField>
        <EcField label="Email" for="d-kin-email" :error="badEmail(form.educore_kin_email) ? 'Not a valid email address' : undefined">
          <InputText id="d-kin-email" v-model="form.educore_kin_email" type="email" fluid :invalid="badEmail(form.educore_kin_email)" />
        </EcField>
        <EcField label="Address" for="d-kin-address"><InputText id="d-kin-address" v-model="form.educore_kin_address" fluid /></EcField>
      </div>
    </section>

    <section class="group">
      <h3>Fees</h3>
      <div class="grid">
        <EcField label="Who pays the fees" for="d-payer"><Select v-model="form.educore_fee_payer" input-id="d-payer" :options="FEE_PAYERS" fluid /></EcField>
        <template v-if="paidBySomeoneElse">
          <EcField label="Name of person or institution" for="d-payer-name" hint="E.g. NSFAF, an employer or a parent">
            <InputText id="d-payer-name" v-model="form.educore_fee_payer_name" fluid />
          </EcField>
          <EcField label="Their email" for="d-payer-email" :error="badEmail(form.educore_fee_payer_email) ? 'Not a valid email address' : undefined">
            <InputText id="d-payer-email" v-model="form.educore_fee_payer_email" type="email" fluid :invalid="badEmail(form.educore_fee_payer_email)" />
          </EcField>
          <EcField label="Their phone" for="d-payer-phone">
            <PhoneField v-model="form.educore_fee_payer_phone" input-id="d-payer-phone" :dial-codes="dialCodes" :home-country="homeCountry" />
          </EcField>
        </template>
      </div>
    </section>

    <section class="group">
      <h3>Support</h3>
      <div class="check">
        <Checkbox v-model="form.educore_disability" input-id="d-disability" binary />
        <label for="d-disability">{{ theyHave }} a disability or impairment</label>
      </div>
      <EcField v-if="form.educore_disability" label="Support needed" for="d-needs" hint="Used to plan support only; not part of the decision">
        <Textarea id="d-needs" v-model="form.educore_support_needs" rows="2" auto-resize fluid />
      </EcField>
    </section>
  </div>
</template>

<style scoped>
.details {
  display: grid;
  gap: 1.5rem;
}

.group {
  display: grid;
  gap: 0.75rem;
}

h3 {
  margin: 0;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--ec-border-soft);
  color: var(--ec-ink);
  font-size: 0.9rem;
  font-weight: 650;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 14rem), 1fr));
  gap: 0.9rem 1rem;
  align-items: start;
}

.check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>
