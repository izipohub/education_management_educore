<script setup lang="ts">
import Checkbox from "primevue/checkbox";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import ToggleSwitch from "primevue/toggleswitch";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import { type AssessmentType, type FacultyTypes, getAssessmentTypes, saveAssessmentTypes } from "./api";

/**
 * The faculty's assessment types, kept by the Dean: the kinds of continuous assessment its lecturers may plan, whether
 * each is taken online in Moodle, and the most it may count for in a module's CA. A type keeps its name (plans use it
 * by name): one to rename is marked not in use and a new one added. Others read them.
 */
const toast = useToast();
const faculties = ref<FacultyTypes[]>([]);
const canEdit = ref(false);
const faculty = ref<string | null>(null);
const rows = ref<AssessmentType[]>([]);
const saving = ref(false);

function take(page: { faculties: FacultyTypes[]; can_edit: boolean }) {
  faculties.value = page.faculties;
  canEdit.value = page.can_edit;
  if (!faculty.value || !page.faculties.some((f) => f.faculty === faculty.value)) faculty.value = page.faculties[0]?.faculty ?? null;
  reset();
}
const current = computed(() => faculties.value.find((f) => f.faculty === faculty.value) ?? null);
function reset() {
  rows.value = (current.value?.types ?? []).map((t) => ({ ...t }));
}
onMounted(async () => take(await getAssessmentTypes()));

const options = computed(() => faculties.value.map((f) => ({ value: f.faculty, label: f.label })));
const changed = computed(() => JSON.stringify(rows.value) !== JSON.stringify(current.value?.types ?? []));
const ready = computed(() => rows.value.every((r) => r.type_name.trim()) && rows.value.some((r) => !r.disabled));
function add() {
  rows.value.push({ type_name: "", online: 0, max_share: 0, disabled: 0 });
}
async function save() {
  if (!faculty.value) return;
  saving.value = true;
  try {
    take(await saveAssessmentTypes(faculty.value, rows.value));
    toast.add({ severity: "success", summary: "Assessment types saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <EcPanel v-if="current" title="Assessment types" :note="canEdit ? undefined : 'Set by the Dean'" flush>
    <template v-if="options.length > 1" #note>
      <Select v-model="faculty" :options="options" option-label="label" option-value="value" size="small" aria-label="Faculty" :disabled="changed" @change="reset" />
    </template>
    <table class="ec-table types">
      <thead>
        <tr><th>Type</th><th>Online in Moodle</th><th class="num">Highest share of the CA</th><th>In use</th></tr>
      </thead>
      <tbody>
        <tr v-for="(t, i) in rows" :key="t.name ?? `new-${i}`" :class="{ off: t.disabled }">
          <td>
            <InputText v-if="canEdit && !t.name" v-model="t.type_name" size="small" :aria-label="`Type ${i + 1}`" fluid />
            <template v-else>{{ t.type_name }}</template>
          </td>
          <td>
            <Checkbox v-if="canEdit" v-model="t.online" :true-value="1" :false-value="0" binary :aria-label="`${t.type_name} online in Moodle`" />
            <template v-else>{{ t.online ? "Yes" : "" }}</template>
          </td>
          <td class="num">
            <InputNumber
              v-if="canEdit"
              :model-value="t.max_share || null"
              :min="1"
              :max="100"
              suffix="%"
              size="small"
              :aria-label="`${t.type_name} highest share`"
              placeholder="No limit"
              fluid
              @update:model-value="(v: number | null) => (t.max_share = v ?? 0)"
            />
            <template v-else>{{ t.max_share ? `${t.max_share}%` : "No limit" }}</template>
          </td>
          <td>
            <ToggleSwitch v-if="canEdit" :model-value="!t.disabled" :aria-label="`${t.type_name} in use`" @update:model-value="(v: boolean) => (t.disabled = v ? 0 : 1)" />
            <template v-else>{{ t.disabled ? "No" : "Yes" }}</template>
          </td>
        </tr>
      </tbody>
    </table>
    <template v-if="canEdit" #footer>
      <EcButton label="Add a type" variant="ghost" size="sm" @click="add" />
      <span class="grow" />
      <template v-if="changed">
        <EcButton label="Undo" variant="ghost" size="sm" @click="reset" />
        <EcButton label="Save" variant="primary" size="sm" :loading="saving" :disabled="!ready" @click="save" />
      </template>
    </template>
  </EcPanel>
</template>

<style scoped>
.types td {
  vertical-align: middle;
}

.types td:nth-child(3) {
  width: 11rem;
}

.types tr.off td {
  color: var(--ec-muted);
}

.grow {
  flex: 1;
}
</style>
