<script setup lang="ts">
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type ServiceCategory, type ServiceRequest, askService, myServiceRequests } from "@/modules/records/serviceRequests";

/** The student's service requests: what they asked for, where it stands, and asking for something new */
const toast = useToast();
const router = useRouter();
const categories = ref<ServiceCategory[]>([]);
const requests = ref<ServiceRequest[]>([]);
const open = ref(false);
const category = ref<string | null>(null);
const details = ref("");
const file = ref<File | null>(null);
const busy = ref(false);

onMounted(async () => {
  const page = await myServiceRequests().catch(() => null);
  if (page) {
    categories.value = page.categories;
    requests.value = page.requests;
  }
});
const chosen = computed(() => categories.value.find((c) => c.name === category.value) ?? null);
const ready = computed(() => Boolean(chosen.value && details.value.trim() && (!chosen.value.needs_attachment || file.value)));
function start() {
  category.value = null;
  details.value = "";
  file.value = null;
  open.value = true;
}
async function send() {
  busy.value = true;
  try {
    const made = await askService(category.value!, details.value.trim(), file.value);
    open.value = false;
    toast.add({ severity: "success", summary: "Request sent", detail: `${made.office} answers by ${formatDate(made.due_on)}`, life: 4000 });
    await router.push({ name: "my-service-request", params: { name: made.name } });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not sent", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
const line = (r: ServiceRequest) =>
  r.status === "Submitted" || r.status === "In progress"
    ? `${r.office} · answer by ${formatDate(r.due_on)}${r.fee_unpaid ? ` · fee ${formatMoney(r.fee)} to pay` : ""}`
    : [r.office, r.outcome_note].filter(Boolean).join(" · ");
</script>

<template>
  <section v-if="categories.length || requests.length" class="block services">
    <div class="head">
      <h2>Service requests</h2>
      <EcButton v-if="categories.length" label="Ask for a service" size="sm" @click="start" />
    </div>
    <ul v-if="requests.length" class="history">
      <li v-for="r in requests" :key="r.name">
        <RouterLink :to="{ name: 'my-service-request', params: { name: r.name } }" class="row">
          <span class="line">
            <span>{{ r.category }}</span>
            <StatusTag kind="service" :value="r.status" />
          </span>
          <span class="sub">{{ line(r) }}</span>
        </RouterLink>
      </li>
    </ul>
    <p v-else class="sub">A letter, a card replacement, a change of name: ask the office here and follow its answer.</p>
  </section>

  <EcModal :open="open" title="Ask for a service" size="md" @update:open="(v: boolean) => (open = v)">
    <div class="form">
      <EcField label="What you need" for="service-category">
        <Select v-model="category" input-id="service-category" :options="categories" option-label="name" option-value="name" placeholder="Choose" aria-label="What you need" fluid />
      </EcField>
      <p v-if="chosen" class="sub">
        {{ chosen.office }} answers within {{ chosen.response_days }} working days<template v-if="chosen.fee"> · fee {{ formatMoney(chosen.fee) }}, invoiced to your fee account</template>.
      </p>
      <EcField label="Details" for="service-details" :hint="chosen?.guidance ?? undefined">
        <Textarea id="service-details" v-model="details" rows="4" auto-resize fluid />
      </EcField>
      <EcField :label="chosen?.needs_attachment ? 'Document (required)' : 'Document (optional)'" for="service-file" hint="PDF, JPG or PNG, up to 5 MB">
        <input id="service-file" type="file" accept=".pdf,.jpg,.jpeg,.png" @change="(e) => (file = (e.target as HTMLInputElement).files?.[0] ?? null)" />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="open = false" />
      <EcButton label="Send" variant="primary" :loading="busy" :disabled="!ready" @click="send" />
    </template>
  </EcModal>
</template>

<style scoped>
.services {
  margin-bottom: 1.5rem;
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

h2 {
  margin: 0;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6b7280;
}

.history {
  display: grid;
  gap: 0.5rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.row {
  display: grid;
  gap: 0.15rem;
  padding: 0.7rem 0.9rem;
  border: 1px solid var(--ec-border-soft);
  border-radius: var(--ec-radius-sm);
  background: var(--ec-surface, #fff);
  color: inherit;
  text-decoration: none;
}

.row:hover {
  border-color: var(--ec-border);
}

.line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  font-weight: 600;
}

.sub {
  margin: 0;
  color: #6b7280;
  font-size: 0.85rem;
}

.form {
  display: grid;
  gap: 0.75rem;
}
</style>
