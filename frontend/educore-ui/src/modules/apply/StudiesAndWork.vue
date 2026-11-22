<script setup lang="ts">
import Button from "primevue/button";
import DatePicker from "primevue/datepicker";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { computed, reactive, watch } from "vue";
import { formatDate, fromIsoDate, toIsoDate } from "@/core/format";
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

/**
 * Saved rows show as one line; a row opens as a form when added, when Edit is clicked, or while it is incomplete.
 * Keys are "<list>-<index>".
 */
const opened = reactive(new Set<string>());
// saved: the parent hands over fresh lists, and every row folds back to its line
watch([prior, employment, referees], () => opened.clear());
const isOpen = (list: string, index: number, complete: boolean) => opened.has(`${list}-${index}`) || !complete;
const open = (list: string, index: number) => opened.add(`${list}-${index}`);
function removeRow<T>(rows: T[], list: string, index: number) {
  rows.splice(index, 1);
  // indexes after it shift: close them all rather than open the wrong one
  [...opened].filter((key) => key.startsWith(`${list}-`)).forEach((key) => opened.delete(key));
}

const priorDone = (r: PriorQualification) => Boolean(r.qualification && r.institution);
const jobDone = (r: Employment) => Boolean(r.employer && r.position && r.from_date);
const refereeDone = (r: Referee) => Boolean(r.full_name && r.email);

const priorLine = (r: PriorQualification) =>
  [r.qualification, r.institution, r.nqf_level ? `NQF ${r.nqf_level}` : "", r.year_completed ? String(r.year_completed) : "not finished", r.average != null ? `${r.average}%` : ""]
    .filter(Boolean)
    .join(" · ");
const jobLine = (r: Employment) => `${r.position}, ${r.employer} · ${formatDate(r.from_date)} to ${r.to_date ? formatDate(r.to_date) : "now"}`;
const refereeLine = (r: Referee) => [r.full_name, r.position, r.institution, r.email].filter(Boolean).join(" · ");

function addPrior() {
  prior.value.push({ qualification: "", institution: "", country: props.homeCountry, nqf_level: null, year_completed: null, average: null });
  open("prior", prior.value.length - 1);
}
function addJob() {
  employment.value.push({ employer: "", position: "", from_date: null, to_date: null, duties: null });
  open("job", employment.value.length - 1);
}
function addReferee() {
  referees.value.push({ full_name: "", position: null, institution: null, email: "", phone: null });
  open("ref", referees.value.length - 1);
}

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
        <small class="sub">As shown on your student card or academic record.</small>
      </div>
    </section>

    <!-- qualifications after school -->
    <section v-if="showPrior" class="block">
      <h2>{{ evidence === "Prior qualification" ? "Your qualifications" : "Your studies after school" }}</h2>
      <p class="sub">
        <template v-if="evidence === 'Prior qualification'">Your highest completed qualification first. The NQF level is on your certificate or academic record.</template>
        <template v-else>List all institutions attended, including incomplete studies. Credit is determined by the faculty.</template>
      </p>
      <template v-for="(row, index) in prior" :key="index">
      <div v-if="!isOpen('prior', index, priorDone(row))" class="row-line">
        <span>{{ priorLine(row) }}</span>
        <Button label="Edit" text size="small" :aria-label="`Edit qualification ${index + 1}`" @click="open('prior', index)" />
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove qualification ${index + 1}`" @click="removeRow(prior, 'prior', index)" />
      </div>
      <div v-else class="row-card">
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
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove qualification ${index + 1}`" @click="removeRow(prior, 'prior', index)" />
      </div>
      </template>
      <Button :label="prior.length ? 'Add another' : 'Add a qualification'" text @click="addPrior" />
    </section>

    <!-- work -->
    <section v-if="showWork" class="block">
      <h2>
        Your work experience
        <span v-if="workYears" class="sub">· {{ workYears }} years</span>
      </h2>
      <p class="sub">
        <template v-if="evidence === 'Work experience'">List your employment history, most recent first. Mature age applications are assessed on work experience.</template>
        <template v-else>If applicable. Some programmes require work experience.</template>
      </p>
      <template v-for="(row, index) in employment" :key="index">
      <div v-if="!isOpen('job', index, jobDone(row))" class="row-line">
        <span>{{ jobLine(row) }}</span>
        <Button label="Edit" text size="small" :aria-label="`Edit job ${index + 1}`" @click="open('job', index)" />
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove job ${index + 1}`" @click="removeRow(employment, 'job', index)" />
      </div>
      <div v-else class="row-card">
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
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove job ${index + 1}`" @click="removeRow(employment, 'job', index)" />
      </div>
      </template>
      <Button :label="employment.length ? 'Add another job' : 'Add a job'" text @click="addJob" />
    </section>

    <!-- referees -->
    <section v-if="showReferees" class="block">
      <h2>Referees <span class="sub">· {{ refereesRequired }} needed</span></h2>
      <p class="sub">Academic or professional referees, such as a lecturer or manager. The Admissions Office may contact them.</p>
      <template v-for="(row, index) in referees" :key="index">
      <div v-if="!isOpen('ref', index, refereeDone(row))" class="row-line">
        <span>{{ refereeLine(row) }}</span>
        <Button label="Edit" text size="small" :aria-label="`Edit referee ${index + 1}`" @click="open('ref', index)" />
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove referee ${index + 1}`" @click="removeRow(referees, 'ref', index)" />
      </div>
      <div v-else class="row-card">
        <div class="grid">
          <div class="field"><label :for="`ref-${index}`">Name</label><InputText :id="`ref-${index}`" v-model="row.full_name" fluid /></div>
          <div class="field"><label :for="`ref-pos-${index}`">Position</label><InputText :id="`ref-pos-${index}`" v-model="row.position" fluid /></div>
          <div class="field"><label :for="`ref-inst-${index}`">Institution or employer</label><InputText :id="`ref-inst-${index}`" v-model="row.institution" fluid /></div>
          <div class="field"><label :for="`ref-email-${index}`">Email</label><InputText :id="`ref-email-${index}`" v-model="row.email" type="email" fluid /></div>
          <div class="field"><label :for="`ref-phone-${index}`">Phone</label><InputText :id="`ref-phone-${index}`" v-model="row.phone" type="tel" fluid /></div>
        </div>
        <Button label="Remove" text severity="danger" size="small" :aria-label="`Remove referee ${index + 1}`" @click="removeRow(referees, 'ref', index)" />
      </div>
      </template>
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

.row-line {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem 0.5rem;
  padding: 0.35rem 0.6rem;
  border: 1px solid #f3f4f6;
  border-radius: 0.5rem;
  font-size: 0.9rem;
}

.row-line > span {
  flex: 1 1 16rem;
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
