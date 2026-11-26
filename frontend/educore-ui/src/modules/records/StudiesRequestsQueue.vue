<script setup lang="ts">
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { useToast } from "primevue/usetoast";
import { onMounted, ref, watch } from "vue";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcSegmented from "@/core/ui/EcSegmented.vue";
import { type RequestQueue, type RequestStatus, type StudiesRequest, approveRequest, declineRequest, describeRequest, requestQueue } from "./studiesRequests";

/** Requests to interrupt or cancel studies, or to move campus, for the Registry to decide */
const emit = defineEmits<{ counts: [Record<RequestStatus, number>] }>();
const toast = useToast();
const status = ref<RequestStatus>("Submitted");
const page = ref<RequestQueue | null>(null);
const error = ref("");
const busy = ref("");

async function load() {
  error.value = "";
  try {
    page.value = await requestQueue(status.value);
    emit("counts", page.value.counts);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
onMounted(load);
watch(status, load);

const approving = ref<StudiesRequest | null>(null);
async function approve() {
  const r = approving.value;
  if (!r) return;
  busy.value = r.name;
  try {
    await approveRequest(r.name);
    toast.add({ severity: "success", summary: `${r.request_type} approved for ${r.student_name}`, life: 3000 });
    approving.value = null;
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not approved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = "";
  }
}

const declining = ref<StudiesRequest | null>(null);
const note = ref("");
async function decline() {
  const r = declining.value;
  if (!r) return;
  busy.value = r.name;
  try {
    await declineRequest(r.name, note.value.trim());
    toast.add({ severity: "success", summary: "Declined", life: 2500 });
    declining.value = null;
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not declined", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = "";
  }
}
const statusOptions = [
  { value: "Submitted" as RequestStatus, label: "To decide" },
  { value: "Approved" as RequestStatus, label: "Approved" },
  { value: "Declined" as RequestStatus, label: "Declined" },
];
const what = describeRequest;
const approveNote = (r: StudiesRequest) =>
  r.request_type === "Cancellation"
    ? "The student leaves and comes off this year's class lists; returning means applying again."
    : r.request_type === "Campus transfer"
      ? `The student belongs to ${r.to_campus} from now (its Registry and Finance), and registers there from ${r.from_year}.`
      : `The student comes off this year's class lists and registers again for ${r.return_year}.`;
</script>

<template>
  <section class="ec-card queue">
    <div class="toolbar"><EcSegmented v-model="status" :options="statusOptions" label="Status" /></div>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <table v-else-if="page?.rows.length" class="ec-table">
      <thead>
        <tr><th>Student</th><th>Request</th><th>Last day</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="r in page.rows" :key="r.name">
          <td>
            <RouterLink :to="{ name: 'student-record', params: { name: r.student } }" class="who">{{ r.student_name }}</RouterLink>
            <div class="ec-muted">{{ r.student }} · {{ r.program }}</div>
          </td>
          <td>
            {{ what(r) }}
            <div class="ec-muted">{{ r.reason }}</div>
            <div v-if="r.review_note" class="ec-muted">Declined: {{ r.review_note }}</div>
          </td>
          <td class="ec-nowrap">{{ r.last_day ? formatDate(r.last_day) : "" }}</td>
          <td class="acts">
            <template v-if="r.status === 'Submitted'">
              <EcButton label="Decline" variant="ghost" size="sm" :disabled="Boolean(busy)" @click="(declining = r), (note = '')" />
              <EcButton label="Approve" variant="primary" size="sm" :disabled="Boolean(busy)" @click="approving = r" />
            </template>
            <span v-else class="ec-muted ec-nowrap">{{ formatDate(r.reviewed_on) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="none ec-muted">No requests here</p>
  </section>

  <EcModal
    :open="approving !== null"
    :title="approving ? `${approving.request_type}: ${approving.student_name}` : ''"
    :description="approving ? approveNote(approving) : ''"
    @update:open="(v: boolean) => !v && (approving = null)"
  >
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="approving = null" />
      <EcButton label="Approve" variant="primary" :loading="Boolean(busy)" @click="approve" />
    </template>
  </EcModal>

  <EcModal :open="declining !== null" :title="`Decline: ${declining?.student_name ?? ''}`" @update:open="(v: boolean) => !v && (declining = null)">
    <EcField label="Reason, shown to the student" for="decline-request-note">
      <InputText id="decline-request-note" v-model="note" fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="declining = null" />
      <EcButton label="Decline" variant="primary" :loading="Boolean(busy)" :disabled="!note.trim()" @click="decline" />
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

.acts {
  text-align: right;
  white-space: nowrap;
}

.none {
  margin: 0;
  padding: 2rem 1rem;
  text-align: center;
}
</style>
