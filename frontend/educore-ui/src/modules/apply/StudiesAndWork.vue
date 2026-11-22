<script setup lang="ts">
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { computed } from "vue";
import { fromIsoDate, toIsoDate } from "@/core/format";
import type { Employment, Evidence, PriorQualification, Referee } from "./api";

/** The evidence a pathway is judged on, besides school results: what applies is set by the pathway */
const props = defineProps<{
  evidence: Evidence;
  refereesRequired: number;
  homeCountry: string;
  countries: string[];
  workYears: number | null;
}>();
const prior = defineModel<PriorQualification[]>("prior", { required: true });
const employment = defineModel<Employment[]>("employment", { required: true });
const referees = defineModel<Referee[]>("referees", { required: true });
const previousNumber = defineModel<string>("previousNumber", { required: true });

const showPrior = computed(() => props.evidence === "Prior qualification" || props.evidence === "Studies elsewhere");
const showWork = computed(() => props.evidence === "Work experience" || props.evidence === "Prior qualification");
const showReferees = computed(() => props.refereesRequired > 0);
const thisYear = new Date().getFullYear();

const addPrior = () =>
  prior.value.push({ qualification: "", institution: "", country: props.homeCountry, nqf_level: null, year_completed: null, average: null });
const addJob = () => employment.value.push({ employer: "", position: "", from_date: null, to_date: null, duties: null });
const addReferee = () => referees.value.push({ full_name: "", position: null, institution: null, email: "", phone: null });

const date = (value: string | null) => (value ? fromIsoDate(value) : null);
const iso = (value: Date | Date[] | (Date | null)[] | null | undefined) => (value instanceof Date ? toIsoDate(value) : null);
</script>

