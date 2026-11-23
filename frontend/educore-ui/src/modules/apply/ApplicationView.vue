<script setup lang="ts">
import EcField from "@/core/ui/EcField.vue";
import ApplicantDetails from "./ApplicantDetails.vue";
import { type DetailsForm, detailsFrom, detailsToApi, emptyDetails } from "./details";
import StatusTag from "@/core/ui/StatusTag.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
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
import { eligibilityLabel } from "@/core/status";
import { formatDate, toIsoDate } from "@/core/format";
import FeePanel from "./FeePanel.vue";
import OfferPanel from "./OfferPanel.vue";
import StudiesAndWork from "./StudiesAndWork.vue";
import {
  type Application,
  type ApplyOptions,
  type DraftChanges,
  type Employment,
  type Evidence,
  type Pathway,
  type PriorQualification,
  type Referee,
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
const pathwayByName = computed(() => new Map((options.value?.pathways ?? []).map((p) => [p.name, p])));
const pathway = computed<Pathway | undefined>(() => (app.value?.pathway ? pathwayByName.value.get(app.value.pathway) : undefined));
const evidence = computed<Evidence>(() => pathway.value?.evidence ?? "School results");
/** school details and NSSC results: school leavers and transfers from home schools */
const usesSchool = computed(() => ["School results", "Studies elsewhere"].includes(evidence.value));
const usesResults = computed(() => usesSchool.value && !app.value?.international);
const STEP_TWO: Record<Evidence, string> = {
  "School results": "School and results",
  "Studies elsewhere": "School and studies",
  "Work experience": "Work experience",
  "Studies here": "Earlier studies",
  "Prior qualification": "Qualifications",
};
const steps = computed(() => {
  const list: { label: string; value: Step }[] = [
    { label: "1 · About you", value: "personal" },
    { label: `2 · ${STEP_TWO[evidence.value]}`, value: "school" },
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

const start = reactive({ intake: "", pathway: "", international: false });
watch(options, (o) => {
  if (o?.intakes.length && !start.intake) start.intake = o.intakes[0]!.name;
  if (o?.pathways.length && !start.pathway) start.pathway = o.pathways[0]!.name;
});
const pathwayGroups = computed(() =>
  (["Undergraduate", "Postgraduate"] as const)
    .map((level) => ({ level, pathways: (options.value?.pathways ?? []).filter((p) => p.level === level) }))
    .filter((g) => g.pathways.length),
);
const RESIDENCY = [
  { label: "Yes", value: false },
  { label: "No, I am international", value: true },
];

async function startApplication() {
  await save({ intake: start.intake, pathway: start.pathway, international: start.international }, "Application started");
}

// --- the forms, copied from the application so edits can be saved or dropped ---------------------------

/** how they are applying (step 1, above the particulars) */
const personal = reactive({ pathway: "", international: false });
/** the particulars (modules/apply/ApplicantDetails.vue) */
const details = ref<DetailsForm>(emptyDetails("Namibian"));
/** choosing a route at another level drops the programmes already chosen: said before saving */
const levelChange = computed(() => {
  const next = pathwayByName.value.get(personal.pathway);
  return Boolean(app.value?.choices.length && next && pathway.value && next.level !== pathway.value.level);
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
const prior = ref<PriorQualification[]>([]);
const employment = ref<Employment[]>([]);
const referees = ref<Referee[]>([]);
const previousNumber = ref("");
const choices = ref<(string | null)[]>([null, null, null]);

function resetForms() {
  const a = app.value;
  if (!a) return;
  details.value = detailsFrom(a.personal, "Namibian");
  Object.assign(personal, { pathway: a.pathway ?? "", international: a.international });
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
  prior.value = a.prior_qualifications.map((r) => ({ ...r }));
  employment.value = a.employment.map((r) => ({ ...r }));
  referees.value = a.referees.map((r) => ({ ...r }));
  previousNumber.value = a.previous_student_number ?? "";
  const max = options.value?.max_choices ?? 3;
  choices.value = Array.from({ length: max }, (_, i) => a.choices[i]?.offering ?? null);
}

async function savePersonal() {
  const ok = await save({
    pathway: personal.pathway || undefined,
    international: personal.international,
    personal: detailsToApi(details.value),
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

/** step 2: whatever this pathway is judged on */
async function saveBackground() {
  const changes: DraftChanges = {};
  if (usesSchool.value) {
    changes.school = school.notListed
      ? { school_name: school.typedName.trim(), town: school.typedTown.trim() }
      : school.selected
        ? { name: school.selected.name }
        : null;
    if (usesResults.value) {
      changes.exam_number = school.examNumber.trim() || null;
      changes.exam_year = school.examYear;
      changes.results = results.value.filter((r) => r.subject && r.level && r.grade);
    }
  }
  if (evidence.value !== "School results") {
    changes.prior_qualifications = prior.value;
    changes.employment = employment.value;
    changes.referees = referees.value;
    changes.previous_student_number = previousNumber.value.trim() || null;
  } else if ((pathway.value?.referees_required ?? 0) > 0) {
    changes.referees = referees.value;
  }
  const ok = await save(changes);
  if (ok) step.value = "choices";
}

// choices
const offeringOptions = computed(() =>
  (options.value?.offerings ?? [])
    .filter((o) => o.level === (pathway.value?.level ?? "Undergraduate"))
    .map((o) => ({
    value: o.name,
    label: `${o.program}, ${o.campus.replace(" Campus", "")}, ${o.mode_of_study}`,
  })),
);
const offeringByName = computed(() => new Map((options.value?.offerings ?? []).map((o) => [o.name, o])));
function requirementText(name: string | null) {
  const o = name ? offeringByName.value.get(name) : undefined;
  if (!o) return "";
  if (o.level === "Postgraduate") {
    return [
      o.min_prior_nqf ? `a qualification at NQF level ${o.min_prior_nqf} or higher` : "",
      o.min_prior_average ? `an average of at least ${o.min_prior_average}%` : "",
    ]
      .filter(Boolean)
      .join(", with ");
  }
  const parts = [o.min_points ? `at least ${o.min_points} points` : ""].concat(
    o.subject_requirements.map((r) => `${r.subject} at least ${r.grade} (${r.level})`),
  );
  return parts.filter(Boolean).join("; ");
}
/** published entry requirements are for school leavers and postgraduates; other routes are decided by a person */
const showsEntry = computed(() => ["School results", "Studies elsewhere", "Prior qualification"].includes(evidence.value));
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
/** after a decision the offer comes first; the application itself is a click away (open while a document needs replacing) */
const detailsOpen = ref(false);
const showDetails = computed(
  () => detailsOpen.value || !app.value?.offer || app.value.documents.some((d) => d.status === "Rejected"),
);
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
        <fieldset class="pathways">
          <legend>How are you applying?</legend>
          <template v-for="group in pathwayGroups" :key="group.level">
            <p class="group">{{ group.level }}</p>
            <label v-for="p in group.pathways" :key="p.name" class="pathway" :class="{ chosen: start.pathway === p.name }">
              <input v-model="start.pathway" type="radio" name="pathway" :value="p.name" />
              <span>
                <strong>{{ p.name }}<span v-if="p.min_age" class="sub"> · aged {{ p.min_age }} or older</span></strong>
                <!-- only the chosen route says more: the list stays short -->
                <small v-if="p.description && start.pathway === p.name" class="sub">{{ p.description }}</small>
              </span>
            </label>
          </template>
        </fieldset>
        <div class="field">
          <label>Are you a citizen or permanent resident of {{ options.home_country }}?</label>
          <SelectButton v-model="start.international" :options="RESIDENCY" option-label="label" option-value="value" :allow-empty="false" aria-label="Residency" />
        </div>
        <Button label="Start application" :loading="saving" :disabled="!start.intake || !start.pathway" @click="startApplication" />
      </template>
      <Message v-else severity="info" :closable="false">Applications are closed at the moment.</Message>
    </article>

    <!-- the application -->
    <template v-else>
      <PageHeader title="Your application" :subtitle="`${app.intake} · ${app.name}`" class="app-header">
        <template #actions><StatusTag kind="application" :value="app.status" /></template>
      </PageHeader>

      <!-- submitted: read only -->
      <template v-if="!app.editable">
        <OfferPanel v-if="app.offer" :application="app" class="offer-card" @changed="(updated) => (app = updated)" />
        <Button
          v-if="!showDetails"
          label="View application details"
          text
          size="small"
          @click="detailsOpen = true"
        />
        <article v-if="showDetails" class="card">
          <p v-if="app.status === 'Applied' && app.submitted_on">Submitted on {{ formatDate(app.submitted_on) }}. The Admissions Office is reviewing your application; the outcome will be shown here.</p>
          <Message v-if="app.decision_reason" severity="error" :closable="false">{{ app.decision_reason }}</Message>
          <h2>Your choices</h2>
          <ol class="choice-list">
            <li v-for="c in app.choices" :key="c.offering">{{ c.program }}, {{ c.campus }}</li>
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
        <article v-if="app.fee.amount && (showDetails || app.fee.status === 'Unpaid')" class="card fee-card">
          <FeePanel :fee="app.fee" />
        </article>
      </template>

      <!-- draft: the steps -->
      <div v-else class="layout">
        <aside class="checklist card">
          <h2>Outstanding</h2>
          <p v-if="!app.missing.length" class="ready">✓ Complete and ready to submit</p>
          <ul v-else>
            <li v-for="gap in app.missing" :key="gap">{{ gap }}</li>
          </ul>
          <p class="points">Entry pathway: <strong>{{ app.pathway }}</strong><template v-if="app.international"> · international</template></p>
          <p v-if="app.fee.amount" class="points">
            Application fee: <strong>{{ app.fee.status }}</strong>
          </p>
          <p v-if="app.points !== null && usesResults" class="points">
            Admission points: <strong>{{ app.points }}</strong>
            <span class="sub"> (best {{ options?.best_subjects }} subjects)</span>
          </p>
        </aside>

        <div ref="stepTop" class="main">
          <SelectButton v-model="step" :options="steps" option-label="label" option-value="value" :allow-empty="false" aria-label="Steps" class="steps" />

          <!-- 1 about you -->
          <article v-if="step === 'personal'" class="card form">
            <div class="grid">
              <div class="field">
                <label id="pathway-label" for="pathway">Entry pathway</label>
                <Select v-model="personal.pathway" input-id="pathway" aria-labelledby="pathway-label" :options="options?.pathways ?? []" option-label="name" option-value="name" fluid />
                <small class="sub">{{ pathwayByName.get(personal.pathway)?.description }}</small>
              </div>
              <div class="field">
                <label>Citizen or permanent resident of {{ options?.home_country }}?</label>
                <SelectButton v-model="personal.international" :options="RESIDENCY" option-label="label" option-value="value" :allow-empty="false" aria-label="Residency" />
              </div>
            </div>
            <ApplicantDetails v-model="details" :international="personal.international" :dial-codes="options?.dial_codes ?? []" :home-country="options?.home_country ?? 'Namibia'">
              <template #email>
                <EcField label="Email" for="email" hint="Your sign-in; it becomes your student login">
                  <InputText id="email" :model-value="app?.personal.student_email_id ?? ''" type="email" fluid readonly />
                </EcField>
              </template>
            </ApplicantDetails>
            <Message v-if="levelChange" severity="warn" :closable="false">
              {{ personal.pathway }} is for {{ pathwayByName.get(personal.pathway)?.level.toLowerCase() }} programmes: saving removes the
              programmes you chose.
            </Message>
            <div class="step-nav"><Button label="Save and continue" :loading="saving" @click="savePersonal" /></div>
          </article>

          <!-- 2 school and results -->
          <article v-else-if="step === 'school'" class="card form">
            <div v-if="usesSchool" class="field">
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
            <template v-if="usesResults">
              <div class="grid">
                <div class="field"><label for="exam-no">Examination number</label><InputText id="exam-no" v-model="school.examNumber" fluid /></div>
                <div class="field">
                  <label for="exam-year">Year of your latest results</label>
                  <InputText id="exam-year" :model-value="school.examYear ? String(school.examYear) : ''" inputmode="numeric" fluid @update:model-value="(v) => (school.examYear = v ? Number(v) : null)" />
                </div>
              </div>
              <h2>Results</h2>
              <p class="sub">Every subject on your latest NSSC statement. Your admission points are the best {{ options?.best_subjects }} subjects.</p>
              <div v-for="(result, index) in results" :key="index" class="result">
                <Select v-model="result.subject" :options="options?.subjects ?? []" placeholder="Subject" filter :aria-label="`Subject ${index + 1}`" class="subject" />
                <Select v-model="result.level" :options="levels" :aria-label="`Level ${index + 1}`" @change="result.grade = ''" />
                <Select v-model="result.grade" :options="gradesFor(result.level)" placeholder="Grade" :aria-label="`Grade ${index + 1}`" />
                <span class="sub pts">{{ result.points != null ? `${result.points} pts` : "" }}</span>
                <Button text severity="secondary" :aria-label="`Remove result ${index + 1}`" label="✕" @click="results.splice(index, 1)" />
              </div>
              <Button label="Add a subject" text @click="addResult" />
            </template>
            <Message v-else-if="usesSchool" severity="info" :closable="false">The admissions office assesses foreign school qualifications: upload them with your documents.</Message>
            <StudiesAndWork
              v-if="evidence !== 'School results' || (pathway?.referees_required ?? 0) > 0"
              v-model:prior="prior"
              v-model:employment="employment"
              v-model:referees="referees"
              v-model:previous-number="previousNumber"
              :evidence="evidence"
              :referees-required="pathway?.referees_required ?? 0"
              :home-country="options?.home_country ?? ''"
              :countries="options?.countries ?? []"
              :work-years="app.work_years"
              :dial-codes="options?.dial_codes ?? []"
            />
            <div class="step-nav">
              <Button label="Back" severity="secondary" text @click="go(-1)" />
              <Button label="Save and continue" :loading="saving" @click="saveBackground" />
            </div>
          </article>

          <!-- 3 programmes -->
          <article v-else-if="step === 'choices'" class="card form">
            <p class="sub">Up to {{ options?.max_choices }} programmes, in order of preference. Your first choice is considered first.</p>
            <div v-for="(_, index) in choices" :key="index" class="field choice">
              <label :id="`choice-label-${index}`" :for="`choice-${index}`">Choice {{ index + 1 }}</label>
              <Select
                v-model="choices[index]"
                :input-id="`choice-${index}`"
                :aria-labelledby="`choice-label-${index}`"
                :options="offeringOptions"
                option-label="label"
                option-value="value"
                :placeholder="index === 0 ? 'Choose a programme' : 'Optional'"
                show-clear
                filter
                fluid
              />
              <small v-if="choices[index] && showsEntry" class="sub">Entry: {{ requirementText(choices[index]) }}</small>
              <div v-if="eligibilityFor(choices[index])" class="eligibility">
                <Tag :severity="eligibilitySeverity(eligibilityFor(choices[index])?.eligibility)" :value="eligibilityLabel(eligibilityFor(choices[index])?.eligibility)" />
                <span class="sub">{{ eligibilityFor(choices[index])?.eligibility_note }}</span>
              </div>
            </div>
            <p class="sub">Eligibility is a first check on what you entered; the admissions office decides.</p>
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
                <Tag :value="doc.required ? 'Required' : 'If applicable'" :severity="doc.required ? 'warn' : 'secondary'" />
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
              <li>{{ app.pathway }}<template v-if="app.international"> · international applicant</template></li>
              <li v-if="app.school && usesSchool">{{ app.school.school_name }}<template v-if="app.points !== null && usesResults"> · {{ app.points }} points</template></li>
              <li v-for="q in app.prior_qualifications" :key="q.qualification + q.institution">{{ q.qualification }}, {{ q.institution }}<template v-if="q.year_completed"> ({{ q.year_completed }})</template></li>
              <li v-if="app.employment.length">{{ app.employment.length }} {{ app.employment.length === 1 ? "job" : "jobs" }}<template v-if="app.work_years"> · {{ app.work_years }} years of work</template></li>
              <li v-if="app.referees.length">Referees: {{ app.referees.map((r) => r.full_name).join(", ") }}</li>
              <li v-for="c in app.choices" :key="c.offering">Choice {{ c.rank }}: {{ c.program }}, {{ c.campus }}</li>
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


.start {
  max-width: 36rem;
  display: grid;
  gap: 1rem;
}

.pathways {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  border: 0;
}

.pathways legend {
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
}

.group {
  margin: 0.5rem 0 0;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: #6b7280;
}

.pathway {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
  padding: 0.55rem 0.8rem;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
}

.pathway > span {
  display: grid;
  gap: 0.15rem;
}

.pathway input {
  margin-top: 0.2rem;
  accent-color: var(--color-brand-navy);
}

.pathway.chosen {
  border-color: var(--color-brand-navy);
  background: #f8fafc;
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

.offer-card {
  margin-bottom: 1rem;
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
