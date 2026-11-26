<script setup lang="ts">
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { onMounted, ref } from "vue";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type MyCase, appealCase, myCases } from "@/modules/records/discipline";

/** The student's disciplinary cases, from the hearing on: the charge and hearing, the decision, and their appeal */
const toast = useToast();
const cases = ref<MyCase[]>([]);
const appealing = ref<MyCase | null>(null);
const reason = ref("");
const busy = ref(false);

onMounted(async () => {
  cases.value = await myCases().catch(() => []);
});
async function send() {
  busy.value = true;
  try {
    cases.value = await appealCase(appealing.value!.name, reason.value.trim());
    appealing.value = null;
    toast.add({ severity: "success", summary: "Appeal sent", detail: "The Registrar decides it and you are emailed", life: 4000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not sent", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section v-if="cases.length" class="block discipline">
    <h2>Disciplinary {{ cases.length === 1 ? "case" : "cases" }}</h2>
    <article v-for="c in cases" :key="c.name" class="case">
      <div class="line">
        <strong>{{ c.status === "Hearing" ? "Hearing" : c.outcome }}</strong>
        <StatusTag kind="discipline" :value="c.status" />
      </div>
      <template v-if="c.status === 'Hearing'">
        <p class="sub">{{ formatDate(c.hearing_on) }} at {{ c.hearing_on?.slice(11, 16) }} · {{ c.hearing_venue }}</p>
        <p class="sub">Charge: {{ c.charge }}</p>
      </template>
      <template v-else>
        <p class="sub">{{ c.decision_note }}</p>
        <p v-if="c.fine_unpaid" class="sub">Fine of {{ formatMoney(c.fine) }} on your fee statement</p>
        <p v-if="c.appeal_reason" class="sub">Your appeal ({{ formatDate(c.appealed_on) }}): {{ c.appeal_reason }}</p>
        <p v-if="c.appeal_outcome" class="sub">Appeal {{ c.appeal_outcome.toLowerCase() }}: {{ c.appeal_note }}</p>
        <div v-if="c.can_appeal" class="appeal">
          <span class="sub">You may appeal until {{ formatDate(c.appeal_until) }}</span>
          <EcButton label="Appeal" size="sm" @click="(appealing = c), (reason = '')" />
        </div>
      </template>
    </article>
  </section>

  <EcModal :open="appealing !== null" title="Appeal the decision" description="To the Registrar, who decides it" @update:open="(v: boolean) => !v && (appealing = null)">
    <EcField label="Your grounds" for="appeal-reason" hint="Why the decision should change, and anything new">
      <Textarea id="appeal-reason" v-model="reason" rows="4" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="appealing = null" />
      <EcButton label="Send" variant="primary" :loading="busy" :disabled="!reason.trim()" @click="send" />
    </template>
  </EcModal>
</template>

<style scoped>
.discipline {
  margin-top: 1.5rem;
}

h2 {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6b7280;
}

.case {
  display: grid;
  gap: 0.3rem;
  padding: 0.8rem 1rem;
  border: 1px solid var(--ec-border-soft);
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface, #fff);
}

.line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.sub {
  margin: 0;
  color: #6b7280;
  font-size: 0.85rem;
}

.appeal {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.3rem;
}
</style>
