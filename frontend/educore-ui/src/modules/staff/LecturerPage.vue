<script setup lang="ts">
import AutoComplete from "primevue/autocomplete";
import MultiSelect from "primevue/multiselect";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useSession } from "@/core/auth/session";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { ALLOCATION_ROLES } from "@/modules/teaching/allocation";
import { type Lecturer, type StaffRecord, findStaffRecords, getLecturer, linkStaffRecord, saveLecturer, setLeft } from "./api";

/** One lecturer: their teaching department and campuses, the classes they teach, their login and HR staff record */
const props = defineProps<{ name: string }>();
const route = useRoute();
const toast = useToast();
const session = useSession();
const lecturer = ref<Lecturer | null>(null);
const error = ref("");
const busy = ref(false);
const editing = ref(false);

async function load() {
  try {
    lecturer.value = await getLecturer(props.name);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch(
  () => props.name,
  () => {
    lecturer.value = null;
    error.value = "";
    editing.value = false;
    void load();
  },
  { immediate: true },
);

const back = computed(() => {
  const { from, ...query } = route.query;
  return from === "workload" ? { to: { name: "workload", query }, label: "Workload" } : { to: { name: "academic-staff", query }, label: "Academic staff" };
});
const subtitle = computed(() => [lecturer.value?.department_label, lecturer.value?.user].filter(Boolean).join(" · "));
const outstanding = computed(() => {
  const l = lecturer.value;
  if (!l || l.state === "Left") return [];
  return [
    !l.department && "Teaching department to be set by the department or faculty",
    !l.campuses.length && "Campus to be set by the department or faculty",
    !l.employee && "HR staff record to be linked by HR",
  ].filter(Boolean) as string[];
});
const hours = (n: number | undefined) => `${Number((n ?? 0).toFixed(1))} h`;
const canOpenClass = computed(() => session.hasRole(...ALLOCATION_ROLES));

async function act(run: () => Promise<Lecturer>, done: string) {
  busy.value = true;
  try {
    lecturer.value = await run();
    toast.add({ severity: "success", summary: done, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}
// department and campuses (head of department, dean)
const department = ref<string | null>(null);
const campuses = ref<string[]>([]);
function edit() {
  department.value = lecturer.value?.department ?? null;
  campuses.value = [...(lecturer.value?.campuses ?? [])];
  editing.value = true;
}
async function save() {
  if (!lecturer.value) return;
  const data: { department?: string; campuses?: string[] } = { campuses: campuses.value };
  if (department.value) data.department = department.value;
  if (await act(() => saveLecturer(lecturer.value!.name, data), "Saved")) editing.value = false;
}

// left, or back
const leaving = ref(false);
async function markLeft(left: boolean) {
  if (await act(() => setLeft(lecturer.value!.name, left), left ? "Marked as left" : "Active again")) leaving.value = false;
}

// the HR staff record (HR)
const linking = ref(false);
const chosen = ref<(StaffRecord & { label: string }) | null>(null);
const suggestions = ref<(StaffRecord & { label: string })[]>([]);
async function searchRecords(event: { query: string }) {
  const found = await findStaffRecords(event.query).catch(() => []);
  suggestions.value = found.map((r) => ({ ...r, label: [r.employee_name, r.name, r.department].filter(Boolean).join(" · ") }));
}
async function link() {
  if (!lecturer.value || !chosen.value || typeof chosen.value !== "object") return;
  if (await act(() => linkStaffRecord(lecturer.value!.name, chosen.value!.name), "Staff record linked")) {
    linking.value = false;
    chosen.value = null;
  }
}
</script>

<template>
  <RecordPage :back="back" :title="lecturer?.instructor_name" :subtitle="subtitle" :error="error" :outstanding="outstanding">
    <template #tags>
      <StatusTag v-if="lecturer" kind="lecturer" :value="lecturer.state" />
    </template>

    <template v-if="lecturer" #actions>
      <EcButton v-if="lecturer.can_link" label="Link staff record" variant="primary" @click="(linking = true), (chosen = null)" />
      <template v-if="lecturer.can_edit">
        <EcButton v-if="lecturer.state === 'Left'" label="Active again" :loading="busy" @click="markLeft(false)" />
        <EcButton v-else label="Mark as left" variant="ghost" @click="leaving = true" />
      </template>
    </template>

    <template v-if="lecturer">
      <EcPanel title="Teaching">
        <dl v-if="!editing" class="ec-facts">
          <div><dt>Department</dt><dd>{{ lecturer.department_label || "Not set" }}</dd></div>
          <div><dt>Campuses</dt><dd>{{ lecturer.campuses.join(", ") || "Not set" }}</dd></div>
        </dl>
        <div v-else class="form">
          <EcField label="Department" for="lecturer-department">
            <Select v-model="department" input-id="lecturer-department" :options="lecturer.choices.departments" option-label="label" option-value="name" placeholder="Choose" fluid />
          </EcField>
          <EcField label="Campuses" for="lecturer-campuses">
            <MultiSelect v-model="campuses" input-id="lecturer-campuses" :options="lecturer.choices.campuses" display="chip" placeholder="Choose" fluid />
          </EcField>
        </div>
        <template v-if="lecturer.can_edit && lecturer.state !== 'Left'" #footer>
          <template v-if="editing">
            <EcButton label="Cancel" variant="ghost" size="sm" @click="editing = false" />
            <EcButton label="Save" variant="primary" size="sm" :loading="busy" :disabled="!campuses.length" @click="save" />
          </template>
          <EcButton v-else label="Edit" variant="ghost" size="sm" @click="edit" />
        </template>
      </EcPanel>

      <EcPanel v-if="lecturer.workload?.academic_year" title="Workload" :note="`${lecturer.workload.semester} ${lecturer.workload.academic_year}`" class="workload">
        <dl class="ec-facts">
          <div>
            <dt>Hours a week</dt>
            <dd>
              {{ hours(lecturer.workload.hours) }}
              <StatusTag kind="workload" :value="lecturer.workload.status" />
              <span class="ec-muted">of {{ lecturer.workload.rule.min_hours }} to {{ lecturer.workload.rule.max_hours }} h</span>
            </dd>
          </div>
          <div><dt>Students</dt><dd>{{ lecturer.workload.students ?? 0 }}</dd></div>
          <div><dt>Invigilation</dt><dd>{{ lecturer.workload.invigilation ? hours(lecturer.workload.invigilation) : "None" }}</dd></div>
        </dl>
        <table v-if="lecturer.workload.modules?.length" class="ec-table">
          <thead>
            <tr><th>Module</th><th>Campus</th><th class="num">Students</th><th class="num">Hours a week</th></tr>
          </thead>
          <tbody>
            <tr v-for="m in lecturer.workload.modules" :key="m.group">
              <td>
                {{ m.course_name || m.course }}
                <div class="ec-muted">{{ [m.code, m.with.length ? `with ${m.with.join(", ")}` : ""].filter(Boolean).join(" · ") }}</div>
              </td>
              <td>{{ m.campus?.replace(" Campus", "") }}</td>
              <td class="num">{{ m.students }}</td>
              <td class="num">{{ m.hours ? hours(m.hours) : "Not timetabled" }}</td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel title="Classes" :note="lecturer.classes.length ? `${lecturer.classes.length} classes` : undefined" :flush="lecturer.classes.length > 0">
        <table v-if="lecturer.classes.length" class="ec-table">
          <thead>
            <tr><th>Year</th><th>Course</th><th>Campus</th><th class="num">Students</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in lecturer.classes" :key="c.name">
              <td>{{ c.academic_year }}</td>
              <td>
                <RouterLink v-if="canOpenClass" :to="{ name: 'teaching-class', params: { group: c.name } }" class="link">{{ c.course_name || c.course }}</RouterLink>
                <template v-else>{{ c.course_name || c.course }}</template>
                <div class="ec-muted">{{ c.code }}</div>
              </td>
              <td>{{ c.campus?.replace(" Campus", "") }}</td>
              <td class="num">{{ c.students }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No classes allocated</p>
      </EcPanel>
    </template>

    <template v-if="lecturer" #aside>
      <EcPanel title="Login">
        <dl v-if="lecturer.login" class="ec-facts stacked">
          <div><dt>Email</dt><dd>{{ lecturer.login.name }}</dd></div>
          <div><dt>Last signed in</dt><dd>{{ lecturer.login.last_login ? formatDate(lecturer.login.last_login) : "Never" }}</dd></div>
          <div v-if="lecturer.positions.length"><dt>Positions</dt><dd>{{ lecturer.positions.join(", ") }}</dd></div>
          <div v-if="!lecturer.login.enabled"><dt>Access</dt><dd>Disabled</dd></div>
        </dl>
        <p v-else class="none ec-muted">No login</p>
      </EcPanel>

      <EcPanel title="HR staff record">
        <dl v-if="lecturer.staff_record" class="ec-facts stacked">
          <div><dt>Staff number</dt><dd>{{ lecturer.staff_record.name }}</dd></div>
          <div v-if="lecturer.staff_record.designation"><dt>Designation</dt><dd>{{ lecturer.staff_record.designation }}</dd></div>
          <div v-if="lecturer.staff_record.date_of_joining"><dt>Joined</dt><dd>{{ formatDate(lecturer.staff_record.date_of_joining) }}</dd></div>
        </dl>
        <p v-else class="none ec-muted">Not linked</p>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal :open="leaving" title="Mark as left" description="No longer allocated to classes. The classes already taught stay on record." @update:open="(v: boolean) => (leaving = v)">
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="leaving = false" />
      <EcButton label="Mark as left" variant="danger" :loading="busy" @click="markLeft(true)" />
    </template>
  </EcModal>

  <EcModal :open="linking" title="Link staff record" :description="lecturer?.instructor_name" @update:open="(v: boolean) => (linking = v)">
    <EcField label="Staff record" for="link-staff" hint="Name or staff number">
      <AutoComplete v-model="chosen" input-id="link-staff" :suggestions="suggestions" option-label="label" fluid @complete="searchRecords" />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="linking = false" />
      <EcButton label="Link" variant="primary" :loading="busy" :disabled="!chosen || typeof chosen !== 'object'" @click="link" />
    </template>
  </EcModal>
</template>

<style scoped>
.none {
  margin: 0;
}

.form {
  display: grid;
  gap: 0.75rem;
}

.workload .ec-table {
  margin-top: 1rem;
}

.workload dd {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.link {
  color: var(--ec-accent);
  font-weight: 600;
  text-decoration: none;
}
</style>
