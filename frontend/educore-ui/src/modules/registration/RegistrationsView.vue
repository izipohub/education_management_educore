<script setup lang="ts">
import Button from "primevue/button";
import Message from "primevue/message";
import SelectButton from "primevue/selectbutton";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref, watch } from "vue";
import { formatDate } from "@/core/format";
import DetailPane from "@/core/ui/DetailPane.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SplitView from "@/core/ui/SplitView.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Queue, type QueueRow, approveRegistration, getQueue, returnRegistration } from "./api";

const toast = useToast();
const status = ref<"Submitted" | "Returned" | "Approved">("Submitted");
const page = ref<Queue | null>(null);
const loading = ref(false);
const loadError = ref("");
const selected = ref<string | null>(null);
const busy = ref(false);

async function load() {
  loading.value = true;
  loadError.value = "";
  try {
    page.value = await getQueue(status.value);
    if (!page.value.rows.some((r) => r.name === selected.value)) selected.value = page.value.rows[0]?.name ?? null;
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(status, load);

const tabs = computed(() => (["Submitted", "Returned", "Approved"] as const).map((s) => ({ label: `${s} ${page.value?.counts[s] ?? 0}`, value: s })));
const items = computed(() => (page.value?.rows ?? []) as unknown as Record<string, unknown>[]);
const asRow = (item: Record<string, unknown>) => item as unknown as QueueRow;
const current = computed(() => page.value?.rows.find((r) => r.name === selected.value) ?? null);

const returning = ref(false);
const note = ref("");
watch(selected, () => {
  returning.value = false;
  note.value = "";
});

async function run(call: () => Promise<unknown>, message: string) {
  busy.value = true;
  try {
    await call();
    toast.add({ severity: "success", summary: message, life: 3000 });
    returning.value = false;
    await load();
  } catch (e) {
    toast.add({ severity: "error", summary: "Not done", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
const approve = (row: QueueRow) => run(() => approveRegistration(row.name), `${row.student_name}: approved`);
const sendBack = (row: QueueRow) => note.value.trim() && run(() => returnRegistration(row.name, note.value.trim()), `${row.student_name}: returned`);
</script>

<template>
  <PageHeader
    :title="page?.academic_year ? `Registrations ${page.academic_year}` : 'Registrations'"
    subtitle="Returning students in your faculty and campus. Approving registers the student and invoices the year."
  >
    <SelectButton v-model="status" :options="tabs" option-label="label" option-value="value" :allow-empty="false" aria-label="Status" />
  </PageHeader>

  <Message v-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

  <SplitView
    v-model:selected="selected"
    :items="items"
    item-key="name"
    :loading="loading"
    list-label="Registrations"
    :empty-title="`No ${status.toLowerCase()} registrations`"
    placeholder="Select a registration"
  >
    <template #item="{ item }">
      <div class="item">
        <div class="item-top">
          <span class="who">{{ asRow(item).student_name }}</span>
          <span class="ec-muted ec-nowrap">{{ asRow(item).offering }}</span>
        </div>
        <div class="item-bottom">
          <span class="ec-muted">Year {{ asRow(item).year_of_study }} · {{ asRow(item).credits }} credits</span>
          <span v-if="asRow(item).late" class="chip warn">Late</span>
          <StatusTag v-if="asRow(item).standing && asRow(item).standing !== 'Good standing'" kind="standing" :value="asRow(item).standing" />
        </div>
      </div>
    </template>

    <template #detail>
      <DetailPane
        v-if="current"
        :title="current.student_name"
        :subtitle="[current.student, current.submitted_on ? `submitted ${formatDate(current.submitted_on)}` : ''].filter(Boolean).join(' · ')"
      >
        <template #tags>
          <StatusTag kind="registration" :value="current.status" />
          <span v-if="current.late" class="chip warn">Late</span>
        </template>
        <template v-if="current.review_note" #notice>
          <div class="notice">Returned: {{ current.review_note }}</div>
        </template>

        <DetailSection title="Programme" :summary="current.program">
          <p class="ec-muted">{{ current.offering }} · {{ current.campus }} · year {{ current.year_of_study }}</p>
        </DetailSection>
        <DetailSection title="Standing">
          <template #summary><StatusTag kind="standing" :value="current.standing" /></template>
        </DetailSection>
        <DetailSection title="Courses" :summary="`${current.courses.length} courses, ${current.credits} credits`" collapsible open>
          <div v-for="c in current.courses" :key="c.course" class="line">
            <span class="grow">{{ c.course_name }}</span>
            <span class="ec-muted">{{ c.credits }} credits</span>
          </div>
        </DetailSection>
        <DetailSection v-if="returning" title="Return">
          <label for="note" class="label">What should the student change? They see this.</label>
          <Textarea id="note" v-model="note" rows="3" auto-resize fluid />
        </DetailSection>

        <template v-if="current.status === 'Submitted'" #actions>
          <template v-if="returning">
            <Button label="Cancel" text :disabled="busy" @click="returning = false" />
            <Button label="Return to student" severity="danger" :loading="busy" :disabled="!note.trim()" @click="sendBack(current)" />
          </template>
          <template v-else>
            <Button label="Return" severity="secondary" outlined :disabled="busy" @click="returning = true" />
            <Button label="Approve" :loading="busy" @click="approve(current)" />
          </template>
        </template>
      </DetailPane>
    </template>
  </SplitView>
</template>

<style scoped>
.item {
  display: grid;
  gap: 0.3rem;
}

.item-top,
.item-bottom {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.item-top {
  justify-content: space-between;
}

.who {
  font-weight: 600;
  font-size: 0.9rem;
}

.chip {
  padding: 0.1rem 0.45rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}

.chip.warn {
  background: #fef3c7;
  color: var(--ec-warn);
}

.notice {
  padding: 0.55rem 0.75rem;
  border-radius: var(--ec-radius-sm);
  background: #fffbeb;
  color: var(--ec-warn);
  font-size: 0.85rem;
}

.line {
  display: flex;
  gap: 0.5rem;
  padding: 0.35rem 0;
  border-top: 1px solid var(--ec-border-soft);
}

.line:first-child {
  border-top: 0;
}

.grow {
  flex: 1;
}

.label {
  display: block;
  margin-bottom: 0.35rem;
  font-size: 0.8125rem;
  color: var(--ec-muted);
}

p {
  margin: 0;
}
</style>
