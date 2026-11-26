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
import { type Entry, type Sheet, approve, approvePlan, getSheet, returnPlan, moderate, publish, grantSpecial, publishSupplementary, returnSheet, workOut } from "./api";

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

// the supplementary results, approved by the board
const publishingSupp = ref(false);
const suppBoard = ref("");
async function confirmPublishSupp() {
  if (await run(() => publishSupplementary(props.group, suppBoard.value.trim()), "Supplementary results published")) publishingSupp.value = false;
}
const suppRows = computed(() => rows.value.filter((e) => e.writes_supplementary));

// a special examination for an absence with a valid reason (the examinations office)
const granting = ref<Entry | null>(null);
const specialReason = ref("");
async function confirmGrant() {
  const e = granting.value;
  if (!e) return;
  if (await run(() => grantSpecial(props.group, e.student, specialReason.value.trim()), `Special examination granted to ${e.student_name}`)) granting.value = null;
}

// the assessment plan (the department, while the marks are with the lecturer)
const returningPlan = ref(false);
const planNote = ref("");
async function confirmReturnPlan() {
  if (await run(() => returnPlan(props.group, planNote.value.trim()), "Plan returned to the lecturer")) returningPlan.value = false;
}
const planNoteText = computed(() => {
  const p = sheet.value?.plan;
  if (!p) return undefined;
  if (p.status === "Approved" && p.approved_by) return `Approved by ${p.approved_by}${p.approved_on ? `, ${formatDate(p.approved_on)}` : ""}`;
  if (p.status === "Proposed") return "Submitted by the lecturer";
  return "With the lecturer";
});

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
      <EcButton v-else-if="sheet.can_publish_supp" label="Publish supplementary results" variant="primary" :disabled="busy" @click="(publishingSupp = true), (suppBoard = '')" />
    </template>

    <EcPanel v-if="sheet && sheet.assessments.length" title="Assessment plan" flush>
      <template #note>
        <span class="plan-head"><span class="ec-muted">{{ planNoteText }}</span><StatusTag kind="plan" :value="sheet.plan.status" /></span>
      </template>
      <table class="ec-table">
        <thead>
          <tr><th>Assessment</th><th>Type</th><th class="num">Out of</th><th class="num">Share of CA</th></tr>
        </thead>
        <tbody>
          <tr v-for="a in sheet.assessments" :key="a.assessment_key">
            <td>
              {{ a.title }}
              <div v-if="a.moodle_activity" class="ec-muted">
                Moodle: <a v-if="a.moodle_url" :href="a.moodle_url" target="_blank" rel="noopener" class="link">{{ a.moodle_activity }}</a><template v-else>{{ a.moodle_activity }}</template>
              </div>
            </td>
            <td>{{ a.kind }}</td>
            <td class="num">{{ a.out_of }}</td>
            <td class="num">{{ a.weight }}%</td>
          </tr>
        </tbody>
      </table>
      <p v-if="!sheet.plan.status && sheet.plan.note" class="plan-note ec-muted">Returned: {{ sheet.plan.note }}</p>
      <template v-if="sheet.can_approve_plan || sheet.can_return_plan" #footer>
        <EcButton v-if="sheet.can_return_plan" :label="sheet.plan.status === 'Approved' ? 'Return for a change' : 'Return to lecturer'" variant="ghost" size="sm" :disabled="busy" @click="(returningPlan = true), (planNote = '')" />
        <EcButton v-if="sheet.can_approve_plan" label="Approve plan" variant="primary" size="sm" :loading="busy" @click="run(() => approvePlan(group), 'Plan approved')" />
      </template>
    </EcPanel>

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
            <td>
              <StatusTag v-if="live(e).result" kind="result" :value="live(e).result" />
              <button v-if="sheet.can_grant_special && e.result === 'Absent' && e.sitting !== 'Special'" type="button" class="grant" @click="(granting = e), (specialReason = '')">Grant special</button>
              <div v-else-if="e.sitting === 'Special'" class="ec-muted">Special granted</div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-else class="none ec-muted">The lecturer has not entered marks yet</p>
    </EcPanel>

    <EcPanel v-if="sheet && suppRows.length && sheet.status === 'Published'" title="Supplementary and special examinations" :note="sheet.supp_status === 'Published' ? sheet.supp_board_reference ?? 'Published' : sheet.supp_status === 'Submitted' ? 'Marks submitted' : 'With the lecturer'" flush>
      <table class="ec-table">
        <thead><tr><th>Student</th><th class="num">First attempt</th><th class="num">Examination</th><th class="num">Final</th><th>Result</th></tr></thead>
        <tbody>
          <tr v-for="e in suppRows" :key="e.student">
            <td>{{ e.student_name }}<div class="ec-muted">{{ e.sitting }}<template v-if="e.special_reason"> · {{ e.special_reason }}</template></div></td>
            <td class="num">{{ e.sitting === "Special" ? "Absent" : (e.first_final_mark ?? e.final_mark) }}</td>
            <td class="num">{{ e.supp_exam_mark ?? "" }}</td>
            <td class="num">{{ e.first_result ? e.final_mark : "" }}</td>
            <td><StatusTag v-if="e.first_result" kind="result" :value="e.result" /></td>
          </tr>
        </tbody>
      </table>
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

  <EcModal
    :open="returningPlan"
    title="Return the assessment plan"
    :description="sheet?.plan.status === 'Approved' ? 'The lecturer changes it and submits it again; the scores of the assessments kept stay' : undefined"
    @update:open="(v: boolean) => (returningPlan = v)"
  >
    <EcField label="What needs changing" for="plan-note">
      <Textarea id="plan-note" v-model="planNote" rows="3" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="returningPlan = false" />
      <EcButton label="Return" variant="primary" :loading="busy" :disabled="!planNote.trim()" @click="confirmReturnPlan" />
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

  <EcModal :open="granting !== null" :title="`Special examination: ${granting?.student_name ?? ''}`" description="For an absence with a valid reason; written at the supplementary sitting and counted in full" @update:open="(v: boolean) => !v && (granting = null)">
    <EcField label="Reason" for="special-reason" hint="E.g. hospitalised, medical certificate seen">
      <InputText id="special-reason" v-model="specialReason" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="granting = null" />
      <EcButton label="Grant" variant="primary" :loading="busy" :disabled="!specialReason.trim()" @click="confirmGrant" />
    </template>
  </EcModal>

  <EcModal :open="publishingSupp" title="Publish the supplementary results" @update:open="(v: boolean) => (publishingSupp = v)">
    <EcField label="Examination board meeting" for="supp-board" hint="E.g. Supplementary Examination Board, 20-01-2027">
      <InputText id="supp-board" v-model="suppBoard" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="publishingSupp = false" />
      <EcButton label="Publish" variant="primary" :loading="busy" :disabled="!suppBoard.trim()" @click="confirmPublishSupp" />
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
.plan-head {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
}

.link {
  color: var(--ec-accent);
  text-decoration: none;
}

.plan-note {
  margin: 0;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--ec-border-soft);
  font-size: 0.85rem;
}

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

.grant {
  display: block;
  margin-top: 0.2rem;
  padding: 0;
  border: 0;
  background: none;
  color: var(--ec-accent);
  font: inherit;
  font-size: 0.75rem;
  font-weight: 600;
  cursor: pointer;
}

.none {
  margin: 0;
  padding: 1rem 1.25rem;
}

.none-pad {
  margin: 0;
}
</style>
