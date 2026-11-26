<script setup lang="ts">
import { Search, Trash2 } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { ASSESSMENT_KINDS, type Assessment, type Sheet, caFrom, mySheet, saveGradebook } from "./api";

/**
 * The module's gradebook: the lecturer's own assessments (two tests and two assignments, quizzes, a project: each
 * marked out of what they choose, with its share of the CA) and each student's scores; the CA is worked out as they
 * type and goes to the Marks tab. Locked once the marks are submitted.
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

const editable = computed(() => sheet.value?.status === "Draft");
const assessments = computed(() => sheet.value?.assessments ?? []);
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

async function save() {
  saving.value = true;
  try {
    take(await saveGradebook(props.group, assessments.value, scores.value));
    toast.add({ severity: "success", summary: "Scores saved", life: 2000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}

// --- the assessments ---
const planning = ref<Assessment[] | null>(null);
function openPlan() {
  planning.value = assessments.value.length
    ? assessments.value.map((a) => ({ ...a }))
    : [
        { title: "Test 1", kind: "Test", out_of: 50, weight: 25 },
        { title: "Test 2", kind: "Test", out_of: 50, weight: 25 },
        { title: "Assignment 1", kind: "Assignment", out_of: 100, weight: 25 },
        { title: "Assignment 2", kind: "Assignment", out_of: 100, weight: 25 },
      ];
}
const planTotal = computed(() => Math.round((planning.value ?? []).reduce((sum, a) => sum + (a.weight || 0), 0) * 100) / 100);
const planReady = computed(() => (planning.value ?? []).every((a) => a.title.trim() && a.out_of > 0 && a.weight > 0) && (planning.value?.length === 0 || planTotal.value === 100));
function addAssessment() {
  const n = (planning.value?.length ?? 0) + 1;
  planning.value!.push({ title: `Quiz ${n}`, kind: "Quiz", out_of: 20, weight: Math.max(0, 100 - planTotal.value) });
}
async function keepPlan() {
  saving.value = true;
  try {
    take(await saveGradebook(props.group, planning.value!, scores.value));
    planning.value = null;
    toast.add({ severity: "success", summary: "Assessments saved", life: 2000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
  <section v-else-if="sheet" class="ec-card tab">
    <div class="bar">
      <StatusTag kind="marks" :value="sheet.status" />
      <span class="ec-muted small">{{ assessments.length ? `CA: ${plan}` : "No assessments yet: set them up, or type the CA on the Marks tab" }}</span>
      <span class="spacer" />
      <EcButton v-if="editable" :label="assessments.length ? 'Change assessments' : 'Set up assessments'" size="sm" :variant="assessments.length ? 'ghost' : 'primary'" @click="openPlan" />
    </div>

    <template v-if="assessments.length">
      <div class="bar">
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name or student number" aria-label="Search students" fluid size="small" />
        </IconField>
        <EcSegmented v-model="filter" :options="filters" label="Show" />
        <span class="spacer" />
        <EcButton v-if="editable" label="Save scores" size="sm" variant="primary" :loading="saving" :disabled="!changed" @click="save" />
      </div>
      <div class="scroll">
        <table class="ec-table sticky book">
          <thead>
            <tr>
              <th class="who-col">Student</th>
              <th v-for="a in assessments" :key="a.assessment_key" class="num score-col">
                {{ a.title }}
                <span class="head-sub">/{{ a.out_of }} · {{ a.weight }}%</span>
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
                  v-if="editable"
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

  <EcModal :open="planning !== null" title="The module's assessments" description="What makes up the CA: each assessment's mark out of, and its share of the CA" size="lg" @update:open="(v: boolean) => !v && (planning = null)">
    <table v-if="planning" class="plan">
      <thead>
        <tr><th>Assessment</th><th>Kind</th><th class="num">Out of</th><th class="num">Share of CA</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="(a, i) in planning" :key="i">
          <td><InputText v-model="a.title" size="small" :aria-label="`Assessment ${i + 1}`" fluid /></td>
          <td><Select v-model="a.kind" :options="[...ASSESSMENT_KINDS]" size="small" :aria-label="`Kind ${i + 1}`" fluid /></td>
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
    <p class="ec-muted small">Removing an assessment removes its scores. Scores already entered stay with the assessments kept.</p>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="planning = null" />
      <EcButton label="Save assessments" variant="primary" :loading="saving" :disabled="!planReady" @click="keepPlan" />
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
