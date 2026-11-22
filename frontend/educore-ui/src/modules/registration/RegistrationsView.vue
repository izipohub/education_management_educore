<script setup lang="ts">
import Button from "primevue/button";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Dialog from "primevue/dialog";
import Message from "primevue/message";
import SelectButton from "primevue/selectbutton";
import Tag from "primevue/tag";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { formatDate } from "@/core/format";
import { type Queue, type QueueRow, approveRegistration, getQueue, returnRegistration } from "./api";

const toast = useToast();
const status = ref<"Submitted" | "Returned" | "Approved">("Submitted");
const page = ref<Queue | null>(null);
const loading = ref(false);
const loadError = ref("");
const busy = ref(new Set<string>());
const expanded = ref<Record<string, boolean>>({});

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await getQueue(status.value);
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(status, load);

const tabs = computed(() =>
  (["Submitted", "Returned", "Approved"] as const).map((s) => ({ label: `${s} (${page.value?.counts[s] ?? 0})`, value: s })),
);

async function approve(row: QueueRow) {
  busy.value.add(row.name);
  try {
    await approveRegistration(row.name);
    toast.add({ severity: "success", summary: `${row.student_name}: approved`, life: 3000 });
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not approved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value.delete(row.name);
  }
}

const returning = ref<QueueRow | null>(null);
const note = ref("");
async function confirmReturn() {
  const row = returning.value;
  if (!row || !note.value.trim()) return;
  returning.value = null;
  busy.value.add(row.name);
  try {
    await returnRegistration(row.name, note.value.trim());
    toast.add({ severity: "success", summary: `${row.student_name}: returned`, life: 3000 });
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not returned", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value.delete(row.name);
  }
}
</script>

<template>
  <section class="registrations">
    <header>
      <h1>{{ page?.academic_year ? `Registrations ${page.academic_year}` : "Registrations" }}</h1>
      <p class="sub">Returning students in your faculty and campus. Approving registers the student and invoices the year.</p>
    </header>

    <SelectButton v-model="status" :options="tabs" option-label="label" option-value="value" :allow-empty="false" aria-label="Status" class="tabs" />
    <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <DataTable :value="page?.rows ?? []" :loading="loading" data-key="name" class="table">
      <template #empty><p class="empty">Nothing here.</p></template>
      <Column header="Student">
        <template #body="{ data }">
          <strong>{{ data.student_name }}</strong>
          <div class="sub">{{ data.student }}<template v-if="data.submitted_on"> · {{ formatDate(data.submitted_on) }}</template></div>
        </template>
      </Column>
      <Column header="Programme">
        <template #body="{ data }">
          {{ data.program }}
          <div class="sub">{{ data.offering }} · year {{ data.year_of_study }}</div>
        </template>
      </Column>
      <Column header="Courses">
        <template #body="{ data }">
          <Button
            :label="`${data.courses.length} courses, ${data.credits} credits`"
            text
            size="small"
            :aria-expanded="Boolean(expanded[data.name])"
            @click="expanded[data.name] = !expanded[data.name]"
          />
          <ul v-if="expanded[data.name]" class="course-list">
            <li v-for="c in data.courses" :key="c.course">{{ c.course_name }} <span class="sub">{{ c.credits }} cr</span></li>
          </ul>
        </template>
      </Column>
      <Column header="">
        <template #body="{ data }">
          <div class="tags">
            <Tag v-if="data.late" severity="warn" value="Late" />
            <Tag v-if="data.standing && data.standing !== 'Good standing'" :severity="data.standing === 'Probation' ? 'warn' : 'danger'" :value="data.standing" />
          </div>
          <div v-if="data.review_note" class="sub">{{ data.review_note }}</div>
        </template>
      </Column>
      <Column v-if="status === 'Submitted'" header="" class="actions-col">
        <template #body="{ data }">
          <div class="actions">
            <Button label="Approve" size="small" :loading="busy.has(data.name)" @click="approve(data)" />
            <Button label="Return" size="small" severity="secondary" outlined :disabled="busy.has(data.name)" @click="(returning = data), (note = '')" />
          </div>
        </template>
      </Column>
    </DataTable>

    <Dialog
      :visible="returning !== null"
      modal
      :header="returning ? `Return: ${returning.student_name}` : ''"
      :style="{ width: 'min(30rem, calc(100vw - 32px))' }"
      @update:visible="(v: boolean) => !v && (returning = null)"
    >
      <label for="note" class="note-label">What should the student change? They see this.</label>
      <Textarea id="note" v-model="note" rows="3" auto-resize fluid />
      <template #footer>
        <Button label="Cancel" text @click="returning = null" />
        <Button label="Return" :disabled="!note.trim()" @click="confirmReturn" />
      </template>
    </Dialog>
  </section>
</template>

<style scoped>
.registrations {
  display: grid;
  gap: 1rem;
}

h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.tabs {
  justify-self: start;
}

.table {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  overflow: hidden;
}

.empty {
  margin: 0;
  color: #6b7280;
}

.course-list {
  margin: 0.25rem 0 0;
  padding-left: 1.1rem;
  font-size: 0.9rem;
}

.tags,
.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

:deep(.actions-col) {
  width: 1%;
  white-space: nowrap;
}

.note-label {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 0.875rem;
}
</style>
