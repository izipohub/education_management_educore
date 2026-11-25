<script setup lang="ts">
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import { type Hold, type StudentClearance, getClearance, liftHold, placeHold } from "./clearance";

/** One student's financial clearance: what stops it, their invoices and sponsors, the holds placed and lifted */
const props = defineProps<{ name: string }>();
const route = useRoute();
const toast = useToast();
const data = ref<StudentClearance | null>(null);
const error = ref("");
const busy = ref(false);

watch(
  () => props.name,
  async () => {
    data.value = null;
    error.value = "";
    try {
      data.value = await getClearance(props.name);
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e);
    }
  },
  { immediate: true },
);

const back = computed(() => ({ to: { name: "clearance", query: route.query }, label: "Financial clearance" }));
const subtitle = computed(() => (data.value ? [data.value.name, data.value.campus].filter(Boolean).join(" · ") : ""));

async function act(run: () => Promise<StudentClearance>, done: string) {
  busy.value = true;
  try {
    data.value = await run();
    toast.add({ severity: "success", summary: done, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

const placing = ref(false);
const reason = ref("");
async function place() {
  if (await act(() => placeHold(props.name, reason.value), "Hold placed")) placing.value = false;
}
const lifting = ref<Hold | null>(null);
const note = ref("");
async function lift() {
  if (lifting.value && (await act(() => liftHold(lifting.value!.name, note.value), "Hold lifted"))) lifting.value = null;
}
</script>

<template>
  <RecordPage :back="back" :title="data?.student_name" :subtitle="subtitle" :error="error" :outstanding="data?.reasons ?? []">
    <template #tags>
      <span v-if="data" class="state">{{ data.cleared ? "Cleared" : "Not cleared" }}</span>
    </template>
    <template v-if="data" #actions>
      <EcButton label="Place a hold" @click="(placing = true), (reason = '')" />
    </template>

    <template v-if="data">
      <EcPanel title="Holds" :flush="data.history.length > 0">
        <table v-if="data.history.length" class="ec-table">
          <tbody>
            <tr v-for="h in data.history" :key="h.name">
              <td>
                {{ h.reason }}
                <div class="ec-muted">
                  Placed {{ formatDate(h.placed_on) }} by {{ h.placed_by }}<template v-if="h.status === 'Lifted'"> · lifted {{ formatDate(h.lifted_on) }}: {{ h.lift_note }}</template>
                </div>
              </td>
              <td class="num">
                <EcButton v-if="h.status === 'Active'" label="Lift" size="sm" variant="ghost" @click="(lifting = h), (note = '')" />
                <span v-else class="ec-muted">Lifted</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No holds</p>
      </EcPanel>

      <EcPanel title="Invoices" :note="data.owing ? `${formatMoney(data.owing)} owing` : 'Nothing owing'" :flush="data.invoices.length > 0">
        <table v-if="data.invoices.length" class="ec-table">
          <thead>
            <tr><th>Invoice</th><th>Date</th><th class="num">Amount</th><th class="num">Owing</th></tr>
          </thead>
          <tbody>
            <tr v-for="i in data.invoices" :key="i.name">
              <td>
                {{ i.name }}
                <div v-if="i.is_return && i.remarks" class="ec-muted">{{ i.remarks }}</div>
              </td>
              <td class="ec-nowrap">{{ formatDate(i.posting_date) }}</td>
              <td class="num ec-nowrap">{{ formatMoney(i.grand_total) }}</td>
              <td class="num ec-nowrap">{{ i.outstanding_amount > 0 ? formatMoney(i.outstanding_amount) : "" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No invoices</p>
      </EcPanel>
    </template>

    <template v-if="data" #aside>
      <EcPanel title="Sponsors">
        <dl v-if="data.sponsors.length" class="ec-facts stacked">
          <div v-for="s in data.sponsors" :key="`${s.sponsor_name}-${s.academic_year}`"><dt>{{ s.academic_year }}</dt><dd>{{ s.sponsor_name }}<template v-if="s.amount"> · {{ formatMoney(s.amount) }}</template></dd></div>
        </dl>
        <p v-else class="none ec-muted">None</p>
      </EcPanel>
      <EcPanel title="Contact">
        <p class="none">{{ data.student_email_id || "No email recorded" }}</p>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal :open="placing" title="Place a hold" :description="`${data?.student_name ?? ''}: blocks registration and clearance until lifted`" @update:open="(v: boolean) => (placing = v)">
    <EcField label="Reason" for="hold-reason" hint="Shown to the student and the registry">
      <Textarea id="hold-reason" v-model="reason" rows="3" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="placing = false" />
      <EcButton label="Place hold" variant="primary" :loading="busy" :disabled="!reason.trim()" @click="place" />
    </template>
  </EcModal>

  <EcModal :open="lifting !== null" title="Lift the hold" :description="lifting?.reason" @update:open="(v: boolean) => !v && (lifting = null)">
    <EcField label="Why it is lifted" for="lift-note">
      <Textarea id="lift-note" v-model="note" rows="2" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="lifting = null" />
      <EcButton label="Lift hold" variant="primary" :loading="busy" :disabled="!note.trim()" @click="lift" />
    </template>
  </EcModal>
</template>

<style scoped>
.none {
  margin: 0;
}

.state {
  color: var(--ec-muted);
  font-size: 0.8125rem;
}
</style>
