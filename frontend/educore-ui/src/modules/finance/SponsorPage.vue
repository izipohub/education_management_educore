<script setup lang="ts">
import { FileText, Plus } from "@lucide/vue";
import AutoComplete from "primevue/autocomplete";
import Checkbox from "primevue/checkbox";
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { sponsorStatementUrl } from "@/core/documents";
import { formatDate, formatMoney } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import {
  type CoverType,
  type Sponsor,
  type SponsorDetails,
  type SponsoredStudent,
  addSponsoredStudent,
  findSponsorStudents,
  getSponsor,
  saveSponsor,
  withdrawSponsorship,
} from "./sponsors";

/** One sponsor: the students it pays for in a year, what it was invoiced and paid, how it pays; "new" makes one */
const props = defineProps<{ name: string }>();
const route = useRoute();
const router = useRouter();
const toast = useToast();
const TYPES = ["Government fund", "Bursary", "Scholarship", "Employer", "Other"];
const COVERS: CoverType[] = ["Full fees", "Percent of fees", "Amount"];

const sponsor = ref<Sponsor | null>(null);
const error = ref("");
const busy = ref(false);
const editing = ref(false);
const year = ref<string | undefined>((route.query.year as string) || undefined);
const isNew = computed(() => props.name === "new");

const blank = (): SponsorDetails => ({ sponsor_name: "", sponsor_type: "Government fund", contact_person: null, email: null, phone: null, address: null, payment_days: 60, disabled: 0 });
const form = ref<SponsorDetails>(blank());

