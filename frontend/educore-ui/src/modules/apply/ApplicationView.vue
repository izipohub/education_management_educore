<script setup lang="ts">
import AutoComplete from "primevue/autocomplete";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { formatDate, fromIsoDate, toIsoDate } from "@/core/format";
import FeePanel from "./FeePanel.vue";
import {
  type Application,
  type ApplyOptions,
  type DraftChanges,
  LEVELS,
  type Level,
  type Result,
  type School,
  findSchools,
  getOptions,
  myApplication,
  removeDocument,
  saveDraft,
  submitApplication,
  uploadDocument,
} from "./api";

const toast = useToast();
const GENDERS = ["Female", "Male", "Other", "Prefer not to say"];

const options = ref<ApplyOptions | null>(null);
const app = ref<Application | null>(null);
const loading = ref(true);
const loadError = ref("");
const saving = ref(false);

type Step = "personal" | "school" | "choices" | "documents" | "submit";
const step = ref<Step>("personal");
const ORDER: Step[] = ["personal", "school", "choices", "documents", "submit"];
/** the top of the step area: brought into view on every step change, so nobody scrolls back up */
const stepTop = ref<HTMLElement | null>(null);
watch(step, () => {
  requestAnimationFrame(() => stepTop.value?.scrollIntoView({ behavior: "smooth", block: "start" }));
});
function go(offset: number) {
  const index = ORDER.indexOf(step.value) + offset;
  if (index >= 0 && index < ORDER.length) step.value = ORDER[index]!;
}
const steps = computed(() => {
  const list: { label: string; value: Step }[] = [
    { label: "1 · About you", value: "personal" },
    { label: app.value?.pathway === "International" ? "2 · School" : "2 · School and results", value: "school" },
    { label: "3 · Programmes", value: "choices" },
    { label: "4 · Documents", value: "documents" },
    { label: "5 · Submit", value: "submit" },
  ];
  return list;
});

