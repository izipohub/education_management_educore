<script setup lang="ts">
import { X } from "@lucide/vue";
import Checkbox from "primevue/checkbox";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import { type Curriculum, type CurriculumCourse, SEMESTERS, type Semester, getCurriculum, saveCurriculum, semesterLabel } from "./api";

/**
 * A programme's curriculum, one panel per year of study, its courses grouped by when they run (Semester 1,
 * Semester 2, the full year) with the credits of each. A course moves between periods or years with its selects;
 * Save keeps the whole layout.
 */
const props = defineProps<{ name: string }>();
/** the faculty edits; the Registrar's office sees the same layout, read only */
const editable = computed(() => Boolean(data.value?.can_edit));
const toast = useToast();
const data = ref<Curriculum | null>(null);
const rows = ref<CurriculumCourse[]>([]);
const error = ref("");
const saving = ref(false);

function take(c: Curriculum) {
  data.value = c;
  rows.value = c.courses.map((r) => ({ ...r }));
}
watch(
  () => props.name,
  async () => {
    data.value = null;
    error.value = "";
    try {
      take(await getCurriculum(props.name));
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

const key = (r: Pick<CurriculumCourse, "course" | "year" | "semester" | "required" | "prerequisites">) =>
  `${r.course}|${r.year}|${r.semester}|${r.required}|${[...r.prerequisites].sort().join("+")}`;
const changed = computed(() => {
  const saved = (data.value?.courses ?? []).map(key).sort().join(",");
  return saved !== rows.value.map(key).sort().join(",");
});

const years = computed(() => {
  const most = Math.max(data.value?.duration ?? 1, ...rows.value.map((r) => r.year));
  return Array.from({ length: most }, (_, i) => i + 1);
});
const inYear = (year: number) => rows.value.filter((r) => r.year === year);
const inPeriod = (year: number, semester: Semester) =>
  inYear(year)
    .filter((r) => r.semester === semester)
    .sort((a, b) => (a.code ?? a.course).localeCompare(b.code ?? b.course));
const credits = (list: CurriculumCourse[]) => list.reduce((sum, r) => sum + (r.credits ?? 0), 0);
const yearNote = (year: number) => {
  const parts = SEMESTERS.map((s) => [s, credits(inPeriod(year, s))] as const)
    .filter(([, c]) => c)
    .map(([s, c]) => `${semesterLabel(s)} ${c}`);
  return `${credits(inYear(year))} credits${parts.length ? ` · ${parts.join(" · ")}` : ""}`;
};

const periodOptions = SEMESTERS.map((s) => ({ value: s, label: semesterLabel(s) }));
const yearOptions = computed(() => years.value.map((y) => ({ value: y, label: `Year ${y}` })));

// adding a course from the catalogue to a year (Semester 1 to start with)
const adding = ref<Record<number, string | null>>({});
const available = computed(() => {
  const taken = new Set(rows.value.map((r) => r.course));
  return (data.value?.catalogue ?? [])
    .filter((c) => !taken.has(c.course))
    .map((c) => ({ value: c.course, label: [c.code, c.course].filter(Boolean).join(" · ") }));
});
function add(year: number) {
  const course = adding.value[year];
  const c = data.value?.catalogue.find((x) => x.course === course);
  if (!c) return;
  rows.value.push({ course: c.course, course_name: c.course, code: c.code, credits: c.credits ?? 0, nqf_level: c.nqf_level, year, semester: "Semester 1", required: true, prerequisites: [] });
  adding.value[year] = null;
}
const remove = (r: CurriculumCourse) => rows.value.splice(rows.value.indexOf(r), 1);

async function save() {
  saving.value = true;
  try {
    take(await saveCurriculum(props.name, rows.value.map(({ course, year, semester, required, prerequisites }) => ({ course, year, semester, required, prerequisites }))));
    toast.add({ severity: "success", summary: "Curriculum saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
const undo = () => data.value && take(data.value);

// prerequisites: the courses to pass first, chosen in a small dialog
const editingNeeds = ref<CurriculumCourse | null>(null);
const needs = ref<string[]>([]);
const needOptions = computed(() =>
  (data.value?.catalogue ?? [])
    .filter((c) => c.course !== editingNeeds.value?.course)
    .map((c) => ({ value: c.course, label: [c.code, c.course].filter(Boolean).join(" · ") })),
);
function startNeeds(r: CurriculumCourse) {
  editingNeeds.value = r;
  needs.value = [...r.prerequisites];
}
function applyNeeds() {
  if (editingNeeds.value) editingNeeds.value.prerequisites = [...needs.value];
  editingNeeds.value = null;
}

const subtitle = computed(() => {
  const d = data.value;
  return d
    ? [d.code, d.qualification, d.nqf_level ? `NQF ${d.nqf_level}` : "", d.faculty, d.duration ? `${d.duration} years` : ""].filter(Boolean).join(" · ")
    : "";
});
</script>

<template>
  <RecordPage :back="{ to: { name: 'curriculum' }, label: 'Curriculum' }" :title="data?.name" :subtitle="subtitle" :error="error">
    <template v-if="data && !editable" #tags><span class="read-only">Set by the faculty</span></template>
    <template v-if="data">
      <EcPanel v-for="year in years" :key="year" :title="`Year ${year}`" :note="yearNote(year)" flush>
        <table class="ec-table curriculum">
          <!-- the same widths in every year, so the columns line up from one year to the next -->
          <colgroup>
            <col class="c-code" />
            <col />
            <col class="c-num" />
            <col class="c-num" />
            <col class="c-required" />
            <template v-if="editable">
              <col class="c-period" />
              <col class="c-year" />
              <col class="c-remove" />
            </template>
          </colgroup>
          <thead>
            <tr>
              <th>Code</th>
              <th>Course</th>
              <th class="num">NQF</th>
              <th class="num">Credits</th>
              <th>Required</th>
              <th v-if="editable">Runs in</th>
              <th v-if="editable">Year</th>
              <th v-if="editable" aria-hidden="true"></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="semester in SEMESTERS" :key="semester">
              <template v-if="inPeriod(year, semester).length">
                <tr class="group">
                  <td colspan="3">{{ semesterLabel(semester) }}</td>
                  <td class="num">{{ credits(inPeriod(year, semester)) }}</td>
                  <td :colspan="editable ? 4 : 1"></td>
                </tr>
                <tr v-for="r in inPeriod(year, semester)" :key="r.course">
                  <td class="ec-nowrap">{{ r.code }}</td>
                  <td>
                    {{ r.course_name }}
                    <div v-if="r.prerequisites.length" class="needs">Needs {{ r.prerequisites.join(", ") }} passed</div>
                    <button v-if="editable" type="button" class="needs-edit" @click="startNeeds(r)">{{ r.prerequisites.length ? "Change prerequisites" : "Add a prerequisite" }}</button>
                  </td>
                  <td class="num">{{ r.nqf_level ?? "" }}</td>
                  <td class="num">{{ r.credits }}</td>
                  <td v-if="editable"><Checkbox v-model="r.required" binary :aria-label="`${r.course_name} required`" /></td>
                  <td v-else>{{ r.required ? "Required" : "Elective" }}</td>
                  <template v-if="editable">
                    <td><Select v-model="r.semester" :options="periodOptions" option-label="label" option-value="value" size="small" :aria-label="`When ${r.course_name} runs`" class="period" /></td>
                    <td><Select v-model="r.year" :options="yearOptions" option-label="label" option-value="value" size="small" :aria-label="`Year of ${r.course_name}`" class="year" /></td>
                    <td class="num"><EcButton :icon="X" size="sm" variant="ghost" :aria-label="`Remove ${r.course_name}`" @click="remove(r)" /></td>
                  </template>
                </tr>
              </template>
            </template>
            <tr v-if="!inYear(year).length">
              <td :colspan="editable ? 8 : 5" class="ec-muted">No courses in year {{ year }} yet</td>
            </tr>
          </tbody>
        </table>
        <template v-if="editable" #footer>
          <Select
            v-model="adding[year]"
            :options="available"
            option-label="label"
            option-value="value"
            filter
            placeholder="Add a course"
            size="small"
            :aria-label="`Add a course to year ${year}`"
            class="add"
            @change="add(year)"
          />
        </template>
      </EcPanel>

      <!-- only once something changed -->
      <div v-if="editable && (changed || saving)" class="save-bar">
        <span class="ec-muted">Unsaved changes</span>
        <EcButton label="Undo" variant="ghost" :disabled="saving" @click="undo" />
        <EcButton label="Save" variant="primary" :loading="saving" @click="save" />
      </div>
    </template>
  </RecordPage>

  <EcModal :open="editingNeeds !== null" :title="`Prerequisites: ${editingNeeds?.course_name ?? ''}`" description="Courses to pass first, wherever this course is taught" @update:open="(v: boolean) => !v && (editingNeeds = null)">
    <EcField label="Courses to pass first" for="needs">
      <MultiSelect v-model="needs" input-id="needs" :options="needOptions" option-label="label" option-value="value" filter display="chip" placeholder="None" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="editingNeeds = null" />
      <EcButton label="Done" variant="primary" @click="applyNeeds" />
    </template>
  </EcModal>
</template>

<style scoped>
.curriculum {
  table-layout: fixed;
}

.curriculum td {
  vertical-align: middle;
  overflow-wrap: anywhere;
}

.c-code {
  width: 7.5rem;
}

.c-num {
  width: 5.5rem;
}

.c-required {
  width: 7rem;
}

.c-period {
  width: 10.5rem;
}

.c-year {
  width: 9rem;
}

.c-remove {
  width: 3.5rem;
}

.period,
.year {
  width: 100%;
}

.needs {
  color: var(--ec-muted);
  font-size: 0.75rem;
}

.needs-edit {
  padding: 0;
  border: 0;
  background: none;
  color: var(--ec-accent);
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.read-only {
  color: var(--ec-muted);
  font-size: 0.8125rem;
}

.group td {
  background: var(--ec-surface-muted);
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.add {
  width: min(100%, 24rem);
  margin-right: auto;
}

.save-bar {
  position: sticky;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: var(--ec-surface);
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius);
  box-shadow: 0 -2px 8px rgb(0 0 0 / 0.05);
}

.save-bar .ec-muted {
  margin-right: auto;
}
</style>
