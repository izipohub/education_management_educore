<script setup lang="ts">
import { Search } from "@lucide/vue";
import Checkbox from "primevue/checkbox";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Entry, type Sheet, mySheet, saveMarks, saveSupplementary, submitMarks, submitSupplementary, workOut, workOutSitting } from "./api";

/**
 * A lecturer's marks for one class: continuous assessment and examination per student, the final mark, grade and
 * result worked out as they type (the university's rules). Saved as often as needed; submitted to the department
 * when complete, after which the department returns it if anything needs changing. A tab of the module's page:
 * for a class of any size, search and show only the students still without marks or not passing.
 */
const props = defineProps<{ group: string }>();
const toast = useToast();
const sheet = ref<Sheet | null>(null);
const rows = ref<Entry[]>([]);
const error = ref("");
const saving = ref(false);
const confirming = ref(false);

function take(s: Sheet) {
  sheet.value = s;
  rows.value = s.entries.map((e) => ({ ...e }));
}
watch(
  () => props.group,
  async () => {
    sheet.value = null;
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
const live = (e: Entry) => (sheet.value ? workOut(e, sheet.value.rules) : { final_mark: null, grade: null, result: null });
const input = (e: Entry) => ({ student: e.student, ca_mark: e.ca_mark, exam_mark: e.exam_mark, absent: e.absent });
const changed = computed(() => JSON.stringify(rows.value.map(input)) !== JSON.stringify((sheet.value?.entries ?? []).map(input)));
const missing = computed(() => rows.value.filter((e) => !live(e).result).length);
const search = ref("");
type Filter = "all" | "missing" | "failing";
const filter = ref<Filter>("all");
const failing = computed(() => rows.value.filter((e) => live(e).result && live(e).result !== "Pass").length);
const filters = computed(() => [
  { value: "all" as Filter, label: `All ${rows.value.length}` },
  { value: "missing" as Filter, label: `Without a result ${missing.value}` },
  { value: "failing" as Filter, label: `Not passing ${failing.value}` },
]);
const shown = computed(() => {
  const q = search.value.trim().toLowerCase();
  return rows.value.filter((e) => {
    if (q && !`${e.student_name} ${e.student}`.toLowerCase().includes(q)) return false;
    if (filter.value === "missing") return !live(e).result;
    if (filter.value === "failing") return Boolean(live(e).result) && live(e).result !== "Pass";
    return true;
  });
});
const summary = computed(() => {
  const counts: Record<string, number> = {};
  for (const e of rows.value) {
    const r = live(e).result;
    if (r) counts[r] = (counts[r] ?? 0) + 1;
  }
  return Object.entries(counts).map(([result, n]) => `${n} ${result.toLowerCase()}`).join(" · ");
});

async function save(quiet = false) {
  saving.value = true;
  try {
    take(await saveMarks(props.group, rows.value.map(input)));
    if (!quiet) toast.add({ severity: "success", summary: "Marks saved", life: 2000 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    saving.value = false;
  }
}
async function submit() {
  if (changed.value && !(await save(true))) return;
  saving.value = true;
  try {
    take(await submitMarks(props.group));
    confirming.value = false;
    toast.add({ severity: "success", summary: "Marks submitted to the department", life: 3000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not submitted", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}

// the supplementary sitting, once the results are published
const suppRows = computed(() => rows.value.filter((e) => e.writes_supplementary));
const suppOpen = computed(() => sheet.value?.status === "Published" && sheet.value.supp_status === "Open" && suppRows.value.length > 0);
const suppChanged = computed(
  () => JSON.stringify(suppRows.value.map((e) => e.supp_exam_mark)) !== JSON.stringify((sheet.value?.entries ?? []).filter((e) => e.writes_supplementary).map((e) => e.supp_exam_mark)),
);
const suppMissing = computed(() => suppRows.value.filter((e) => e.supp_exam_mark === null || e.supp_exam_mark === undefined).length);
const liveSupp = (e: Entry) => (sheet.value ? workOutSitting(e, sheet.value.rules) : { final_mark: null, grade: null, result: null });
async function saveSupp(quiet = false) {
  saving.value = true;
  try {
    take(await saveSupplementary(props.group, suppRows.value.map((e) => ({ student: e.student, supp_exam_mark: e.supp_exam_mark }))));
    if (!quiet) toast.add({ severity: "success", summary: "Supplementary marks saved", life: 2000 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    saving.value = false;
  }
}
async function submitSupp() {
  if (suppChanged.value && !(await saveSupp(true))) return;
  saving.value = true;
  try {
    take(await submitSupplementary(props.group));
    toast.add({ severity: "success", summary: "Supplementary marks submitted", life: 3000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not submitted", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}

const rulesNote = computed(() => {
  const r = sheet.value?.rules;
  return r ? `CA ${r.ca_weight}%, examination ${100 - r.ca_weight}% · pass ${r.pass_mark}` : "";
});
</script>

<template>
  <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
  <template v-else-if="sheet">
    <Message v-if="sheet.return_note && editable" severity="warn" :closable="false">Returned by the department: {{ sheet.return_note }}</Message>
    <section class="ec-card tab">
      <div class="bar">
        <StatusTag kind="marks" :value="sheet.status" />
        <span class="ec-muted small">{{ rulesNote }}<template v-if="sheet.ca_from_gradebook"> · CA from the gradebook</template><template v-if="summary"> · {{ summary }}</template></span>
        <span class="spacer" />
        <template v-if="editable">
          <EcButton label="Save" size="sm" :loading="saving" :disabled="!changed" @click="save()" />
          <EcButton label="Submit to the department" size="sm" variant="primary" :disabled="saving || missing > 0" :title="missing ? `${missing} students still without a result` : undefined" @click="confirming = true" />
        </template>
      </div>
      <div class="bar">
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Name or student number" aria-label="Search students" fluid size="small" />
        </IconField>
        <EcSegmented v-model="filter" :options="filters" label="Show" />
      </div>
      <div class="scroll">
      <table class="ec-table marks sticky">
        <colgroup>
          <col />
          <col class="c-mark" />
          <col class="c-mark" />
          <col class="c-absent" />
          <col class="c-final" />
          <col class="c-grade" />
          <col class="c-result" />
        </colgroup>
        <thead>
          <tr>
            <th>Student</th>
            <th class="num">CA</th>
            <th class="num">Examination</th>
            <th>Absent</th>
            <th class="num">Final</th>
            <th>Grade</th>
            <th>Result</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in shown" :key="e.student">
            <td>
              {{ e.student_name }}
              <div class="ec-muted">{{ e.student }}</div>
              <div v-if="e.moderation_note" class="ec-muted">Moderated: {{ e.moderation_note }}</div>
            </td>
            <td class="num">
              <InputNumber v-if="editable && !sheet.ca_from_gradebook" v-model="e.ca_mark" :min="0" :max="100" :max-fraction-digits="1" size="small" :aria-label="`CA, ${e.student_name}`" fluid />
              <template v-else>{{ e.ca_mark ?? "" }}</template>
            </td>
            <td class="num">
              <InputNumber v-if="editable" v-model="e.exam_mark" :min="0" :max="100" :max-fraction-digits="1" size="small" :disabled="Boolean(e.absent)" :aria-label="`Examination, ${e.student_name}`" fluid />
              <template v-else>{{ e.exam_mark ?? "" }}</template>
            </td>
            <td>
              <Checkbox v-if="editable" v-model="e.absent" :true-value="1" :false-value="0" binary :aria-label="`Absent, ${e.student_name}`" />
              <template v-else>{{ e.absent ? "Absent" : "" }}</template>
            </td>
            <td class="num final">{{ live(e).final_mark ?? "" }}</td>
            <td>{{ live(e).grade ?? "" }}</td>
            <td><StatusTag v-if="live(e).result" kind="result" :value="live(e).result" /></td>
          </tr>
        </tbody>
      </table>
      <p v-if="!shown.length" class="none ec-muted">No student here</p>
      </div>
    </section>

    <EcPanel v-if="suppRows.length && sheet.status === 'Published'" title="Supplementary and special examinations" :note="sheet.supp_status === 'Open' ? 'At the supplementary sitting' : sheet.supp_status === 'Submitted' ? 'Submitted to the examinations office' : 'Published'" flush>
      <table class="ec-table marks">
        <colgroup>
          <col />
          <col class="c-mark" />
          <col class="c-mark" />
          <col class="c-final" />
          <col class="c-grade" />
          <col class="c-result" />
        </colgroup>
        <thead>
          <tr><th>Student</th><th class="num">First attempt</th><th class="num">Examination</th><th class="num">Final</th><th>Grade</th><th>Result</th></tr>
        </thead>
        <tbody>
          <tr v-for="e in suppRows" :key="e.student">
            <td>
              {{ e.student_name }}
              <div class="ec-muted">{{ e.sitting }} · CA {{ e.ca_mark }}<template v-if="e.special_reason"> · {{ e.special_reason }}</template></div>
            </td>
            <td class="num">{{ e.sitting === "Special" ? "Absent" : (e.first_final_mark ?? e.final_mark) }}</td>
            <td class="num">
              <InputNumber v-if="suppOpen" v-model="e.supp_exam_mark" :min="0" :max="100" :max-fraction-digits="1" size="small" :aria-label="`${e.sitting}, ${e.student_name}`" fluid />
              <template v-else>{{ e.supp_exam_mark ?? "" }}</template>
            </td>
            <td class="num final">{{ suppOpen ? (liveSupp(e).final_mark ?? "") : (e.first_result ? e.final_mark : "") }}</td>
            <td>{{ suppOpen ? (liveSupp(e).grade ?? "") : (e.first_result ? e.grade : "") }}</td>
            <td>
              <StatusTag v-if="suppOpen && liveSupp(e).result" kind="result" :value="liveSupp(e).result" />
              <StatusTag v-else-if="!suppOpen && e.first_result" kind="result" :value="e.result" />
            </td>
          </tr>
        </tbody>
      </table>
      <template v-if="suppOpen" #footer>
        <EcButton label="Save" size="sm" :loading="saving" :disabled="!suppChanged" @click="saveSupp()" />
        <EcButton label="Submit these marks" size="sm" variant="primary" :disabled="saving || suppMissing > 0" @click="submitSupp" />
      </template>
    </EcPanel>
  </template>

  <EcModal :open="confirming" title="Submit the marks?" description="The department moderates them next; they are returned to you if anything needs changing." @update:open="(v: boolean) => (confirming = v)">
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="confirming = false" />
      <EcButton label="Submit" variant="primary" :loading="saving" @click="submit" />
    </template>
  </EcModal>
</template>

<style scoped>
.marks {
  table-layout: fixed;
}

.c-mark {
  width: 8rem;
}

.c-absent {
  width: 5.5rem;
}

.c-final {
  width: 5rem;
}

.c-grade {
  width: 4.5rem;
}

.c-result {
  width: 9.5rem;
}

.final {
  font-weight: 600;
}

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
  overflow-y: auto;
}

.sticky thead th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: var(--ec-surface, #fff);
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
}
</style>
