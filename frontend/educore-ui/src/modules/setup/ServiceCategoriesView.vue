<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import ToggleSwitch from "primevue/toggleswitch";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, reactive, ref } from "vue";
import { formatMoney } from "@/core/format";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type ServiceCategory, saveServiceCategory, serviceCategories } from "@/modules/records/serviceRequests";

/**
 * The services students may ask for, kept by the Registrar: the office that handles each, how many working days it has
 * to respond, any fee (invoiced when the student asks), whether a document is needed, and what to include. A category
 * keeps its name once made; one no longer offered is marked not in use.
 */
const toast = useToast();
const rows = ref<ServiceCategory[]>([]);
const offices = ref<string[]>([]);
const canEdit = ref(false);
const loading = ref(false);
const error = ref("");

function take(page: { rows: ServiceCategory[]; offices: string[]; can_edit: boolean }) {
  rows.value = page.rows;
  offices.value = page.offices;
  canEdit.value = page.can_edit;
}
onMounted(async () => {
  loading.value = true;
  try {
    take(await serviceCategories());
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
});

const columns: Column[] = [
  { key: "name", label: "Category" },
  { key: "office", label: "Handled by" },
  { key: "response_days", label: "Working days", align: "right", wide: true },
  { key: "fee", label: "Fee", align: "right" },
  { key: "disabled", label: "In use" },
];
const row = (r: Record<string, unknown>) => r as unknown as ServiceCategory;

// adding or changing one
const editing = ref(false);
const isNew = ref(false);
const form = reactive({ name: "", office: "Registry", response_days: 3, fee: 0, needs_attachment: false, guidance: "", disabled: false });
function edit(c?: ServiceCategory) {
  if (!canEdit.value) return;
  isNew.value = !c;
  Object.assign(form, {
    name: c?.name ?? "",
    office: c?.office ?? "Registry",
    response_days: c?.response_days ?? 3,
    fee: c?.fee ?? 0,
    needs_attachment: Boolean(c?.needs_attachment),
    guidance: c?.guidance ?? "",
    disabled: Boolean(c?.disabled),
  });
  editing.value = true;
}
const ready = computed(() => Boolean(form.name.trim() && form.office));
const saving = ref(false);
async function save() {
  saving.value = true;
  try {
    take(
      await saveServiceCategory({
        ...(isNew.value ? { category_name: form.name.trim() } : { name: form.name }),
        office: form.office,
        response_days: form.response_days,
        fee: form.fee,
        needs_attachment: form.needs_attachment ? 1 : 0,
        guidance: form.guidance,
        disabled: form.disabled ? 1 : 0,
      }),
    );
    editing.value = false;
    toast.add({ severity: "success", summary: "Saved", life: 2000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <section class="list-page">
    <PageHeader title="Service request categories" subtitle="What students may ask the offices for, who handles it and how soon">
      <template v-if="canEdit" #actions>
        <EcButton label="Add a category" variant="primary" @click="edit()" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable :columns="columns" :rows="rows as unknown as Record<string, unknown>[]" row-key="name" :to="() => null" :loading="loading" noun="categories" empty-title="No categories yet">
      <template #cell-name="{ row: r }">
        <button v-if="canEdit" type="button" class="link" @click="edit(row(r))">{{ row(r).name }}</button>
        <template v-else>{{ row(r).name }}</template>
        <span v-if="row(r).needs_attachment" class="sub">Document required</span>
      </template>
      <template #cell-fee="{ row: r }">{{ row(r).fee ? formatMoney(row(r).fee) : "Free" }}</template>
      <template #cell-disabled="{ row: r }">{{ row(r).disabled ? "No" : "Yes" }}</template>
    </DataTable>
  </section>

  <EcModal :open="editing" :title="isNew ? 'Add a category' : form.name" size="md" @update:open="(v: boolean) => (editing = v)">
    <div class="form">
      <EcField v-if="isNew" label="Category" for="cat-name" hint="As students see it, e.g. Letter of enrolment">
        <InputText id="cat-name" v-model="form.name" fluid />
      </EcField>
      <div class="pair">
        <EcField label="Handled by" for="cat-office">
          <Select v-model="form.office" input-id="cat-office" :options="offices" fluid />
        </EcField>
        <EcField label="Working days to respond" for="cat-days">
          <InputNumber v-model="form.response_days" input-id="cat-days" :min="0" :max="60" show-buttons fluid />
        </EcField>
      </div>
      <EcField label="Fee" for="cat-fee" hint="Invoiced to the student when they ask. 0: free">
        <InputNumber v-model="form.fee" input-id="cat-fee" :min="0" prefix="N$ " :min-fraction-digits="2" :max-fraction-digits="2" fluid />
      </EcField>
      <EcField label="What to include" for="cat-guidance" hint="Shown to the student when they ask">
        <Textarea id="cat-guidance" v-model="form.guidance" rows="2" auto-resize fluid />
      </EcField>
      <label class="toggle"><ToggleSwitch v-model="form.needs_attachment" /> A document is required</label>
      <label v-if="!isNew" class="toggle"><ToggleSwitch :model-value="!form.disabled" @update:model-value="(v: boolean) => (form.disabled = !v)" /> In use</label>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="editing = false" />
      <EcButton label="Save" variant="primary" :loading="saving" :disabled="!ready" @click="save" />
    </template>
  </EcModal>
</template>

<style scoped>
.list-page {
  display: grid;
  gap: 1rem;
}

.form {
  display: grid;
  gap: 0.75rem;
}

.pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.toggle {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.9rem;
}

.link {
  padding: 0;
  border: 0;
  background: none;
  color: var(--ec-accent);
  font: inherit;
  font-weight: 600;
  cursor: pointer;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
}
</style>
