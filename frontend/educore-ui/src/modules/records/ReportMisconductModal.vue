<script setup lang="ts">
import DatePicker from "primevue/datepicker";
import Select from "primevue/select";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { toIsoDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import { reportMisconduct } from "./discipline";

/**
 * Reporting a student's misconduct to Student Affairs: the student (fixed, or chosen from a class), the day, what
 * happened and any evidence. Confidential: the reporter is told it reached Student Affairs, nothing more.
 */
const props = defineProps<{ students: { student: string; student_name: string }[] }>();
const open = defineModel<boolean>("open", { required: true });
const toast = useToast();
const student = ref<string | null>(null);
const day = ref<Date>(new Date());
const incident = ref("");
const file = ref<File | null>(null);
const busy = ref(false);

watch(open, (v) => {
  if (!v) return;
  student.value = props.students.length === 1 ? props.students[0]!.student : null;
  day.value = new Date();
  incident.value = "";
  file.value = null;
});
const ready = computed(() => Boolean(student.value && day.value && incident.value.trim()));
async function send() {
  busy.value = true;
  try {
    const made = await reportMisconduct(student.value!, toIsoDate(day.value), incident.value.trim(), file.value);
    open.value = false;
    toast.add({ severity: "success", summary: "Reported to Student Affairs", detail: `${made.student_name}: Student Affairs looks into it`, life: 5000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not reported", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <EcModal v-model:open="open" title="Report misconduct" description="To Student Affairs, in confidence" size="md">
    <div class="form">
      <EcField v-if="students.length > 1" label="Student" for="report-student">
        <Select v-model="student" input-id="report-student" :options="students" option-label="student_name" option-value="student" filter placeholder="Choose" aria-label="Student" fluid />
      </EcField>
      <p v-else-if="students.length === 1" class="who">{{ students[0]!.student_name }} · {{ students[0]!.student }}</p>
      <EcField label="When it happened" for="report-day">
        <DatePicker v-model="day" input-id="report-day" date-format="dd-mm-yy" show-icon :max-date="new Date()" fluid />
      </EcField>
      <EcField label="What happened" for="report-incident" hint="What you saw or were told, where, and who else was there">
        <Textarea id="report-incident" v-model="incident" rows="4" auto-resize fluid />
      </EcField>
      <EcField label="Evidence (optional)" for="report-file" hint="PDF, JPG or PNG, up to 5 MB">
        <input id="report-file" type="file" accept=".pdf,.jpg,.jpeg,.png" @change="(e) => (file = (e.target as HTMLInputElement).files?.[0] ?? null)" />
      </EcField>
    </div>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" @click="open = false" />
      <EcButton label="Report" variant="primary" :loading="busy" :disabled="!ready" @click="send" />
    </template>
  </EcModal>
</template>

<style scoped>
.form {
  display: grid;
  gap: 0.75rem;
}

.who {
  margin: 0;
  font-weight: 600;
}
</style>