<template>
  <div class="evidence">
    <!-- resumption -->
    <section v-if="evidence === 'Studies here'" class="block">
      <h2>Your earlier studies here</h2>
      <div class="field narrow">
        <label for="previous-number">Your student number</label>
        <InputText id="previous-number" v-model="previousNumber" fluid />
        <small class="sub">From your student card or an old statement. Admissions checks your record and standing.</small>
      </div>
    </section>

    <!-- qualifications after school -->
    <section v-if="showPrior" class="block">
      <h2>{{ evidence === "Prior qualification" ? "Your qualifications" : "Your studies after school" }}</h2>
      <p class="sub">
        <template v-if="evidence === 'Prior qualification'">Your highest completed qualification first. The NQF level is on your certificate or academic record.</template>
        <template v-else>Every university or college you studied at, finished or not: the faculty decides which courses earn credit.</template>
      </p>
      <div v-for="(row, index) in prior" :key="index" class="row-card">
        <div class="grid">
          <div class="field"><label :for="`q-${index}`">Qualification</label><InputText :id="`q-${index}`" v-model="row.qualification" placeholder="e.g. Bachelor of Commerce" fluid /></div>
          <div class="field"><label :for="`inst-${index}`">Institution</label><InputText :id="`inst-${index}`" v-model="row.institution" fluid /></div>
          <div class="field">
            <label :for="`country-${index}`">Country</label>
            <Select v-model="row.country" :input-id="`country-${index}`" :options="countries" filter fluid />
          </div>
          <div class="field">
            <label :for="`nqf-${index}`">NQF level</label>
            <InputNumber v-model="row.nqf_level" :input-id="`nqf-${index}`" :min="1" :max="10" :use-grouping="false" fluid />
          </div>
          <div class="field">
            <label :for="`year-${index}`">Year completed</label>
            <InputNumber v-model="row.year_completed" :input-id="`year-${index}`" :min="1960" :max="thisYear" :use-grouping="false" placeholder="Empty: not finished" fluid />
          </div>
          <div class="field">
            <label :for="`avg-${index}`">Average (%)</label>
            <InputNumber v-model="row.average" :input-id="`avg-${index}`" :min="0" :max="100" :max-fraction-digits="1" suffix="%" fluid />
          </div>
        </div>
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove qualification ${index + 1}`" @click="prior.splice(index, 1)" />
      </div>
      <Button :label="prior.length ? 'Add another' : 'Add a qualification'" text @click="addPrior" />
    </section>

    <!-- work -->
    <section v-if="showWork" class="block">
      <h2>
        Your work experience
        <span v-if="workYears" class="sub">· {{ workYears }} years</span>
      </h2>
      <p class="sub">
        <template v-if="evidence === 'Work experience'">Every job, most recent first: mature age entry is decided on your experience.</template>
        <template v-else>If you have worked: some programmes ask for experience.</template>
      </p>
      <div v-for="(row, index) in employment" :key="index" class="row-card">
        <div class="grid">
          <div class="field"><label :for="`emp-${index}`">Employer</label><InputText :id="`emp-${index}`" v-model="row.employer" fluid /></div>
          <div class="field"><label :for="`pos-${index}`">Position</label><InputText :id="`pos-${index}`" v-model="row.position" fluid /></div>
          <div class="field">
            <label :for="`from-${index}`">From</label>
            <DatePicker :model-value="date(row.from_date)" :input-id="`from-${index}`" date-format="dd-mm-yy" show-icon fluid :max-date="new Date()" @update:model-value="(v) => (row.from_date = iso(v))" />
          </div>
          <div class="field">
            <label :for="`to-${index}`">To</label>
            <DatePicker :model-value="date(row.to_date)" :input-id="`to-${index}`" date-format="dd-mm-yy" show-icon fluid placeholder="Empty: current job" @update:model-value="(v) => (row.to_date = iso(v))" />
          </div>
        </div>
        <div class="field"><label :for="`duties-${index}`">Main duties</label><Textarea :id="`duties-${index}`" v-model="row.duties" rows="2" auto-resize fluid /></div>
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove job ${index + 1}`" @click="employment.splice(index, 1)" />
      </div>
      <Button :label="employment.length ? 'Add another job' : 'Add a job'" text @click="addJob" />
    </section>

    <!-- referees -->
    <section v-if="showReferees" class="block">
      <h2>Referees <span class="sub">· {{ refereesRequired }} needed</span></h2>
      <p class="sub">People who know your studies or work, such as a lecturer or manager. Admissions may contact them.</p>
      <div v-for="(row, index) in referees" :key="index" class="row-card">
        <div class="grid">
          <div class="field"><label :for="`ref-${index}`">Name</label><InputText :id="`ref-${index}`" v-model="row.full_name" fluid /></div>
          <div class="field"><label :for="`ref-pos-${index}`">Position</label><InputText :id="`ref-pos-${index}`" v-model="row.position" fluid /></div>
          <div class="field"><label :for="`ref-inst-${index}`">Institution or employer</label><InputText :id="`ref-inst-${index}`" v-model="row.institution" fluid /></div>
          <div class="field"><label :for="`ref-email-${index}`">Email</label><InputText :id="`ref-email-${index}`" v-model="row.email" type="email" fluid /></div>
          <div class="field"><label :for="`ref-phone-${index}`">Phone</label><InputText :id="`ref-phone-${index}`" v-model="row.phone" type="tel" fluid /></div>
        </div>
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove referee ${index + 1}`" @click="referees.splice(index, 1)" />
      </div>
      <Button v-if="referees.length < Math.max(refereesRequired, 3)" label="Add a referee" text @click="addReferee" />
    </section>
  </div>
</template>

<style scoped>
.evidence {
  display: grid;
  gap: 1.25rem;
}

.block {
  display: grid;
  gap: 0.6rem;
  justify-items: start;
}

.block > * {
  justify-self: stretch;
}

.block > .p-button {
  justify-self: start;
}

h2 {
  margin: 0;
  font-size: 1rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 400;
  color: #6b7280;
}

.row-card {
  display: grid;
  gap: 0.6rem;
  justify-items: start;
  padding: 0.9rem;
  background: #f9fafb;
  border: 1px solid #f3f4f6;
  border-radius: 0.5rem;
}

.row-card > .grid,
.row-card > .field {
  justify-self: stretch;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(13rem, 1fr));
  gap: 0.75rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

.narrow {
  max-width: 20rem;
}

label {
  font-size: 0.875rem;
}
</style>
