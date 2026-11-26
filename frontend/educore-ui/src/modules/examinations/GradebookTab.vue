<script setup lang="ts">
import { ExternalLink, Search, Trash2 } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Assessment, type MoodleActivity, type Sheet, caFrom, moodleActivities, moodleScores, mySheet, proposePlan, saveGradebook } from "./api";

/**
 * The module's gradebook: the lecturer's assessments (of the faculty's assessment types, each marked out of what they
 * choose, with its share of the CA) and each student's scores; the CA is worked out as they type and goes to the
 * Marks tab. The plan goes to the Head of Department for approval; scores are entered once it is approved. An online
 * assessment is linked to its Moodle activity and its grades brought in to check and save. Locked once the marks
 * are submitted.
 */
const props = defineProps<{ group: string }>();
const toast = useToast();
const sheet = ref<Sheet | null>(null);
const error = ref("");
const saving = ref(false);
const scores = ref<Record<string, Record<string, number | null>>>({});
const search = ref("");
type Filter = "all" | "missing";
const filter = ref<Filter>("all");

function take(s: Sheet) {
  sheet.value = s;
  scores.value = Object.fromEntries(s.entries.map((e) => [e.student, { ...(s.scores[e.student] ?? {}) }]));
}
watch(
  () => props.group,
  async () => {
    error.value = "";
    try {
      take(await mySheet(props.group));
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

const fail = (e: unknown) => toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
const editable = computed(() => sheet.value?.status === "Draft");
const planStatus = computed(() => sheet.value?.plan?.status ?? null);
/** the plan is the lecturer's to change: not with the department, not approved */
const planOpen = computed(() => editable.value && !planStatus.value);
/** scores go in once the plan is approved */
const scoring = computed(() => editable.value && planStatus.value === "Approved");
const assessments = computed(() => sheet.value?.assessments ?? []);
const types = computed(() => sheet.value?.assessment_types ?? []);
const isOnline = (a: Assessment) => Boolean(types.value.find((t) => t.type_name === a.kind)?.online);
const missingOf = (student: string) => assessments.value.filter((a) => scores.value[student]?.[a.assessment_key!] == null).length;
const missing = computed(() => (sheet.value?.entries ?? []).filter((e) => missingOf(e.student) > 0).length);
const changed = computed(() =>
  (sheet.value?.entries ?? []).some((e) => assessments.value.some((a) => (scores.value[e.student]?.[a.assessment_key!] ?? null) !== (sheet.value!.scores[e.student]?.[a.assessment_key!] ?? null))),
);
const filters = computed(() => [
  { value: "all" as Filter, label: `All ${sheet.value?.entries.length ?? 0}` },
  { value: "missing" as Filter, label: `Scores missing ${missing.value}` },
]);
const shown = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (sheet.value?.entries ?? []).filter((e) => (!q || `${e.student_name} ${e.student}`.toLowerCase().includes(q)) && (filter.value === "all" || missingOf(e.student) > 0));
});
const plan = computed(() => assessments.value.map((a) => `${a.title} ${a.weight}%`).join(" · "));
const planLine = computed(() => {
  if (!assessments.value.length) return "No assessments yet: set them up, or type the CA on the Marks tab";
  if (planStatus.value === "Proposed") return `With the Head of Department for approval · ${plan.value}`;
  if (planStatus.value === "Approved") return `CA: ${plan.value}`;
  return `Not yet submitted for approval · ${plan.value}`;
});

async function save() {
  saving.value = true;
  try {
    take(await saveGradebook(props.group, assessments.value, scores.value));
    toast.add({ severity: "success", summary: "Scores saved", life: 2000 });
  } catch (e) {
    fail(e);
  } finally {
    saving.value = false;
  }
}

// --- the plan ---
const planning = ref<Assessment[] | null>(null);
const typeOptions = computed(() =>
  types.value.map((t) => ({ value: t.type_name, label: [t.type_name, t.online ? "Moodle" : "", t.max_share ? `at most ${t.max_share}%` : ""].filter(Boolean).join(" · ") })),
);
const firstOf = (...names: string[]) => names.find((n) => types.value.some((t) => t.type_name === n)) ?? types.value[0]?.type_name ?? "";
function openPlan() {
  planning.value = assessments.value.length
    ? assessments.value.map((a) => ({ ...a }))
    : [
        { title: "Test 1", kind: firstOf("Test"), out_of: 50, weight: 25 },
        { title: "Test 2", kind: firstOf("Test"), out_of: 50, weight: 25 },
        { title: "Assignment 1", kind: firstOf("Assignment"), out_of: 100, weight: 25 },
        { title: "Assignment 2", kind: firstOf("Assignment"), out_of: 100, weight: 25 },
      ];
}
const planTotal = computed(() => Math.round((planning.value ?? []).reduce((sum, a) => sum + (a.weight || 0), 0) * 100) / 100);
const planReady = computed(() => (planning.value ?? []).every((a) => a.title.trim() && a.kind && a.out_of > 0 && a.weight > 0) && (planning.value?.length === 0 || planTotal.value === 100));
function addAssessment() {
  const n = (planning.value?.length ?? 0) + 1;
  planning.value!.push({ title: `Quiz ${n}`, kind: firstOf("Quiz", "Online quiz"), out_of: 20, weight: Math.max(0, 100 - planTotal.value) });
}
async function keepPlan() {
  saving.value = true;
  try {
    // an assessment no longer online keeps no Moodle link
    const rows = planning.value!.map((a) => (types.value.find((t) => t.type_name === a.kind)?.online ? a : { ...a, moodle_cmid: null, moodle_activity: null, moodle_url: null }));
    take(await saveGradebook(props.group, rows, scores.value));
    planning.value = null;
    toast.add({ severity: "success", summary: "Assessments saved", life: 2000 });
  } catch (e) {
    fail(e);
  } finally {
    saving.value = false;
  }
}
const proposing = ref(false);
async function propose() {
  proposing.value = true;
  try {
    take(await proposePlan(props.group));
    toast.add({ severity: "success", summary: "Submitted for approval", life: 2500 });
  } catch (e) {
    fail(e);
  } finally {
    proposing.value = false;
  }
}

// --- Moodle ---
const linking = ref<Assessment | null>(null);
const activities = ref<MoodleActivity[]>([]);
const chosen = ref<number | null>(null);
const loadingActivities = ref(false);
const moodleNote = computed(() => {
  const m = sheet.value?.moodle;
  if (!m?.connected) return "Moodle is not connected yet";
  if (!m.in_moodle) return "The class is not in Moodle yet";
  return "";
});
async function openLink(a: Assessment) {
  linking.value = a;
  chosen.value = a.moodle_cmid ?? null;
  activities.value = [];
  loadingActivities.value = true;
  try {
    activities.value = await moodleActivities(props.group);
  } catch (e) {
    fail(e);
    linking.value = null;
  } finally {
    loadingActivities.value = false;
  }
}
const activityOptions = computed(() => activities.value.map((a) => ({ value: a.cmid, label: [a.name, a.kind, a.section].filter(Boolean).join(" · ") })));
async function link() {
  const target = linking.value;
  if (!target || !chosen.value) return;
  saving.value = true;
  try {
    const rows = assessments.value.map((a) => (a.assessment_key === target.assessment_key ? { ...a, moodle_cmid: chosen.value } : a));
    take(await saveGradebook(props.group, rows, sheet.value!.scores));
    linking.value = null;
    toast.add({ severity: "success", summary: "Linked to Moodle", life: 2000 });
  } catch (e) {
    fail(e);
  } finally {
    saving.value = false;
  }
}
const fetching = ref<string | null>(null);
async function fromMoodle(a: Assessment) {
  fetching.value = a.assessment_key!;
  try {
    const got = await moodleScores(props.group, a.assessment_key!);
    for (const [student, score] of Object.entries(got.scores)) {
      if (scores.value[student]) scores.value[student][a.assessment_key!] = score;
    }
    const count = Object.keys(got.scores).length;
    toast.add({
      severity: "info",
      summary: `${count} ${count === 1 ? "score" : "scores"} from Moodle`,
      detail: [got.not_graded ? `${got.not_graded} not graded in Moodle yet` : "", "Check them, then save"].filter(Boolean).join(". "),
      life: 5000,
    });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not brought in", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    fetching.value = null;
  }
}
</script>

<template>
  <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
  <section v-else-if="sheet" class="ec-card tab">
    <div class="bar">
      <StatusTag v-if="assessments.length" kind="plan" :value="planStatus" />
      <StatusTag v-else kind="marks" :value="sheet.status" />
      <span class="ec-muted small">{{ planLine }}</span>
      <span class="spacer" />
      <template v-if="planOpen">
        <EcButton :label="assessments.length ? 'Change assessments' : 'Set up assessments'" size="sm" :variant="assessments.length ? 'ghost' : 'primary'" @click="openPlan" />
        <EcButton v-if="assessments.length" label="Submit for approval" size="sm" variant="primary" :loading="proposing" @click="propose" />
      </template>
    </div>
    <p v-if="planOpen && sheet.plan?.note" class="returned small"><strong>Returned by the department:</strong> {{ sheet.plan.note }}</p>

    <template v-if="assessments.length">
      <div class="bar">
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name or student number" aria-label="Search students" fluid size="small" />
        </IconField>
        <EcSegmented v-model="filter" :options="filters" label="Show" />
        <span class="spacer" />
        <EcButton v-if="scoring" label="Save scores" size="sm" variant="primary" :loading="saving" :disabled="!changed" @click="save" />
      </div>
      <div class="scroll">
        <table class="ec-table sticky book">
          <thead>
            <tr>
              <th class="who-col">Student</th>
              <th v-for="a in assessments" :key="a.assessment_key" class="num score-col">
                {{ a.title }}
                <span class="head-sub">/{{ a.out_of }} · {{ a.weight }}%</span>
                <span v-if="isOnline(a)" class="head-moodle">
                  <a v-if="a.moodle_url" :href="a.moodle_url" target="_blank" rel="noopener" class="moodle-link" :title="a.moodle_activity ?? ''">
                    Moodle <ExternalLink :size="11" />
                  </a>
                  <template v-if="editable">
                    <button v-if="scoring && a.moodle_cmid" type="button" class="head-action" :disabled="fetching !== null" @click="fromMoodle(a)">
                      {{ fetching === a.assessment_key ? "Bringing in" : "From Moodle" }}
                    </button>
                    <button v-else-if="!a.moodle_cmid" type="button" class="head-action" :disabled="Boolean(moodleNote)" :title="moodleNote" @click="openLink(a)">Link</button>
                  </template>
                </span>
              </th>
              <th class="num ca-col">CA</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="e in shown" :key="e.student">
              <td class="who-col">
                {{ e.student_name }}
                <div class="ec-muted">{{ e.student }}</div>
              </td>
              <td v-for="a in assessments" :key="a.assessment_key" class="num">
                <InputNumber
                  v-if="scoring"
                  v-model="scores[e.student][a.assessment_key!]"
                  :min="0"
                  :max="a.out_of"
                  :max-fraction-digits="1"
                  size="small"
                  :aria-label="`${a.title}, ${e.student_name}`"
                  fluid
                />
                <template v-else>{{ scores[e.student]?.[a.assessment_key!] ?? "" }}</template>
              </td>
              <td class="num ca">{{ caFrom(assessments, scores[e.student]) ?? "" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-if="!shown.length" class="none ec-muted">No student here</p>
      </div>
    </template>
  </section>

  <EcModal :open="planning !== null" title="The module's assessments" description="What makes up the CA: each assessment's type, mark out of, and share of the CA" size="lg" @update:open="(v: boolean) => !v && (planning = null)">
    <table v-if="planning" class="plan">
      <thead>
        <tr><th>Assessment</th><th>Type</th><th class="num">Out of</th><th class="num">Share of CA</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="(a, i) in planning" :key="i">
          <td><InputText v-model="a.title" size="small" :aria-label="`Assessment ${i + 1}`" fluid /></td>
          <td><Select v-model="a.kind" :options="typeOptions" option-label="label" option-value="value" size="small" :aria-label="`Type ${i + 1}`" fluid /></td>
          <td><InputNumber v-model="a.out_of" :min="1" size="small" :aria-label="`Out of ${i + 1}`" fluid /></td>
          <td><InputNumber v-model="a.weight" :min="0" :max="100" suffix="%" :max-fraction-digits="2" size="small" :aria-label="`Share ${i + 1}`" fluid /></td>
          <td><button type="button" class="remove" :aria-label="`Remove ${a.title}`" @click="planning.splice(i, 1)"><Trash2 :size="15" /></button></td>
        </tr>
      </tbody>
    </table>
    <div class="plan-foot">
      <EcButton label="Add an assessment" size="sm" variant="ghost" @click="addAssessment" />
      <span :class="['total', { off: planTotal !== 100 }]">Total {{ planTotal }}%{{ planTotal !== 100 ? " (must be 100%)" : "" }}</span>
    </div>
    <p class="ec-muted small">The types are the faculty's. Removing an assessment removes its scores. Once saved, submit the plan for the Head of Department's approval.</p>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="planning = null" />
      <EcButton label="Save assessments" variant="primary" :loading="saving" :disabled="!planReady" @click="keepPlan" />
    </template>
  </EcModal>

  <EcModal :open="linking !== null" title="Link to Moodle" :description="linking ? `${linking.title}: the activity in the class's Moodle course its scores come from` : ''" @update:open="(v: boolean) => !v && (linking = null)">
    <EcField label="Moodle activity" for="moodle-activity">
      <Select
        v-model="chosen"
        input-id="moodle-activity"
        :options="activityOptions"
        option-label="label"
        option-value="value"
        :loading="loadingActivities"
        :placeholder="loadingActivities ? 'Loading' : activities.length ? 'Choose' : 'No graded activity in the course yet'"
        fluid
      />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="linking = null" />
      <EcButton label="Link" variant="primary" :loading="saving" :disabled="!chosen" @click="link" />
    </template>
  </EcModal>
</template>

<style scoped>
.tab {
  overflow: hidden;
}

.bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--ec-border);
}

.small {
  font-size: 0.8125rem;
}

.spacer {
  flex: 1;
}

.search {
  flex: 1;
  max-width: 20rem;
}

.scroll {
  max-height: 70vh;
  overflow: auto;
}

.sticky thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--ec-surface, #fff);
}

