<script setup lang="ts">
import { semesterLabel } from "@/modules/curriculum/api";
import Textarea from "primevue/textarea";
import { useToast } from "primevue/usetoast";
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import EcModal from "@/core/ui/EcModal.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import RecordPage from "@/core/ui/RecordPage.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type QueueRow, approveRegistration, getRegistration, returnRegistration } from "./api";

/** One returning student's registration on its own page: courses, standing, and the decision */
const props = defineProps<{ name: string }>();
const route = useRoute();
const toast = useToast();

const reg = ref<QueueRow | null>(null);
const error = ref("");
const busy = ref(false);

async function load() {
  error.value = "";
  try {
    reg.value = await getRegistration(props.name);
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}
watch(
  () => props.name,
  () => {
    reg.value = null;
    void load();
  },
  { immediate: true },
);

const back = computed(() => ({ to: { name: "registrations", query: { ...route.query, group: "senior" } }, label: "Registration · senior students" }));

const returning = ref(false);
const note = ref("");
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
const approve = () => reg.value && run(() => approveRegistration(reg.value!.name), `${reg.value.student_name}: approved`);
const sendBack = () =>
  reg.value && note.value.trim() && run(() => returnRegistration(reg.value!.name, note.value.trim()), `${reg.value.student_name}: returned`);
</script>

<template>
  <RecordPage
    :back="back"
    :title="reg?.student_name"
    :subtitle="reg ? [reg.student, reg.program].join(' · ') : ''"
    :error="error"
  >
    <template #tags><StatusTag v-if="reg" kind="registration" :value="reg.status" /></template>

    <template v-if="reg?.status === 'Submitted'" #actions>
      <EcButton label="Return" :disabled="busy" @click="(returning = true), (note = '')" />
      <EcButton label="Approve" variant="primary" :loading="busy" @click="approve" />
    </template>

    <template v-if="reg">
      <EcPanel title="Courses" :note="`${reg.courses.length} courses · ${reg.credits} credits`" flush>
        <table class="ec-table">
          <thead>
            <tr><th>Runs in</th><th>Course</th><th class="num">Credits</th></tr>
          </thead>
          <tbody>
            <tr v-for="c in reg.courses" :key="c.course">
              <td class="ec-nowrap ec-muted">{{ semesterLabel(c.semester) }}</td>
              <td>{{ c.course_name }}</td>
              <td class="num">{{ c.credits }}</td>
            </tr>
          </tbody>
        </table>
      </EcPanel>

      <EcPanel v-if="reg.review_note" title="Returned with a note">
        <p class="note">{{ reg.review_note }}</p>
      </EcPanel>
    </template>

    <template v-if="reg" #aside>
      <EcPanel title="Summary">
        <dl class="ec-facts stacked">
          <div><dt>Standing</dt><dd><StatusTag kind="standing" :value="reg.standing" /></dd></div>
          <div><dt>Programme</dt><dd>{{ reg.program }}</dd></div>
          <div><dt>Offering</dt><dd>{{ reg.offering }}</dd></div>
          <div><dt>Campus</dt><dd>{{ reg.campus }}</dd></div>
          <div><dt>Year of study</dt><dd>{{ reg.year_of_study }}</dd></div>
          <div><dt>Academic year</dt><dd>{{ reg.academic_year }}</dd></div>
          <div v-if="reg.submitted_on"><dt>Submitted</dt><dd>{{ formatDate(reg.submitted_on) }}<template v-if="reg.late"> · late</template></dd></div>
        </dl>
      </EcPanel>
    </template>
  </RecordPage>

  <EcModal :open="returning" :title="`Return to ${reg?.student_name ?? 'the student'}`" @update:open="(v: boolean) => (returning = v)">
    <EcField label="What should the student change?" for="note" hint="The student sees this">
      <Textarea id="note" v-model="note" rows="3" auto-resize fluid />
    </EcField>
    <template #footer>
      <EcButton label="Cancel" variant="ghost" :disabled="busy" @click="returning = false" />
      <EcButton label="Return to student" variant="danger" :loading="busy" :disabled="!note.trim()" @click="sendBack" />
    </template>
  </EcModal>
</template>

<style scoped>
.note {
  margin: 0;
}
</style>
