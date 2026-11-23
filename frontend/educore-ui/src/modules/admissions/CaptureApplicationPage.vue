<script setup lang="ts">
import AutoComplete from "primevue/autocomplete";
import Checkbox from "primevue/checkbox";
import DatePicker from "primevue/datepicker";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, reactive, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { formatMoney, toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import ApplicantDetails from "@/modules/apply/ApplicantDetails.vue";
import StudiesAndWork from "@/modules/apply/StudiesAndWork.vue";
import { type DetailsForm, detailsToApi, emptyDetails } from "@/modules/apply/details";
import {
  type ApplyOptions,
  type Employment,
  LEVELS,
  type Level,
  type PriorQualification,
  type Referee,
  type Result,
  type School,
  findSchools,
  getOptions,
} from "@/modules/apply/api";
import { type CaptureIntake, captureApplication, getCaptureOptions } from "./api";

/**
 * A hard-copy application received at a campus, typed in by an admissions officer: the same details an online
 * applicant gives, on one page, then submitted. The email on the form becomes the student's login when they
 * register. Another officer decides on it (the workflow keeps the person who captured it from approving it).
 */
const router = useRouter();
const toast = useToast();
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const options = ref<ApplyOptions | null>(null);
const intakes = ref<CaptureIntake[]>([]);
const paperFees = ref({ local: 0, international: 0 });
const loadError = ref("");
onMounted(async () => {
  try {
    const [o, c] = await Promise.all([getOptions(), getCaptureOptions()]);
    options.value = o;
    intakes.value = c.intakes;
    paperFees.value = c.fees;
    form.intake = c.intakes[0]?.name ?? "";
    form.pathway = o.pathways[0]?.name ?? "";
    details.value.nationality = o.home_country === "Namibia" ? "Namibian" : "";
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  }
});

const form = reactive({
  intake: "",
  pathway: "",
  receivedOn: new Date() as Date | null,
  international: false,
  email: "",
  receipt: "",
});
const fee = computed(() => (form.international ? paperFees.value.international : paperFees.value.local));
/** the applicant's particulars (modules/apply/ApplicantDetails.vue) */
const details = ref<DetailsForm>(emptyDetails());

const pathway = computed(() => options.value?.pathways.find((p) => p.name === form.pathway));
const evidence = computed(() => pathway.value?.evidence ?? "School results");
const usesSchool = computed(() => ["School results", "Studies elsewhere"].includes(evidence.value));
const usesResults = computed(() => usesSchool.value && !form.international);

// --- programmes -------------------------------------------------------------------------------------------
const choices = ref<string[]>([""]);
const offeringOptions = computed(() =>
  (options.value?.offerings ?? [])
    .filter((o) => o.level === (pathway.value?.level ?? "Undergraduate"))
    .map((o) => ({ value: o.name, label: `${o.program} · ${o.campus.replace(" Campus", "")} · ${o.mode_of_study}` })),
);
// a change of level drops choices that no longer apply
watch(offeringOptions, (list) => {
  const allowed = new Set(list.map((o) => o.value));
  choices.value = choices.value.map((c) => (allowed.has(c) ? c : ""));
});

// --- school and results -----------------------------------------------------------------------------------
const school = reactive({ selected: null as School | null, notListed: false, typedName: "", typedTown: "", examNumber: "", examYear: null as number | null });
const schoolSuggestions = ref<School[]>([]);
async function searchSchools(event: { query: string }) {
  schoolSuggestions.value = await findSchools(event.query).catch(() => []);
}
const schoolLabel = (s: School) => `${s.school_name}${s.town ? `, ${s.town}` : ""}`;
const results = ref<Result[]>([{ subject: "", level: "NSSCO", grade: "" }]);
const gradesFor = (level: Level) => options.value?.grades[level] ?? [];
const levels = computed(() => LEVELS.filter((l) => gradesFor(l).length));

// --- studies, work, referees ------------------------------------------------------------------------------
const prior = ref<PriorQualification[]>([]);
const employment = ref<Employment[]>([]);
const referees = ref<Referee[]>([]);
const previousNumber = ref("");

// --- saving -----------------------------------------------------------------------------------------------
const saving = ref(false);
const error = ref("");
const missing = computed(() =>
  [
    !form.intake && "Intake",
    !details.value.first_name.trim() && "First name",
    !details.value.last_name.trim() && "Surname",
    !details.value.date_of_birth && "Date of birth",
    !EMAIL.test(form.email.trim()) && "Email",
    !choices.value.some(Boolean) && "A programme",
  ].filter(Boolean) as string[],
);

async function save() {
  if (missing.value.length) return;
  saving.value = true;
  error.value = "";
  try {
    const result = await captureApplication({
      intake: form.intake,
      pathway: form.pathway,
      received_on: form.receivedOn ? toIsoDate(form.receivedOn) : undefined,
      receipt_number: form.receipt.trim() || undefined,
      international: form.international,
      email: form.email.trim(),
      personal: detailsToApi(details.value),
      choices: choices.value.filter(Boolean),
      ...(usesSchool.value
        ? {
            school: school.notListed
              ? { school_name: school.typedName.trim(), town: school.typedTown.trim() }
              : school.selected
                ? { name: school.selected.name }
                : null,
          }
        : {}),
      ...(usesResults.value
        ? {
            exam_number: school.examNumber.trim() || null,
            exam_year: school.examYear,
            results: results.value.filter((r) => r.subject && r.grade),
          }
        : {}),
      prior_qualifications: prior.value,
      employment: employment.value,
      referees: referees.value,
      previous_student_number: previousNumber.value.trim() || null,
    });
    toast.add({ severity: "success", summary: "Application captured", detail: result.name, life: 4000 });
    await router.replace({ name: "application-record", params: { name: result.name } });
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <RecordPage
    :back="{ to: { name: 'admissions' }, label: 'Admissions' }"
    title="New paper application"
    subtitle="A hard-copy form received at a campus"
    :error="loadError"
    :loading="!options"
    :outstanding="missing.map((m) => `${m} to fill in`)"
  >
    <template #actions>
      <EcButton label="Cancel" variant="ghost" @click="router.back()" />
      <EcButton label="Capture application" variant="primary" :loading="saving" :disabled="Boolean(missing.length)" :title="missing.length ? `Still needed: ${missing.join(', ')}` : undefined" @click="save" />
    </template>

    <template v-if="options">
      <EcPanel title="Application">
        <div class="form">
          <EcField label="Intake" for="intake">
            <Select v-model="form.intake" input-id="intake" :options="intakes" option-label="title" option-value="name" fluid />
          </EcField>
          <EcField label="Entry pathway" for="pathway">
            <Select v-model="form.pathway" input-id="pathway" :options="options.pathways" option-label="name" option-value="name" fluid />
          </EcField>
          <EcField label="Received on" for="received">
            <DatePicker v-model="form.receivedOn" input-id="received" date-format="dd-mm-yy" show-icon fluid :max-date="new Date()" />
          </EcField>
          <div class="check">
            <Checkbox v-model="form.international" input-id="international" binary />
            <label for="international">International applicant</label>
          </div>
          <EcField :label="`Application fee ${formatMoney(fee)}`" for="receipt" hint="The cashier's receipt number, once paid">
            <InputText id="receipt" v-model="form.receipt" placeholder="Receipt number" fluid />
          </EcField>
        </div>
      </EcPanel>

      <EcPanel title="Applicant">
        <ApplicantDetails v-model="details" staff :international="form.international" :dial-codes="options.dial_codes" :home-country="options.home_country">
          <template #email>
            <EcField
              label="Email"
              for="email"
              hint="Becomes the student's login on registration"
              :error="form.email && !EMAIL.test(form.email.trim()) ? 'Not a valid email address' : undefined"
            >
              <InputText id="email" v-model="form.email" type="email" autocomplete="off" fluid :invalid="Boolean(form.email) && !EMAIL.test(form.email.trim())" />
            </EcField>
          </template>
        </ApplicantDetails>
      </EcPanel>

      <EcPanel title="Programme choices" :note="`Up to ${options.max_choices}, in order of preference`">
        <div class="choices">
          <EcField v-for="(_, i) in choices" :key="i" :label="`Choice ${i + 1}`" :for="`choice-${i}`">
            <Select v-model="choices[i]" :input-id="`choice-${i}`" :options="offeringOptions" option-label="label" option-value="value" filter show-clear fluid placeholder="Programme, campus and mode" />
          </EcField>
        </div>
        <EcButton v-if="choices.length < options.max_choices" label="Add a choice" size="sm" variant="ghost" @click="choices.push('')" />
      </EcPanel>

      <EcPanel v-if="usesSchool" :title="usesResults ? 'School and results' : 'School'">
        <div class="stack">
          <EcField label="Secondary school" for="school">
            <AutoComplete
              v-if="!school.notListed"
              v-model="school.selected"
              input-id="school"
              :suggestions="schoolSuggestions"
              :option-label="schoolLabel"
              placeholder="Two letters of the school or town"
              fluid
              @complete="searchSchools"
            />
          </EcField>
          <div class="check">
            <Checkbox v-model="school.notListed" input-id="not-listed" binary />
            <label for="not-listed">The school is not in the list</label>
          </div>
          <div v-if="school.notListed" class="form">
            <EcField label="School name" for="typed-school"><InputText id="typed-school" v-model="school.typedName" fluid /></EcField>
            <EcField label="Town" for="typed-town"><InputText id="typed-town" v-model="school.typedTown" fluid /></EcField>
          </div>
          <template v-if="usesResults">
            <div class="form">
              <EcField label="Examination number" for="exam-no"><InputText id="exam-no" v-model="school.examNumber" fluid /></EcField>
              <EcField label="Year of the results" for="exam-year">
                <InputText id="exam-year" :model-value="school.examYear ? String(school.examYear) : ''" inputmode="numeric" fluid @update:model-value="(v) => (school.examYear = v ? Number(v) : null)" />
              </EcField>
            </div>
            <table class="ec-table results">
              <thead>
                <tr><th>Subject</th><th>Level</th><th>Grade</th><th aria-hidden="true"></th></tr>
              </thead>
              <tbody>
                <tr v-for="(r, i) in results" :key="i">
                  <td><Select v-model="r.subject" :options="options.subjects" placeholder="Subject" filter fluid :aria-label="`Subject ${i + 1}`" /></td>
                  <td><Select v-model="r.level" :options="levels" fluid :aria-label="`Level ${i + 1}`" @change="r.grade = ''" /></td>
                  <td><Select v-model="r.grade" :options="gradesFor(r.level)" placeholder="Grade" fluid :aria-label="`Grade ${i + 1}`" /></td>
                  <td class="num"><EcButton label="Remove" size="sm" variant="quiet-danger" :aria-label="`Remove result ${i + 1}`" @click="results.splice(i, 1)" /></td>
                </tr>
              </tbody>
            </table>
            <div><EcButton label="Add a subject" size="sm" variant="ghost" @click="results.push({ subject: '', level: 'NSSCO', grade: '' })" /></div>
          </template>
        </div>
      </EcPanel>

      <EcPanel v-if="evidence !== 'School results' || (pathway?.referees_required ?? 0) > 0" title="Studies, work and referees">
        <StudiesAndWork
          v-model:prior="prior"
          v-model:employment="employment"
          v-model:referees="referees"
          v-model:previous-number="previousNumber"
          :evidence="evidence"
          :referees-required="pathway?.referees_required ?? 0"
          :home-country="options.home_country"
          :countries="options.countries"
          :work-years="null"
          :dial-codes="options.dial_codes"
        />
      </EcPanel>

      <Message v-if="error" severity="error" :closable="false" role="alert">{{ error }}</Message>
    </template>

  </RecordPage>
</template>

<style scoped>
.form {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 14rem), 1fr));
  gap: 0.9rem 1rem;
  align-items: start;
}

.choices,
.stack {
  display: grid;
  gap: 0.9rem;
}

.choices {
  margin-bottom: 0.5rem;
}

.check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  align-self: end;
  padding-bottom: 0.6rem;
}

.results td {
  padding-left: 0.25rem;
  padding-right: 0.25rem;
}
</style>