async function load() {
  loading.value = true;
  try {
    [options.value, app.value] = await Promise.all([getOptions(), myApplication()]);
    resetForms();
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);

async function save(changes: DraftChanges, message = "Saved") {
  saving.value = true;
  try {
    app.value = await saveDraft(changes);
    resetForms();
    toast.add({ severity: "success", summary: message, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    saving.value = false;
  }
}

// --- starting ------------------------------------------------------------------------------------------

const start = reactive({ intake: "", pathway: "School leaver" as Application["pathway"] });
watch(options, (o) => {
  if (o?.intakes.length && !start.intake) start.intake = o.intakes[0]!.name;
});

async function startApplication() {
  await save({ intake: start.intake, pathway: start.pathway }, "Application started");
}

// --- the forms, copied from the application so edits can be saved or dropped ---------------------------

const personal = reactive({
  first_name: "",
  middle_name: "",
  last_name: "",
  date_of_birth: null as Date | null,
  gender: "",
  nationality: "Namibian",
  student_mobile_number: "",
  address_line_1: "",
  city: "",
  pathway: "School leaver" as Application["pathway"],
});
const school = reactive({
  selected: null as School | null,
  notListed: false,
  typedName: "",
  typedTown: "",
  examNumber: "",
  examYear: null as number | null,
});
const results = ref<Result[]>([]);
const choices = ref<(string | null)[]>([null, null, null]);

function resetForms() {
  const a = app.value;
  if (!a) return;
  const p = a.personal;
  Object.assign(personal, {
    first_name: p.first_name ?? "",
    middle_name: p.middle_name ?? "",
    last_name: p.last_name ?? "",
    date_of_birth: p.date_of_birth ? fromIsoDate(p.date_of_birth) : null,
    gender: p.gender ?? "",
    nationality: p.nationality ?? "Namibian",
    student_mobile_number: p.student_mobile_number ?? "",
    address_line_1: p.address_line_1 ?? "",
    city: p.city ?? "",
    pathway: a.pathway,
  });
  Object.assign(school, {
    selected: a.school,
    notListed: false,
    typedName: "",
    typedTown: "",
    examNumber: a.exam_number ?? "",
    examYear: a.exam_year,
  });
  results.value = a.results.map((r) => ({ ...r }));
  if (!results.value.length) results.value = [{ subject: "", level: "NSSCO", grade: "" }];
  const max = options.value?.max_choices ?? 3;
  choices.value = Array.from({ length: max }, (_, i) => a.choices[i]?.offering ?? null);
}

async function savePersonal() {
  const ok = await save({
    pathway: personal.pathway,
    personal: {
      first_name: personal.first_name,
      middle_name: personal.middle_name,
      last_name: personal.last_name,
      date_of_birth: personal.date_of_birth ? toIsoDate(personal.date_of_birth) : null,
      gender: personal.gender || null,
      nationality: personal.nationality,
      student_mobile_number: personal.student_mobile_number,
      address_line_1: personal.address_line_1,
      city: personal.city,
    },
  });
  if (ok) step.value = "school";
}

// school search
const schoolSuggestions = ref<School[]>([]);
async function searchSchools(event: { query: string }) {
  schoolSuggestions.value = await findSchools(event.query).catch(() => []);
}
const schoolLabel = (s: School) => `${s.school_name}${s.town ? `, ${s.town}` : ""}`;

const gradesFor = (level: Level) => options.value?.grades[level] ?? [];
const levels = computed(() => LEVELS.filter((l) => gradesFor(l).length));

function addResult() {
  results.value.push({ subject: "", level: "NSSCO", grade: "" });
}

async function saveSchool() {
  const chosen = school.notListed
    ? { school_name: school.typedName.trim(), town: school.typedTown.trim() }
    : school.selected
      ? { name: school.selected.name }
      : null;
  const ok = await save({
    school: chosen,
    exam_number: school.examNumber.trim() || null,
    exam_year: school.examYear,
    results: results.value.filter((r) => r.subject && r.level && r.grade),
  });
  if (ok) step.value = "choices";
}

// choices
const offeringOptions = computed(() =>
  (options.value?.offerings ?? []).map((o) => ({
    value: o.name,
    label: `${o.program} — ${o.campus.replace(" Campus", "")}, ${o.mode_of_study}`,
  })),
);
const offeringByName = computed(() => new Map((options.value?.offerings ?? []).map((o) => [o.name, o])));
function requirementText(name: string | null) {
  const o = name ? offeringByName.value.get(name) : undefined;
  if (!o) return "";
  const parts = [o.min_points ? `at least ${o.min_points} points` : ""].concat(
    o.subject_requirements.map((r) => `${r.subject} at least ${r.grade} (${r.level})`),
  );
  return parts.filter(Boolean).join("; ");
}
function eligibilityFor(name: string | null) {
  return app.value?.choices.find((c) => c.offering === name);
}
function eligibilitySeverity(value: string | null | undefined) {
  return value === "Meets requirements" ? "success" : value === "Does not meet requirements" ? "danger" : "warn";
}

async function saveChoices() {
  const chosen = choices.value.filter((c): c is string => Boolean(c));
  const ok = await save({ choices: chosen });
  if (ok) step.value = "documents";
}

// documents
const certifiedOn = reactive<Record<string, Date | null>>({});
const pendingFile = reactive<Record<string, File | null>>({});
const uploading = ref<string | null>(null);
const mustBeCertified = (name: string) =>
  Boolean(options.value?.documents.find((d) => d.name === name)?.must_be_certified);
const guidance = (name: string) => options.value?.documents.find((d) => d.name === name)?.description ?? "";

function pickFile(name: string, event: Event) {
  const input = event.target as HTMLInputElement;
  pendingFile[name] = input.files?.[0] ?? null;
}

async function upload(name: string) {
  const file = pendingFile[name];
  if (!file) return;
  const max = (options.value?.max_file_size_mb ?? 5) * 1024 * 1024;
  if (file.size > max) {
    toast.add({ severity: "error", summary: `${file.name} is larger than ${options.value?.max_file_size_mb} MB`, life: 6000 });
    return;
  }
  uploading.value = name;
  try {
    const certified = certifiedOn[name] ? toIsoDate(certifiedOn[name]!) : null;
    app.value = await uploadDocument(name, file, certified);
    pendingFile[name] = null;
    toast.add({ severity: "success", summary: `${name} uploaded`, life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not uploaded", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    uploading.value = null;
  }
}

async function remove(name: string) {
  try {
    app.value = await removeDocument(name);
  } catch (e) {
    toast.add({ severity: "error", summary: "Not removed", detail: e instanceof Error ? e.message : String(e), life: 6000 });
  }
}

// submitting
const declared = ref(false);
async function submit() {
  saving.value = true;
  try {
    app.value = await submitApplication();
    toast.add({ severity: "success", summary: "Your application is submitted", life: 5000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not submitted", detail: e instanceof Error ? e.message : String(e), life: 10000 });
  } finally {
    saving.value = false;
  }
}

const statusSeverity = computed(() =>
  ({ Draft: "secondary", Applied: "info", Approved: "success", Rejected: "danger", Admitted: "success" })[
    app.value?.status ?? "Draft"
  ],
);
const statusText = computed(
  () =>
    ({
      Draft: "Draft: not submitted yet",
      Applied: "Submitted: being reviewed",
      Approved: "Offered a place",
      Rejected: "Not successful",
      Admitted: "Admitted",
    })[app.value?.status ?? "Draft"],
);
</script>

<template>
  <section class="application">
    <div v-if="loading" class="loading"><ProgressSpinner style="width: 2.5rem; height: 2.5rem" aria-label="Loading" /></div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <!-- no application yet -->
    <article v-else-if="!app" class="card start">
      <h1>Start your application</h1>
      <template v-if="options?.intakes.length">
        <div class="field">
          <label for="intake">Intake</label>
          <Select
            v-model="start.intake"
            input-id="intake"
            :options="options.intakes"
            option-label="title"
            option-value="name"
            fluid
          />
        </div>
        <div class="field">
          <label>Which describes you?</label>
          <SelectButton
            v-model="start.pathway"
            :options="['School leaver', 'International']"
            :allow-empty="false"
            aria-label="Pathway"
          />
          <small class="sub">School leaver: you have Namibian NSSC results. International: your school qualifications are from another country.</small>
        </div>
        <Button label="Start application" :loading="saving" :disabled="!start.intake" @click="startApplication" />
      </template>
      <Message v-else severity="info" :closable="false">Applications are closed at the moment.</Message>
    </article>

    <!-- the application -->
    <template v-else>
      <header class="head">
        <div>
          <h1>Your application</h1>
          <p class="sub">{{ app.intake }} · {{ app.name }}</p>
        </div>
        <Tag :severity="statusSeverity" :value="statusText" />
      </header>
      <Message v-if="options?.scale_is_placeholder" severity="warn" :closable="false" class="note">
        Demo: points use a sample scale, not the university's published one.
      </Message>

      <!-- submitted: read only -->
      <template v-if="!app.editable">
        <article class="card">
          <p v-if="app.submitted_on">Submitted on {{ formatDate(app.submitted_on) }}. The admissions office reviews your documents and results; you will see their decision here.</p>
          <Message v-if="app.decision_reason" severity="error" :closable="false">{{ app.decision_reason }}</Message>
          <h2>Your choices</h2>
          <ol class="choice-list">
            <li v-for="c in app.choices" :key="c.offering">{{ c.program }} — {{ c.campus }}</li>
          </ol>
          <h2>Documents</h2>
          <ul class="doc-list">
            <li v-for="d in app.documents.filter((x) => x.uploaded)" :key="d.document_type">
              {{ d.document_type }} <Tag :value="d.status ?? ''" :severity="d.status === 'Verified' ? 'success' : d.status === 'Rejected' ? 'danger' : 'secondary'" />
              <template v-if="d.status === 'Rejected'">
                <p class="rejected">Not accepted: {{ d.rejection_reason }}. Upload a new certified copy.</p>
                <div class="upload">
                  <DatePicker
                    v-if="mustBeCertified(d.document_type)"
                    v-model="certifiedOn[d.document_type]"
                    date-format="dd-mm-yy"
                    placeholder="Date certified"
                    show-icon
                    :max-date="new Date()"
                    :aria-label="`Date ${d.document_type} was certified`"
                  />
                  <input type="file" accept=".pdf,.jpg,.jpeg,.png" :aria-label="`File for ${d.document_type}`" @change="pickFile(d.document_type, $event)" />
                  <Button
                    label="Upload"
                    size="small"
                    :loading="uploading === d.document_type"
                    :disabled="!pendingFile[d.document_type] || (mustBeCertified(d.document_type) && !certifiedOn[d.document_type])"
                    @click="upload(d.document_type)"
                  />
                </div>
              </template>
            </li>
          </ul>
        </article>
        <article v-if="app.fee.amount" class="card fee-card">
          <FeePanel :fee="app.fee" />
        </article>
      </template>

      <!-- draft: the steps -->
      <div v-else class="layout">
        <aside class="checklist card">
          <h2>Still needed</h2>
          <p v-if="!app.missing.length" class="ready">✓ Complete: ready to submit</p>
          <ul v-else>
            <li v-for="gap in app.missing" :key="gap">{{ gap }}</li>
          </ul>
          <p v-if="app.fee.amount" class="points">
            Application fee: <strong>{{ app.fee.status === 'Unpaid' ? 'not received yet' : app.fee.status.toLowerCase() }}</strong>
          </p>
          <p v-if="app.points !== null && app.pathway !== 'International'" class="points">
            Your points: <strong>{{ app.points }}</strong>
            <span class="sub"> (best {{ options?.best_subjects }} subjects)</span>
          </p>
        </aside>

        <div ref="stepTop" class="main">
          <SelectButton v-model="step" :options="steps" option-label="label" option-value="value" :allow-empty="false" aria-label="Steps" class="steps" />

          <!-- 1 about you -->
          <article v-if="step === 'personal'" class="card form">
            <div class="grid">
              <div class="field"><label for="fn">First name</label><InputText id="fn" v-model="personal.first_name" fluid /></div>
              <div class="field"><label for="mn">Middle name</label><InputText id="mn" v-model="personal.middle_name" fluid /></div>
              <div class="field"><label for="ln">Last name</label><InputText id="ln" v-model="personal.last_name" fluid /></div>
              <div class="field">
                <label for="dob">Date of birth</label>
                <DatePicker v-model="personal.date_of_birth" input-id="dob" date-format="dd-mm-yy" show-icon fluid :max-date="new Date()" />
              </div>
              <div class="field"><label for="gender">Gender</label><Select v-model="personal.gender" input-id="gender" :options="GENDERS" fluid /></div>
              <div class="field"><label for="nat">Nationality</label><InputText id="nat" v-model="personal.nationality" fluid /></div>
              <div class="field"><label for="mobile">Mobile number</label><InputText id="mobile" v-model="personal.student_mobile_number" type="tel" fluid /></div>
              <div class="field"><label for="address">Address</label><InputText id="address" v-model="personal.address_line_1" fluid /></div>
              <div class="field"><label for="city">Town / city</label><InputText id="city" v-model="personal.city" fluid /></div>
            </div>
            <div class="field">
              <label>Pathway</label>
              <SelectButton v-model="personal.pathway" :options="['School leaver', 'International']" :allow-empty="false" aria-label="Pathway" />
            </div>
            <div class="step-nav"><Button label="Save and continue" :loading="saving" @click="savePersonal" /></div>
          </article>

          <!-- 2 school and results -->
          <article v-else-if="step === 'school'" class="card form">
            <div class="field">
              <label for="school">Secondary school</label>
              <AutoComplete
                v-if="!school.notListed"
                v-model="school.selected"
                input-id="school"
                :suggestions="schoolSuggestions"
                :option-label="schoolLabel"
                placeholder="Type at least two letters of your school or town"
                fluid
                @complete="searchSchools"
              />
              <div class="check">
                <Checkbox v-model="school.notListed" input-id="not-listed" binary />
                <label for="not-listed">My school is not in the list</label>
              </div>
              <div v-if="school.notListed" class="grid">
                <div class="field"><label for="typed-school">School name</label><InputText id="typed-school" v-model="school.typedName" fluid /></div>
                <div class="field"><label for="typed-town">Town</label><InputText id="typed-town" v-model="school.typedTown" fluid /></div>
              </div>
            </div>
            <template v-if="app.pathway !== 'International'">
              <div class="grid">
                <div class="field"><label for="exam-no">Examination number</label><InputText id="exam-no" v-model="school.examNumber" fluid /></div>
                <div class="field">
                  <label for="exam-year">Year of your latest results</label>
                  <InputText id="exam-year" :model-value="school.examYear ? String(school.examYear) : ''" inputmode="numeric" fluid @update:model-value="(v) => (school.examYear = v ? Number(v) : null)" />
                </div>
              </div>
              <h2>Results</h2>
              <p class="sub">Every subject on your latest NSSC statement. Your points are the best {{ options?.best_subjects }} subjects.</p>
              <div v-for="(result, index) in results" :key="index" class="result">
                <Select v-model="result.subject" :options="options?.subjects ?? []" placeholder="Subject" filter :aria-label="`Subject ${index + 1}`" class="subject" />
                <Select v-model="result.level" :options="levels" :aria-label="`Level ${index + 1}`" @change="result.grade = ''" />
                <Select v-model="result.grade" :options="gradesFor(result.level)" placeholder="Grade" :aria-label="`Grade ${index + 1}`" />
                <span class="sub pts">{{ result.points != null ? `${result.points} pts` : "" }}</span>
                <Button text severity="secondary" :aria-label="`Remove result ${index + 1}`" label="✕" @click="results.splice(index, 1)" />
              </div>
              <Button label="Add a subject" text @click="addResult" />
            </template>
            <Message v-else severity="info" :closable="false">The admissions office assesses foreign qualifications: upload them with your documents.</Message>
            <div class="step-nav">
              <Button label="Back" severity="secondary" text @click="go(-1)" />
              <Button label="Save and continue" :loading="saving" @click="saveSchool" />
            </div>
          </article>

          <!-- 3 programmes -->
          <article v-else-if="step === 'choices'" class="card form">
            <p class="sub">Up to {{ options?.max_choices }} programmes, in order of preference. Your first choice is considered first.</p>
            <div v-for="(_, index) in choices" :key="index" class="field choice">
              <label :for="`choice-${index}`">Choice {{ index + 1 }}</label>
              <Select
                v-model="choices[index]"
                :input-id="`choice-${index}`"
                :options="offeringOptions"
                option-label="label"
                option-value="value"
                :placeholder="index === 0 ? 'Choose a programme' : 'Optional'"
                show-clear
                filter
                fluid
              />
              <small v-if="choices[index]" class="sub">Entry: {{ requirementText(choices[index]) }}</small>
              <div v-if="eligibilityFor(choices[index])" class="eligibility">
                <Tag :severity="eligibilitySeverity(eligibilityFor(choices[index])?.eligibility)" :value="eligibilityFor(choices[index])?.eligibility ?? ''" />
                <span class="sub">{{ eligibilityFor(choices[index])?.eligibility_note }}</span>
              </div>
            </div>
            <p class="sub">Eligibility is a first check on your results; the admissions office decides.</p>
            <div class="step-nav">
              <Button label="Back" severity="secondary" text @click="go(-1)" />
              <Button label="Save and continue" :loading="saving" @click="saveChoices" />
            </div>
          </article>

          <!-- 4 documents -->
          <article v-else-if="step === 'documents'" class="card form">
            <p class="sub">
              Certified copies, certified within the last {{ options?.certification_max_age_months }} months, scanned as PDF, JPG or PNG (up to
              {{ options?.max_file_size_mb }} MB each).
            </p>
            <div v-for="doc in app.documents" :key="doc.document_type" class="document">
              <div class="doc-head">
                <strong>{{ doc.document_type }}</strong>
                <Tag :value="doc.required ? 'Required' : 'If it applies'" :severity="doc.required ? 'warn' : 'secondary'" />
              </div>
              <p v-if="guidance(doc.document_type)" class="sub">{{ guidance(doc.document_type) }}</p>
              <div v-if="doc.uploaded" class="uploaded">
                <a :href="doc.file_url ?? '#'" target="_blank" rel="noopener">{{ doc.file_name }}</a>
                <span v-if="doc.certified_on" class="sub">certified {{ formatDate(doc.certified_on) }}</span>
                <Tag :value="doc.status ?? ''" severity="secondary" />
                <Button label="Remove" text severity="danger" size="small" @click="remove(doc.document_type)" />
              </div>
              <div class="upload">
                <DatePicker
                  v-if="mustBeCertified(doc.document_type)"
                  v-model="certifiedOn[doc.document_type]"
                  date-format="dd-mm-yy"
                  placeholder="Date certified"
                  show-icon
                  :max-date="new Date()"
                  :aria-label="`Date ${doc.document_type} was certified`"
                />
                <input
                  type="file"
                  accept=".pdf,.jpg,.jpeg,.png"
                  :aria-label="`File for ${doc.document_type}`"
                  @change="pickFile(doc.document_type, $event)"
                />
                <Button
                  :label="doc.uploaded ? 'Replace' : 'Upload'"
                  size="small"
                  :loading="uploading === doc.document_type"
                  :disabled="!pendingFile[doc.document_type] || (mustBeCertified(doc.document_type) && !certifiedOn[doc.document_type])"
                  @click="upload(doc.document_type)"
                />
              </div>
            </div>
            <div class="step-nav">
              <Button label="Back" severity="secondary" text @click="go(-1)" />
              <Button label="Continue" @click="go(1)" />
            </div>
          </article>

          <!-- 5 submit -->
          <article v-else class="card form">
            <h2>Check and submit</h2>
            <ul class="summary">
              <li>{{ app.personal.first_name }} {{ app.personal.last_name }} · {{ app.personal.student_email_id }}</li>
              <li v-if="app.school">{{ app.school.school_name }}<template v-if="app.points !== null"> · {{ app.points }} points</template></li>
              <li v-for="c in app.choices" :key="c.offering">Choice {{ c.rank }}: {{ c.program }} — {{ c.campus }}</li>
              <li>{{ app.documents.filter((d) => d.uploaded).length }} documents uploaded</li>
            </ul>
            <FeePanel v-if="app.fee.amount" :fee="app.fee" />
            <Message v-if="app.missing.length" severity="warn" :closable="false">
              Not complete yet: {{ app.missing.join("; ") }}
            </Message>
            <div class="check">
              <Checkbox v-model="declared" input-id="declaration" binary />
              <label for="declaration">
                I declare that the information I have given is true and complete, and that my documents are true copies. I understand
                that a false declaration may cancel my application or my studies.
              </label>
            </div>
            <div class="step-nav">
              <Button label="Back" severity="secondary" text @click="go(-1)" />
              <Button label="Submit application" :loading="saving" :disabled="!declared || app.missing.length > 0" @click="submit" />
            </div>
          </article>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.loading {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

h2 {
  margin: 1rem 0 0.5rem;
  font-size: 1rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.note {
  margin-bottom: 1rem;
}

.card {
  padding: 1.25rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
}

.start {
  max-width: 36rem;
  display: grid;
  gap: 1rem;
}

.layout {
  display: grid;
  grid-template-columns: 16rem minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}

.checklist h2 {
  margin-top: 0;
}

.checklist ul {
  margin: 0;
  padding-left: 1.1rem;
  font-size: 0.9rem;
}

.ready {
  color: #15803d;
  font-weight: 600;
}

.points {
  margin: 1rem 0 0;
}

.main {
  scroll-margin-top: 0.5rem;
}

/* always reachable: the step bar stays at the top of the screen while scrolling */
.steps {
  position: sticky;
  top: 0;
  z-index: 2;
  margin-bottom: 1rem;
  flex-wrap: wrap;
  box-shadow: 0 2px 6px rgb(0 0 0 / 0.06);
}

.step-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.form {
  display: grid;
  gap: 1rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.9rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

label {
  font-size: 0.875rem;
}

.check {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
}

.result {
  display: grid;
  grid-template-columns: minmax(10rem, 2fr) 8.5rem 6rem 3.5rem auto;
  align-items: center;
  gap: 0.5rem;
}

.eligibility {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.document {
  padding: 0.9rem 0;
  border-top: 1px solid #f3f4f6;
}

.doc-head,
.uploaded,
.upload {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}

.uploaded,
.upload {
  margin-top: 0.5rem;
}

.summary,
.choice-list,
.doc-list {
  margin: 0;
  padding-left: 1.1rem;
}

.rejected {
  margin: 0.25rem 0;
  color: #b91c1c;
  font-size: 0.9rem;
}

.fee-card {
  margin-top: 1rem;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }

  .result {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
