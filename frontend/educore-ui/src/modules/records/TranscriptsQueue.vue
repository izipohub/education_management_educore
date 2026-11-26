<script setup lang="ts">
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { useToast } from "primevue/usetoast";
import { onMounted, ref, watch } from "vue";
import { academicRecordUrl } from "@/core/documents";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import { type TranscriptQueue, type TranscriptRequest, type TranscriptStatus, declineTranscript, deliveryText, issueTranscript, transcriptQueue } from "./transcripts";

/** Official transcript requests, for the Registry to issue (once paid and cleared) or decline */
const emit = defineEmits<{ counts: [Record<TranscriptStatus, number>] }>();
const toast = useToast();
const status = ref<TranscriptStatus>("Requested");
const page = ref<TranscriptQueue | null>(null);
const error = ref("");
const busy = ref(false);

async function load() {
  error.value = "";
  try {
    page.value = await transcriptQueue(status.value);
    emit("counts", page.value.counts);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
onMounted(load);
watch(status, load);

async function run(action: () => Promise<TranscriptQueue>, done: string) {
  busy.value = true;
  try {
    page.value = await action();
    emit("counts", page.value.counts);
    toast.add({ severity: "success", summary: done, life: 3000 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

const issuing = ref<TranscriptRequest | null>(null);
async function issue() {
  const r = issuing.value!;
  if (await run(() => issueTranscript(r.name), r.delivery === "Email" ? `Emailed to ${r.email}` : `Issued to ${r.student_name}`)) issuing.value = null;
}
const declining = ref<TranscriptRequest | null>(null);
const note = ref("");
async function decline() {
  const r = declining.value!;
  if (await run(() => declineTranscript(r.name, note.value.trim()), "Declined")) declining.value = null;
}

const statusOptions = [
  { value: "Requested" as TranscriptStatus, label: "To issue" },
  { value: "Issued" as TranscriptStatus, label: "Issued" },
  { value: "Declined" as TranscriptStatus, label: "Declined" },
];
const issueNote = (r: TranscriptRequest) =>
  r.delivery === "Email"
    ? `The academic record is emailed to ${r.recipient} at ${r.email}, and the student is told.`
    : r.delivery === "Post"
      ? `Print it, stamp and sign it, and post it to ${r.recipient}. The student is told it was posted.`
      : "Print it, stamp and sign it for the student to collect. The student is told it is ready.";
</script>

<template>
  <section class="ec-card queue">
    <div class="toolbar"><EcSegmented v-model="status" :options="statusOptions" label="Status" /></div>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <table v-else-if="page?.rows.length" class="ec-table">
      <thead>
        <tr><th>Student</th><th>Transcript</th><th>Asked</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in page.rows" :key="r.name">
          <td>
            <RouterLink :to="{ name: 'student-record', params: { name: r.student } }" class="who">{{ r.student_name }}</RouterLink>
            <div class="ec-muted">{{ r.student }}</div>
          </td>
          <td>
            {{ deliveryText(r) }}<template v-if="r.copies > 1">, {{ r.copies }} copies</template>
            <div v-if="r.postal_address" class="ec-muted address">{{ r.postal_address }}</div>
            <div v-if="r.fee" class="ec-muted">Fee {{ formatMoney(r.fee) }}{{ r.paid ? ", paid" : ", not paid" }}</div>
            <div v-for="b in r.blockers ?? []" :key="b" class="blocker">{{ b }}</div>
            <div v-if="r.review_note" class="ec-muted">Declined: {{ r.review_note }}</div>
          </td>
          <td class="ec-nowrap">{{ formatDate(r.requested_on) }}</td>
          <td class="acts">
            <template v-if="r.status === 'Requested'">
              <a v-if="r.delivery !== 'Email'" :href="academicRecordUrl(r.student)" target="_blank" rel="noopener" class="print">Print</a>
              <EcButton label="Decline" variant="ghost" size="sm" :disabled="busy" @click="(declining = r), (note = '')" />
              <EcButton label="Issue" variant="primary" size="sm" :disabled="busy || (r.blockers?.length ?? 0) > 0" @click="issuing = r" />
            </template>
            <span v-else class="ec-muted ec-nowrap">{{ formatDate(r.issued_on) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="none ec-muted">No requests here</p>
  </section>

  <EcModal :open="issuing !== null" :title="`Issue the transcript: ${issuing?.student_name ?? ''}`" :description="issuing ? issueNote(issuing) : ''" @update:open="(v: boolean) => !v && (issuing = null)">
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="issuing = null" />
      <EcButton :label="issuing?.delivery === 'Email' ? 'Email it' : 'Issued'" variant="primary" :loading="busy" @click="issue" />
    </template>
  </EcModal>

  <EcModal :open="declining !== null" :title="`Decline: ${declining?.student_name ?? ''}`" description="An unpaid fee is cancelled" @update:open="(v: boolean) => !v && (declining = null)">
    <EcField label="Reason, shown to the student" for="decline-transcript-note">
      <InputText id="decline-transcript-note" v-model="note" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="declining = null" />
      <EcButton label="Decline" variant="primary" :loading="busy" :disabled="!note.trim()" @click="decline" />
    </template>
  </EcModal>
</template>

<style scoped>
.queue {
  overflow: hidden;
}

.toolbar {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--ec-border);
}

.who {
  color: inherit;
  font-weight: 600;
  text-decoration: none;
}

.address {
  white-space: pre-line;
}

.blocker {
  color: var(--ec-danger, #b42318);
  font-size: 0.8rem;
}

.acts {
  text-align: right;
  white-space: nowrap;
}

.print {
  margin-right: 0.5rem;
  font-size: 0.8125rem;
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
}
</style>
