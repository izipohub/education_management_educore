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
import { type ChangeQueue, type ChangeStatus, type CourseChange, approveChange, changeQueue, declineChange } from "./courseChanges";

/** Course changes: students' requests to add or drop courses after approval, for the faculty officer to decide */
const emit = defineEmits<{ counts: [Record<ChangeStatus, number>] }>();
const toast = useToast();
const status = ref<ChangeStatus>("Submitted");
const page = ref<ChangeQueue | null>(null);
const error = ref("");
const busy = ref("");

function take(q: ChangeQueue) {
  page.value = q;
  emit("counts", q.counts);
}
async function load() {
  error.value = "";
  try {
    take(await changeQueue(status.value));
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
onMounted(load);
watch(status, load);

async function approve(c: CourseChange) {
  busy.value = c.name;
  try {
    await approveChange(c.name);
    toast.add({ severity: "success", summary: `${c.student_name}'s courses changed`, life: 3000 });
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not approved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = "";
  }
}

const declining = ref<CourseChange | null>(null);
const note = ref("");
async function decline() {
  const c = declining.value;
  if (!c) return;
  busy.value = c.name;
  try {
    await declineChange(c.name, note.value.trim());
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
  { value: "Submitted" as ChangeStatus, label: "To decide" },
  { value: "Approved" as ChangeStatus, label: "Approved" },
  { value: "Declined" as ChangeStatus, label: "Declined" },
];
</script>

<template>
  <section class="ec-card queue">
    <div class="toolbar">
      <EcSegmented v-model="status" :options="statusOptions" label="Status" />
      <span class="ec-muted">{{ page?.changes_until ? `Course changes until ${formatDate(page.changes_until)}` : "No course change date set" }}</span>
    </div>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <table v-else-if="page?.rows.length" class="ec-table">
      <thead>
        <tr><th>Student</th><th>Changes</th><th>Submitted</th><th></th></tr>
      </thead>
      <tbody>
        <tr v-for="c in page.rows" :key="c.name">
          <td>
            {{ c.student_name }}
            <div class="ec-muted">{{ c.student }} · {{ c.program }}</div>
          </td>
          <td>
            <div v-for="i in c.items" :key="i.course">
              <span :class="i.action === 'Add' ? 'add' : 'drop'">{{ i.action }}</span> {{ i.course_name }} <span class="ec-muted">{{ i.credits }} cr</span>
            </div>
            <div v-if="c.reason" class="ec-muted">{{ c.reason }}</div>
            <div v-if="c.review_note" class="ec-muted">Declined: {{ c.review_note }}</div>
          </td>
          <td class="ec-nowrap">{{ formatDate(c.submitted_on) }}</td>
          <td class="acts">
            <template v-if="c.status === 'Submitted'">
              <EcButton label="Decline" variant="ghost" size="sm" :disabled="Boolean(busy)" @click="(declining = c), (note = '')" />
              <EcButton label="Approve" variant="primary" size="sm" :loading="busy === c.name" :disabled="Boolean(busy)" @click="approve(c)" />
            </template>
            <span v-else class="ec-muted ec-nowrap">{{ formatDate(c.reviewed_on) }}</span>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="none ec-muted">No course changes here</p>
  </section>

  <EcModal :open="declining !== null" :title="`Decline: ${declining?.student_name ?? ''}`" @update:open="(v: boolean) => !v && (declining = null)">
    <EcField label="Reason, shown to the student" for="decline-note">
      <InputText id="decline-note" v-model="note" fluid />
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
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--ec-border);
}

.add,
.drop {
  display: inline-block;
  min-width: 2.5rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.add {
  color: var(--ec-accent);
}

.drop {
  color: var(--ec-muted);
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