.book .who-col {
  min-width: 13rem;
}

.score-col {
  min-width: 7.5rem;
}

.ca-col {
  min-width: 4.5rem;
}

.head-sub {
  display: block;
  color: var(--ec-muted);
  font-size: 0.7rem;
  font-weight: 400;
}

.head-moodle {
  display: flex;
  justify-content: flex-end;
  gap: 0.4rem;
  margin-top: 0.15rem;
  font-size: 0.7rem;
  font-weight: 500;
}

.moodle-link {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  color: var(--ec-accent);
  text-decoration: none;
}

.head-action {
  padding: 0;
  border: 0;
  background: none;
  color: var(--ec-accent);
  font: inherit;
  cursor: pointer;
}

.head-action:disabled {
  color: var(--ec-muted);
  cursor: default;
}

.returned {
  margin: 0;
  padding: 0.6rem 1rem;
  border-bottom: 1px solid var(--ec-border);
}

.ca {
  font-weight: 600;
}

.plan {
  width: 100%;
  border-collapse: collapse;
}

.plan th {
  padding: 0 0.4rem 0.4rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 600;
  text-align: left;
}

.plan th.num {
  text-align: right;
}

.plan td {
  padding: 0.25rem 0.4rem;
}

.plan td:nth-child(3),
.plan td:nth-child(4) {
  width: 8rem;
}

.remove {
  display: inline-flex;
  padding: 0.3rem;
  border: 0;
  background: none;
  color: var(--ec-muted);
  cursor: pointer;
}

.remove:hover {
  color: var(--ec-danger, #b42318);
}

.plan-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 0.5rem;
}

.total {
  font-size: 0.875rem;
  font-weight: 600;
}

.total.off {
  color: var(--ec-danger, #b42318);
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
}
</style>
