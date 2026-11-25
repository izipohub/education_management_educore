<script setup lang="ts">
import DatePicker from "primevue/datepicker";
import Select from "primevue/select";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { formatMoney, fromIsoDate, toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import SettingRow from "@/core/ui/SettingRow.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Period, type RegistrationSetup, getRegistrationSetup, savePeriod } from "./registrationSetup";

/** One academic year's registration period, on its own page ("new" to add one); Save returns to the list */
const props = defineProps<{ name: string }>();
const router = useRouter();
const toast = useToast();
const setup = ref<RegistrationSetup | null>(null);
const error = ref("");
const saving = ref(false);
const isNew = computed(() => props.name === "new");
const existing = computed<Period | null>(() => setup.value?.periods.find((p) => p.name === props.name) ?? null);
const form = reactive({ academic_year: "", opens_on: null as Date | null, closes_on: null as Date | null, late_until: null as Date | null, changes_until: null as Date | null, late_fee: 0 });

onMounted(async () => {
  try {
    setup.value = await getRegistrationSetup();
    const p = existing.value;
    if (p) {
      Object.assign(form, {
        academic_year: p.academic_year,
        opens_on: p.opens_on ? fromIsoDate(p.opens_on) : null,
        closes_on: p.closes_on ? fromIsoDate(p.closes_on) : null,
        late_until: p.late_until ? fromIsoDate(p.late_until) : null,
        changes_until: p.changes_until ? fromIsoDate(p.changes_until) : null,
        late_fee: p.late_fee,
      });
    } else if (!isNew.value) {
      error.value = `${props.name} has no registration period`;
    } else {
      form.academic_year = setup.value.academic_years[0] ?? "";
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

const back = { to: { name: "registration-setup" }, label: "Registration setup" };
const ready = computed(() => Boolean(form.academic_year && form.opens_on && form.closes_on));
async function save() {
  saving.value = true;
  try {
    await savePeriod(
      {
        academic_year: form.academic_year,
        opens_on: form.opens_on ? toIsoDate(form.opens_on) : null,
        closes_on: form.closes_on ? toIsoDate(form.closes_on) : null,
        late_until: form.late_until ? toIsoDate(form.late_until) : null,
        changes_until: form.changes_until ? toIsoDate(form.changes_until) : null,
      },
      isNew.value ? undefined : props.name,
    );
    toast.add({ severity: "success", summary: "Registration period saved", life: 2500 });
    await router.push(back.to);
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <RecordPage
    :back="back"
    :title="isNew ? 'New registration period' : `Registration ${existing?.academic_year ?? ''}`"
    :subtitle="existing ? `${existing.registrations} ${existing.registrations === 1 ? 'registration' : 'registrations'}` : undefined"
    :error="error"
    :loading="!setup"
  >
    <template v-if="existing" #tags><StatusTag kind="period" :value="existing.state" /></template>
    <template #actions>
      <EcButton label="Cancel" variant="ghost" @click="router.push(back.to)" />
      <EcButton label="Save" variant="primary" :loading="saving" :disabled="!ready" @click="save" />
    </template>

    <EcPanel title="Dates">
      <SettingRow v-if="isNew" label="Academic year" for="year">
        <Select v-model="form.academic_year" input-id="year" :options="setup?.academic_years ?? []" fluid />
      </SettingRow>
      <SettingRow label="Opens" for="opens">
        <DatePicker v-model="form.opens_on" input-id="opens" date-format="dd-mm-yy" show-icon fluid />
      </SettingRow>
      <SettingRow label="Closes" for="closes">
        <DatePicker v-model="form.closes_on" input-id="closes" date-format="dd-mm-yy" show-icon fluid :min-date="form.opens_on ?? undefined" />
      </SettingRow>
      <SettingRow label="Late registration until" help="Empty for no late registration" for="late">
        <DatePicker v-model="form.late_until" input-id="late" date-format="dd-mm-yy" show-icon show-button-bar fluid :min-date="form.closes_on ?? undefined" />
      </SettingRow>
      <SettingRow v-if="form.late_until && !isNew" label="Late registration fee" help="Set by Finance">
        <span class="value">{{ formatMoney(form.late_fee) }}</span>
      </SettingRow>
      <SettingRow label="Course changes until" help="Adding and dropping courses after approval; empty for none" for="changes">
        <DatePicker v-model="form.changes_until" input-id="changes" date-format="dd-mm-yy" show-icon show-button-bar fluid :min-date="form.closes_on ?? undefined" />
      </SettingRow>
    </EcPanel>
  </RecordPage>
</template>

<style scoped>
.value {
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
