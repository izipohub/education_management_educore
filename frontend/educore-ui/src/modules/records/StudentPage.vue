<script setup lang="ts">
import { semesterLabel } from "@/modules/curriculum/api";
import { FileText } from "@lucide/vue";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { proofOfRegistrationUrl } from "@/core/documents";
import { formatDate, formatMoney } from "@/core/format";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type StudentRecord, getStudent } from "./api";

/** One student's record: each year's registration, fees, documents; who they are and who to reach beside it */
const props = defineProps<{ name: string }>();
const route = useRoute();
const record = ref<StudentRecord | null>(null);
const error = ref("");

watch(
  () => props.name,
  async () => {
    record.value = null;
    error.value = "";
    try {
      record.value = await getStudent(props.name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

const back = computed(() => ({ to: { name: "students", query: route.query }, label: "Students" }));
const p = computed(() => record.value?.particulars ?? {});
const current = computed(() => record.value?.enrolments[0] ?? null);
/** the latest year the student is registered for: what a proof of registration confirms */
const registered = computed(() => record.value?.enrolments.find((e) => e.status === "Registered") ?? null);
const subtitle = computed(() => {
  const r = record.value;
  return r ? [r.name, current.value?.program, r.campus].filter(Boolean).join(" · ") : "";
});
const identity = computed(() => p.value.educore_national_id || p.value.educore_passport_number);
</script>

<template>
  <RecordPage :back="back" :title="record?.student_name" :subtitle="subtitle" :error="error">
    <template #tags>
      <StatusTag v-if="record" kind="standing" :value="record.standing" />
      <span v-if="record && !record.enabled" class="left">Left</span>
    </template>

    <template v-if="registered" #actions>
      <a class="pdf" :href="proofOfRegistrationUrl(registered.name)" target="_blank" rel="noopener">
        <FileText :size="16" aria-hidden="true" /> Proof of registration {{ registered.academic_year }}
      </a>
    </template>

    <template v-if="record">
      <EcPanel title="Registration" flush>
        <table v-if="record.enrolments.length" class="ec-table">
          <thead>
            <tr><th>Year</th><th>Programme</th><th class="num">Year of study</th><th class="num">Credits</th><th>Status</th><th aria-hidden="true"></th></tr>
          </thead>
          <tbody>
            <tr v-for="e in record.enrolments" :key="e.name">
              <td>{{ e.academic_year }}</td>
              <td>
                {{ e.program }}
                <div class="ec-muted">{{ e.offering }}<template v-if="e.enrollment_date"> · from {{ formatDate(e.enrollment_date) }}</template></div>
              </td>
              <td class="num">{{ e.year_of_study || "" }}</td>
              <td class="num">{{ e.credits }}</td>
              <td>
                <StatusTag v-if="e.status !== 'Registered'" kind="registration" :value="e.status" />
                <span v-else>Registered</span>
              </td>
              <td class="num">
                <a v-if="e.status === 'Registered'" :href="proofOfRegistrationUrl(e.name)" target="_blank" rel="noopener" class="link">PDF</a>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">Not registered yet</p>
      </EcPanel>

      <EcPanel v-if="current?.courses.length" :title="`Courses ${current.academic_year}`" :note="`${current.credits} credits`" flush>
        <table class="ec-table">
          <tbody>
            <tr v-for="c in current.courses" :key="c.course">
              <td class="ec-nowrap ec-muted">{{ semesterLabel(c.semester) }}</td>
              <td>{{ c.course_name }}</td>
              <td class="num">{{ c.credits }}</td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel title="Fees" :note="record.owing ? `${formatMoney(record.owing)} owing` : 'Nothing owing'" flush>
        <table v-if="record.invoices.length" class="ec-table">
          <thead>
            <tr><th>Invoice</th><th>Date</th><th class="num">Amount</th><th class="num">Owing</th><th>Status</th></tr>
          </thead>
          <tbody>
            <tr v-for="i in record.invoices" :key="i.name">
              <td>{{ i.name }}</td>
              <td class="ec-nowrap">{{ formatDate(i.posting_date) }}</td>
              <td class="num ec-nowrap">{{ formatMoney(i.grand_total) }}</td>
              <td class="num ec-nowrap">{{ formatMoney(i.outstanding_amount) }}</td>
              <td>{{ i.status }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No invoices</p>
      </EcPanel>

      <EcPanel v-if="record.documents.length" title="Documents" flush>
        <table class="ec-table">
          <tbody>
            <tr v-for="d in record.documents" :key="d.document_type">
              <td><a v-if="d.file_url" :href="d.file_url" target="_blank" rel="noopener">{{ d.document_type }}</a><template v-else>{{ d.document_type }}</template></td>
              <td class="num"><StatusTag kind="document" :value="d.status" /></td>
            </tr>
          </tbody>
        </table>
      </EcPanel>
    </template>

    <template v-if="record" #aside>
      <EcPanel title="Student">
        <dl class="ec-facts stacked">
          <div><dt>Full name</dt><dd>{{ [p.educore_title, record.student_name].filter(Boolean).join(" ") }}</dd></div>
          <div><dt>{{ p.educore_national_id ? "National ID" : "Passport" }}</dt><dd>{{ identity || "Not recorded" }}</dd></div>
          <div v-if="record.personal.date_of_birth"><dt>Date of birth</dt><dd>{{ formatDate(record.personal.date_of_birth) }}</dd></div>
          <div v-if="record.personal.gender"><dt>Gender</dt><dd>{{ record.personal.gender }}</dd></div>
          <div v-if="record.personal.nationality"><dt>Nationality</dt><dd>{{ record.personal.nationality }}</dd></div>
          <div v-if="p.educore_home_language"><dt>Home language</dt><dd>{{ p.educore_home_language }}</dd></div>
          <div v-if="p.educore_region_of_origin || p.educore_home_town"><dt>Origin</dt><dd>{{ [p.educore_home_town, p.educore_region_of_origin].filter(Boolean).join(", ") }}</dd></div>
          <div v-if="record.joining_date"><dt>Joined</dt><dd>{{ formatDate(record.joining_date) }}</dd></div>
          <div v-if="record.application"><dt>Application</dt><dd>{{ record.application }}</dd></div>
        </dl>
      </EcPanel>

      <EcPanel title="Contact">
        <dl class="ec-facts stacked">
          <div><dt>Email</dt><dd>{{ record.personal.email || "Not recorded" }}</dd></div>
          <div><dt>Mobile</dt><dd>{{ record.personal.mobile || "Not recorded" }}</dd></div>
          <div v-if="record.personal.address || record.personal.city"><dt>Address</dt><dd>{{ [record.personal.address, record.personal.city].filter(Boolean).join(", ") }}</dd></div>
          <div v-if="p.educore_postal_address"><dt>Postal address</dt><dd>{{ p.educore_postal_address }}</dd></div>
        </dl>
      </EcPanel>

      <EcPanel title="Next of kin">
        <dl v-if="record.guardians.length" class="ec-facts stacked">
          <div v-for="g in record.guardians" :key="g.name">
            <dt>{{ g.relation === "Others" ? "Next of kin" : g.relation }}</dt>
            <dd>{{ g.name }}<template v-if="g.phone"> · {{ g.phone }}</template><template v-if="g.email"> · {{ g.email }}</template></dd>
          </div>
        </dl>
        <p v-else class="none ec-muted">Not recorded</p>
      </EcPanel>

      <EcPanel title="Fees paid by">
        <p class="none">{{ p.educore_fee_payer ? (p.educore_fee_payer_name || p.educore_fee_payer) : "Not recorded" }}</p>
      </EcPanel>

      <EcPanel v-if="p.educore_disability" title="Support">
        <p class="none">{{ p.educore_support_needs || "Has a disability or impairment" }}</p>
      </EcPanel>

      <EcPanel v-if="record.standing_note" title="Standing">
        <p class="none">{{ record.standing_note }}</p>
      </EcPanel>
    </template>
  </RecordPage>
</template>

<style scoped>
.none {
  margin: 0;
}

.left {
  color: var(--ec-muted);
  font-size: 0.8125rem;
}

.pdf {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  height: 2.375rem;
  padding: 0 0.95rem;
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface);
  color: var(--ec-ink);
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
}

.pdf:hover {
  border-color: color-mix(in srgb, var(--ec-accent) 40%, var(--ec-border));
}

.link {
  color: var(--ec-accent);
  font-weight: 600;
  text-decoration: none;
}
</style>