async function load() {
  if (isNew.value) {
    sponsor.value = null;
    form.value = blank();
    editing.value = true;
    return;
  }
  try {
    sponsor.value = await getSponsor(props.name, year.value);
    if (!year.value && sponsor.value.academic_year) year.value = sponsor.value.academic_year;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch(
  () => props.name,
  () => {
    error.value = "";
    editing.value = false;
    void load();
  },
  { immediate: true },
);
watch(year, (value, before) => {
  if (before !== undefined && value !== sponsor.value?.academic_year) void load();
  void router.replace({ query: { ...route.query, ...(value ? { year: value } : {}) } });
});

const back = computed(() => ({ to: { name: "sponsors", query: { ...route.query } }, label: "Sponsors" }));
const title = computed(() => (isNew.value ? "New sponsor" : sponsor.value?.sponsor_name));
const subtitle = computed(() => (sponsor.value ? `${sponsor.value.name} · ${sponsor.value.sponsor_type}` : ""));
const outstanding = computed(() => {
  const waiting = sponsor.value?.totals.waiting ?? 0;
  return waiting ? [`${waiting} ${waiting === 1 ? "student" : "students"} to be invoiced once the registration is approved`] : [];
});

async function act(run: () => Promise<Sponsor>, done: string) {
  busy.value = true;
  try {
    sponsor.value = await run();
    toast.add({ severity: "success", summary: done, life: 2500 });
    return true;
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    return false;
  } finally {
    busy.value = false;
  }
}

// the sponsor's details
function edit() {
  const s = sponsor.value!;
  form.value = { sponsor_name: s.sponsor_name, sponsor_type: s.sponsor_type, contact_person: s.contact_person, email: s.email, phone: s.phone, address: s.address, payment_days: s.payment_days, disabled: s.disabled };
  editing.value = true;
}
async function save() {
  if (isNew.value) {
    busy.value = true;
    try {
      const made = await saveSponsor(form.value);
      toast.add({ severity: "success", summary: `${made.sponsor_name} added`, life: 2500 });
      await router.replace({ name: "sponsor", params: { name: made.name }, query: route.query });
    } catch (e) {
      toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
    } finally {
      busy.value = false;
    }
    return;
  }
  if (await act(() => saveSponsor(form.value, props.name), "Saved")) editing.value = false;
}
function cancel() {
  if (isNew.value) void router.push(back.value.to);
  else editing.value = false;
}

// a student the sponsor pays for
const adding = ref(false);
const student = ref<{ name: string; student_name: string; label: string } | null>(null);
const suggestions = ref<{ name: string; student_name: string; label: string }[]>([]);
const cover = ref<CoverType>("Full fees");
const coverValue = ref<number | null>(null);
const reference = ref("");
async function searchStudents(event: { query: string }) {
  const found = await findSponsorStudents(event.query).catch(() => []);
  suggestions.value = found.map((s) => ({ ...s, label: `${s.student_name} · ${s.name}` }));
}
function openAdd(named?: { student: string; student_name: string }) {
  student.value = named ? { name: named.student, student_name: named.student_name, label: `${named.student_name} · ${named.student}` } : null;
  cover.value = "Full fees";
  coverValue.value = null;
  reference.value = "";
  adding.value = true;
}
const canAdd = computed(() => !!student.value && typeof student.value === "object" && (cover.value === "Full fees" || (coverValue.value ?? 0) > 0));
async function add() {
  if (!sponsor.value || !year.value || !canAdd.value) return;
  const ok = await act(
    () =>
      addSponsoredStudent({
        sponsor_id: sponsor.value!.name,
        student: student.value!.name,
        academic_year: year.value!,
        cover_type: cover.value,
        cover_value: coverValue.value ?? undefined,
        sponsor_reference: reference.value || undefined,
      }),
    `${student.value!.student_name} added`,
  );
  if (ok) adding.value = false;
}

// withdrawing one
const withdrawing = ref<SponsoredStudent | null>(null);
async function withdraw() {
  if (!withdrawing.value) return;
  if (await act(() => withdrawSponsorship(withdrawing.value!.name), "Withdrawn")) withdrawing.value = null;
}
</script>

<template>
  <RecordPage :back="back" :title="title" :subtitle="subtitle" :error="error" :outstanding="outstanding">
    <template #tags>
      <span v-if="sponsor?.disabled" class="left">No longer sponsoring</span>
    </template>

    <template v-if="sponsor" #actions>
      <a v-if="year && sponsor.totals.invoiced" class="pdf" :href="sponsorStatementUrl(sponsor.name, year)" target="_blank" rel="noopener">
        <FileText :size="16" aria-hidden="true" /> Statement {{ year }}
      </a>
      <EcButton v-if="!sponsor.disabled" label="Add student" :icon="Plus" variant="primary" @click="openAdd()" />
      <Select v-model="year" :options="sponsor.academic_years" placeholder="Year" aria-label="Academic year" size="small" class="year" />
    </template>

    <EcPanel v-if="isNew || editing" :title="isNew ? 'Sponsor' : 'Edit sponsor'">
      <div class="form">
        <EcField label="Name" for="sponsor-name">
          <InputText id="sponsor-name" v-model="form.sponsor_name" fluid />
        </EcField>
        <EcField label="Type" for="sponsor-type">
          <Select v-model="form.sponsor_type" input-id="sponsor-type" :options="TYPES" fluid />
        </EcField>
        <EcField label="Contact person" for="sponsor-contact">
          <InputText id="sponsor-contact" v-model="form.contact_person" fluid />
        </EcField>
        <EcField label="Email" for="sponsor-email">
          <InputText id="sponsor-email" v-model="form.email" type="email" fluid />
        </EcField>
        <EcField label="Telephone" for="sponsor-phone">
          <InputText id="sponsor-phone" v-model="form.phone" fluid />
        </EcField>
        <EcField label="Pays within (days)" for="sponsor-days" hint="Due date of its invoices">
          <InputNumber v-model="form.payment_days" input-id="sponsor-days" :min="0" fluid />
        </EcField>
        <EcField label="Postal address" for="sponsor-address" class="wide">
          <Textarea id="sponsor-address" v-model="form.address" rows="3" auto-resize fluid />
        </EcField>
        <label v-if="!isNew" class="check wide">
          <Checkbox v-model="form.disabled" :true-value="1" :false-value="0" binary input-id="sponsor-disabled" />
          <span>No longer sponsoring</span>
        </label>
      </div>
      <template #footer>
        <EcButton label="Cancel" variant="ghost" size="sm" @click="cancel" />
        <EcButton :label="isNew ? 'Add sponsor' : 'Save'" variant="primary" size="sm" :loading="busy" :disabled="!form.sponsor_name.trim()" @click="save" />
      </template>
    </EcPanel>

    <template v-if="sponsor">
      <EcPanel :title="`Students ${sponsor.academic_year ?? ''}`" :note="sponsor.totals.students ? `${sponsor.totals.students} · ${formatMoney(sponsor.totals.invoiced)} invoiced` : undefined" :flush="sponsor.students.length > 0">
        <table v-if="sponsor.students.length" class="ec-table">
          <thead>
            <tr><th>Student</th><th>Cover</th><th class="num">Invoiced</th><th class="num">Owing</th><th>Status</th><th aria-hidden="true"></th></tr>
          </thead>
          <tbody>
            <tr v-for="s in sponsor.students" :key="s.name">
              <td>
                {{ s.student_name }}
                <div class="ec-muted">{{ [s.student, s.program, s.campus?.replace(" Campus", "")].filter(Boolean).join(" · ") }}</div>
              </td>
              <td>
                {{ s.cover }}
                <div v-if="s.sponsor_reference" class="ec-muted ec-nowrap">{{ s.sponsor_reference }}</div>
              </td>
              <td class="num ec-nowrap">{{ s.amount ? formatMoney(s.amount) : "" }}</td>
              <td class="num ec-nowrap">{{ s.status === "Invoiced" ? formatMoney(s.owing) : "" }}</td>
              <td><StatusTag kind="sponsorship" :value="s.status" /></td>
              <td class="num">
                <EcButton v-if="s.can_withdraw" label="Withdraw" size="sm" variant="quiet-danger" @click="withdrawing = s" />
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No students for {{ sponsor.academic_year }}</p>
      </EcPanel>

      <EcPanel v-if="sponsor.named.length" title="Named on their application" :note="`${sponsor.named.length} without a sponsorship for ${sponsor.academic_year}`" flush>
        <table class="ec-table">
          <tbody>
            <tr v-for="n in sponsor.named" :key="n.student">
              <td>
                {{ n.student_name }}
                <div class="ec-muted">{{ [n.student, n.program, n.campus?.replace(" Campus", "")].filter(Boolean).join(" · ") }}</div>
              </td>
              <td class="num"><EcButton v-if="!sponsor.disabled" label="Add" size="sm" variant="ghost" @click="openAdd(n)" /></td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel title="Payments" :flush="sponsor.payments.length > 0">
        <table v-if="sponsor.payments.length" class="ec-table">
          <thead>
            <tr><th>Date</th><th>Bank reference</th><th class="num">Amount</th><th class="num">In advance</th></tr>
          </thead>
          <tbody>
            <tr v-for="p in sponsor.payments" :key="p.name">
              <td class="ec-nowrap">{{ formatDate(p.posting_date) }}</td>
              <td>{{ p.reference_no }}</td>
              <td class="num ec-nowrap">{{ formatMoney(p.paid_amount) }}</td>
              <td class="num ec-nowrap">{{ p.unallocated_amount ? formatMoney(p.unallocated_amount) : "" }}</td>
            </tr>
          </tbody>
        </table>
        <p v-else class="none ec-muted">No payments yet</p>
      </EcPanel>
    </template>

    <template v-if="sponsor" #aside>
      <EcPanel title="Account">
        <dl class="ec-facts stacked">
          <div><dt>Owing</dt><dd>{{ formatMoney(sponsor.totals.owing) }}</dd></div>
          <div v-if="sponsor.totals.owing_year !== sponsor.totals.owing"><dt>Owing for {{ sponsor.academic_year }}</dt><dd>{{ formatMoney(sponsor.totals.owing_year) }}</dd></div>
          <div><dt>Pays by EFT with the reference</dt><dd class="reference">{{ sponsor.name }}</dd></div>
          <div><dt>Pays within</dt><dd>{{ sponsor.payment_days }} days</dd></div>
        </dl>
      </EcPanel>

      <EcPanel title="Contact">
        <dl class="ec-facts stacked">
          <div><dt>Contact person</dt><dd>{{ sponsor.contact_person || "Not recorded" }}</dd></div>
          <div v-if="sponsor.email"><dt>Email</dt><dd>{{ sponsor.email }}</dd></div>
          <div v-if="sponsor.phone"><dt>Telephone</dt><dd>{{ sponsor.phone }}</dd></div>
          <div v-if="sponsor.address"><dt>Postal address</dt><dd class="address">{{ sponsor.address }}</dd></div>
        </dl>
        <template v-if="!editing" #footer>
          <EcButton label="Edit" variant="ghost" size="sm" @click="edit" />
        </template>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal :open="adding" :title="`Add a student for ${year ?? ''}`" :description="sponsor?.sponsor_name" size="md" @update:open="(v: boolean) => (adding = v)">
    <div class="modal-form">
      <EcField label="Student" for="sponsored-student" hint="Name, student number or ID number">
        <AutoComplete v-model="student" input-id="sponsored-student" :suggestions="suggestions" option-label="label" fluid @complete="searchStudents" />
      </EcField>
      <EcField label="Pays" for="sponsored-cover">
        <Select v-model="cover" input-id="sponsored-cover" :options="COVERS" fluid />
      </EcField>
      <EcField v-if="cover !== 'Full fees'" :label="cover === 'Amount' ? 'Amount (N$)' : 'Percent of the fees'" for="sponsored-value">
        <InputNumber v-model="coverValue" input-id="sponsored-value" :min="0" :max="cover === 'Amount' ? undefined : 100" :max-fraction-digits="2" fluid />
      </EcField>
      <EcField label="Sponsor's reference" for="sponsored-reference" hint="Its bursary, loan or award number">
        <InputText id="sponsored-reference" v-model="reference" fluid />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="adding = false" />
      <EcButton label="Add student" variant="primary" :loading="busy" :disabled="!canAdd" @click="add" />
    </template>
  </EcModal>

  <EcModal
    :open="withdrawing !== null"
    title="Withdraw sponsorship"
    :description="withdrawing ? `${withdrawing.student_name} pays the ${sponsor?.academic_year} fees again; the invoice to the sponsor is cancelled.` : undefined"
    @update:open="(v: boolean) => !v && (withdrawing = null)"
  >
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="withdrawing = null" />
      <EcButton label="Withdraw" variant="danger" :loading="busy" @click="withdraw" />
    </template>
  </EcModal>
</template>

<style scoped>
.none {
  margin: 0;
}

.left {
  color: var(--ec-muted);
  font-size: 0.8125rem;
}

.year {
  width: 7.5rem;
}

.form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem 1rem;
}

.form .wide {
  grid-column: 1 / -1;
}

@media (max-width: 640px) {
  .form {
    grid-template-columns: 1fr;
  }
}

.modal-form {
  display: grid;
  gap: 0.75rem;
}

.check {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.reference {
  font-family: ui-monospace, monospace;
  font-weight: 600;
}

.address {
  white-space: pre-line;
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
</style>
