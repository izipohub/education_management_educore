<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Entry, type Sheet, approve, getSheet, moderate, publish, returnSheet, workOut } from "./api";

/**
 * A class's marks for the department and the examinations office: the results and how the class did, who did
 * what and when, and the next step for this person's office (moderate or return; approve or return; publish).
 */
const props = defineProps<{ group: string }>();
const route = useRoute();
const toast = useToast();
const sheet = ref<Sheet | null>(null);
const rows = ref<Entry[]>([]);
const error = ref("");
const busy = ref(false);

function take(s: Sheet) {
  sheet.value = s;
  rows.value = s.entries.map((e) => ({ ...e }));
}
async function load() {
  error.value = "";
  try {
    take(await getSheet(props.group));
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch(() => props.group, load, { immediate: true });

const back = computed(() => ({ to: { name: "examinations", query: route.query }, label: "Examinations" }));
const adjusting = computed(() => Boolean(sheet.value?.can_moderate));
const input = (e: Entry) => ({ student: e.student, ca_mark: e.ca_mark, exam_mark: e.exam_mark, absent: e.absent });
const changed = computed(() => JSON.stringify(rows.value.map(input)) !== JSON.stringify((sheet.value?.entries ?? []).map(input)));
const live = (e: Entry) => (sheet.value ? workOut(e, sheet.value.rules) : { final_mark: null, grade: null, result: null });

async function run(call: () => Promise<Sheet | unknown>, message: string) {
  busy.value = true;
  try {
    const result = await call();
    if (result && typeof result === "object" && "entries" in (result as Sheet)) take(result as Sheet);
    else await load();
    toast.add({ severity: "success", summary: message, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not done", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

// moderating, with the reason when marks were changed
const moderating = ref(false);
const reason = ref("");
async function confirmModerate() {
  const ok = await run(() => moderate(props.group, changed.value ? rows.value.map(input) : undefined, reason.value.trim() || undefined), "Moderated");
  if (ok) moderating.value = false;
}
// returning one step, with a note
const returning = ref(false);
const note = ref("");
async function confirmReturn() {
  if (await run(() => returnSheet(props.group, note.value.trim()), "Returned")) returning.value = false;
}
// approving, with the board's meeting
const approving = ref(false);
const board = ref("");
async function confirmApprove() {
  if (await run(() => approve(props.group, board.value.trim()), "Approved")) approving.value = false;
}

const subtitle = computed(() => {
  const s = sheet.value;
  return s ? [s.course, s.campus?.replace(" Campus", ""), s.academic_year, s.lecturers.join(", ")].filter(Boolean).join(" · ") : "";
});
const counts = computed(() => sheet.value?.summary?.counts);
</script>

<template>
  <RecordPage :back="back" :title="sheet ? `${sheet.code ?? sheet.course} ${sheet.campus?.replace(' Campus', '') ?? ''}` : undefined" :subtitle="subtitle" :error="error">
    <template v-if="sheet" #tags><StatusTag kind="marks" :value="sheet.status" /></template>
    <template v-if="sheet && (sheet.can_moderate || sheet.can_approve || sheet.can_publish)" #actions>
      <template v-if="sheet.can_moderate">
        <EcButton label="Return to lecturer" :disabled="busy" @click="(returning = true), (note = '')" />
        <EcButton label="Moderated" variant="primary" :disabled="busy" @click="(moderating = true), (reason = '')" />
      </template>
      <template v-else-if="sheet.can_approve">
        <EcButton label="Return to department" :disabled="busy" @click="(returning = true), (note = '')" />
        <EcButton label="Approve" variant="primary" :disabled="busy" @click="(approving = true), (board = '')" />
      </template>
      <EcButton v-else-if="sheet.can_publish" label="Publish results" variant="primary" :loading="busy" @click="run(() => publish([group]), 'Results published')" />
    </template>

    <EcPanel v-if="sheet" title="Results" :note="sheet.status === 'Not started' ? 'No marks yet' : undefined" flush>
      <table v-if="rows.length" class="ec-table marks">
        <colgroup>
          <col />
          <col class="c-mark" />
          <col class="c-mark" />
          <col class="c-final" />
          <col class="c-grade" />
          <col class="c-result" />
        </colgroup>
        <thead>
          <tr><th>Student</th><th class="num">CA</th><th class="num">Examination</th><th class="num">Final</th><th>Grade</th><th>Result</th></tr>
        </thead>
        <tbody>
          <tr v-for="e in rows" :key="e.student">
            <td>
              {{ e.student_name }}
              <div class="ec-muted">{{ e.student }}</div>
              <div v-if="e.moderation_note" class="ec-muted">Moderated: {{ e.moderation_note }}</div>
            </td>
            <td class="num">
              <InputNumber v-if="adjusting" v-model="e.ca_mark" :min="0" :max="100" :max-fraction-digits="1" size="small" :aria-label="`CA, ${e.student_name}`" fluid />
              <template v-else>{{ e.ca_mark ?? "" }}</template>
            </td>
            <td class="num">
              <InputNumber v-if="adjusting && !e.absent" v-model="e.exam_mark" :min="0" :max="100" :max-fraction-digits="1" size="small" :aria-label="`Examination, ${e.student_name}`" fluid />
              <template v-else>{{ e.absent ? "Absent" : (e.exam_mark ?? "") }}</template>
            </td>
            <td class="num final">{{ live(e).final_mark ?? "" }}</td>
            <td>{{ live(e).grade ?? "" }}</td>
            <td><StatusTag v-if="live(e).result" kind="result" :value="live(e).result" /></td>
          </tr>
        </tbody>
      </table>
      <p v-else class="none ec-muted">The lecturer has not entered marks yet</p>
    </EcPanel>

    <template v-if="sheet" #aside>
      <EcPanel v-if="sheet.summary && sheet.entries.length" title="How the class did">
        <dl class="ec-facts stacked">
          <div v-if="sheet.summary.pass_rate !== null"><dt>Pass rate</dt><dd>{{ sheet.summary.pass_rate }}%</dd></div>
          <div v-if="sheet.summary.average !== null"><dt>Average final mark</dt><dd>{{ sheet.summary.average }}</dd></div>
          <div v-if="counts">
            <dt>Results</dt>
            <dd>
              {{ counts.Pass }} passed<template v-if="counts.Supplementary"> · {{ counts.Supplementary }} supplementary</template><template v-if="counts.Fail"> · {{ counts.Fail }} failed</template><template v-if="counts['Not admitted']"> · {{ counts["Not admitted"] }} not admitted</template><template v-if="counts.Absent"> · {{ counts.Absent }} absent</template>
            </dd>
          </div>
        </dl>
      </EcPanel>
      <EcPanel v-if="sheet.return_note" title="Returned with">
        <p class="none-pad">{{ sheet.return_note }}</p>
      </EcPanel>
      <EcPanel title="Who and when">
        <dl class="ec-facts stacked">
          <div v-if="sheet.trail.submitted_on"><dt>Submitted</dt><dd>{{ formatDate(sheet.trail.submitted_on) }}<template v-if="sheet.trail.submitted_by"> · {{ sheet.trail.submitted_by }}</template></dd></div>
          <div v-if="sheet.trail.moderated_on"><dt>Moderated</dt><dd>{{ formatDate(sheet.trail.moderated_on) }} · {{ sheet.trail.moderated_by }}</dd></div>
          <div v-if="sheet.trail.approved_on"><dt>Approved</dt><dd>{{ formatDate(sheet.trail.approved_on) }} · {{ sheet.trail.board_reference }}</dd></div>
          <div v-if="sheet.trail.published_on"><dt>Published</dt><dd>{{ formatDate(sheet.trail.published_on) }}</dd></div>
          <div v-if="!sheet.trail.submitted_on"><dt>Status</dt><dd>With the lecturer</dd></div>
        </dl>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal :open="moderating" title="Mark as moderated" @update:open="(v: boolean) => (moderating = v)">
    <EcField v-if="changed" label="Why the marks were changed" for="reason" hint="Kept beside each changed mark">
      <Textarea id="reason" v-model="reason" rows="2" auto-resize fluid />
    </EcField>
    <p v-else class="ec-muted">The marks stand as the lecturer submitted them.</p>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="moderating = false" />
      <EcButton label="Moderated" variant="primary" :loading="busy" :disabled="changed && !reason.trim()" @click="confirmModerate" />
    </template>
  </EcModal>

  <EcModal :open="returning" title="Return the marks" @update:open="(v: boolean) => (returning = v)">
    <EcField label="What needs changing" for="note">
      <Textarea id="note" v-model="note" rows="3" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="returning = false" />
      <EcButton label="Return" variant="danger" :loading="busy" :disabled="!note.trim()" @click="confirmReturn" />
    </template>
  </EcModal>

  <EcModal :open="approving" title="Approve the results" @update:open="(v: boolean) => (approving = v)">
    <EcField label="Examination board meeting" for="board" hint="E.g. Faculty Examination Board, 18-11-2026">
      <InputText id="board" v-model="board" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="approving = false" />
      <EcButton label="Approve" variant="primary" :loading="busy" :disabled="!board.trim()" @click="confirmApprove" />
    </template>
  </EcModal>
</template>

<style scoped>
.marks {
  table-layout: fixed;
}

.c-mark {
  width: 6.5rem;
}

.c-final {
  width: 4rem;
}

.c-grade {
  width: 3.75rem;
}

.c-result {
  width: 8.5rem;
}

.final {
  font-weight: 600;
}

.none {
  margin: 0;
  padding: 1rem 1.25rem;
}

.none-pad {
  margin: 0;
}
</style>
