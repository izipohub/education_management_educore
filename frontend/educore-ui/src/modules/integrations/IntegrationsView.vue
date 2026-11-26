<script setup lang="ts">
import InputNumber from "primevue/inputnumber";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import Select from "primevue/select";
import ToggleSwitch from "primevue/toggleswitch";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, reactive, ref } from "vue";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import SettingRow from "@/core/ui/SettingRow.vue";
import { type Integrations, getIntegrations, saveIntegrations, syncMoodleNow, testMoodle } from "./api";

/** Integrations, for ICT: connecting Moodle, so classes, students and lecturers are kept in it */
const toast = useToast();
const data = ref<Integrations | null>(null);
const error = ref("");
const saving = ref(false);
const form = reactive({ moodle_enabled: false, moodle_url: "", moodle_token: "", sign_in: "Moodle password", campus_categories: true, student_role_id: 5, teacher_role_id: 3 });

function take(d: Integrations) {
  data.value = d;
  Object.assign(form, {
    moodle_enabled: Boolean(d.moodle.moodle_enabled),
    moodle_url: d.moodle.moodle_url ?? "",
    moodle_token: "",
    sign_in: d.moodle.sign_in,
    campus_categories: Boolean(d.moodle.campus_categories),
    student_role_id: d.moodle.student_role_id,
    teacher_role_id: d.moodle.teacher_role_id,
  });
}
onMounted(async () => {
  try {
    take(await getIntegrations());
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

const changed = computed(() => {
  const m = data.value?.moodle;
  if (!m) return false;
  return (
    form.moodle_token !== "" ||
    form.moodle_enabled !== Boolean(m.moodle_enabled) ||
    form.moodle_url !== (m.moodle_url ?? "") ||
    form.sign_in !== m.sign_in ||
    form.campus_categories !== Boolean(m.campus_categories) ||
    form.student_role_id !== m.student_role_id ||
    form.teacher_role_id !== m.teacher_role_id
  );
});

async function save() {
  saving.value = true;
  try {
    take(
      await saveIntegrations({
        moodle_enabled: form.moodle_enabled ? 1 : 0,
        moodle_url: form.moodle_url.trim(),
        sign_in: form.sign_in,
        campus_categories: form.campus_categories ? 1 : 0,
        student_role_id: form.student_role_id,
        teacher_role_id: form.teacher_role_id,
        ...(form.moodle_token ? { moodle_token: form.moodle_token } : {}),
      }),
    );
    toast.add({ severity: "success", summary: "Saved", life: 2500 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not saved", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    saving.value = false;
  }
}

const testing = ref(false);
async function test() {
  testing.value = true;
  try {
    const r = await testMoodle(form.moodle_url.trim() || undefined, form.moodle_token || undefined);
    if (r.ok && r.missing?.length)
      toast.add({
        severity: "warn",
        summary: `Connected to ${r.site}, but the token's service lacks ${r.missing.length} functions`,
        detail: `Add them in Moodle (Site administration, Server, Web services, External services): ${r.missing.join(", ")}`,
        life: 15000,
      });
    else if (r.ok) toast.add({ severity: "success", summary: `Connected to ${r.site}`, detail: `Moodle ${r.release}, as ${r.user}`, life: 5000 });
    else toast.add({ severity: "error", summary: "Could not connect", detail: r.error, life: 8000 });
  } finally {
    testing.value = false;
  }
}

async function syncNow() {
  try {
    await syncMoodleNow();
    toast.add({ severity: "success", summary: "Syncing in the background", detail: "Refresh this page in a minute to see the result", life: 5000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not started", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  }
}
</script>

<template>
  <section class="integrations">
    <PageHeader title="Integrations" subtitle="The learning platforms kept in step with EduCore's classes" />

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-else-if="!data" class="card"><EcSkeleton shape="lines" :rows="6" label="Loading" /></div>

    <template v-else-if="data">
      <EcPanel title="Moodle" :note="data?.moodle.moodle_enabled ? 'Connected' : 'Not connected'">
        <SettingRow label="Keep classes in Moodle" help="Courses made, users created or found, enrolments kept in step, every hour" for="moodle-on">
          <ToggleSwitch v-model="form.moodle_enabled" input-id="moodle-on" />
        </SettingRow>
        <SettingRow label="Moodle address" for="moodle-url">
          <InputText id="moodle-url" v-model="form.moodle_url" placeholder="https://moodle.university.edu.na" fluid />
        </SettingRow>
        <SettingRow label="Web service token" :help="data?.moodle.has_token ? 'Saved; type a new one to replace it' : 'From Moodle: Site administration, Server, Web services, Manage tokens'" for="moodle-token">
          <Password v-model="form.moodle_token" input-id="moodle-token" :feedback="false" toggle-mask :placeholder="data?.moodle.has_token ? '••••••••' : ''" fluid />
        </SettingRow>
        <SettingRow label="Sign-in on Moodle" for="sign-in">
          <Select v-model="form.sign_in" input-id="sign-in" :options="data?.sign_in_options ?? []" fluid />
        </SettingRow>
        <SettingRow label="A course category per campus" for="campus-cat">
          <ToggleSwitch v-model="form.campus_categories" input-id="campus-cat" />
        </SettingRow>
        <SettingRow label="Moodle role IDs" help="Student and teacher, as in Moodle (5 and 3 by default)" for="role-student">
          <div class="roles">
            <InputNumber v-model="form.student_role_id" input-id="role-student" :min="1" aria-label="Student role ID" fluid />
            <InputNumber v-model="form.teacher_role_id" :min="1" aria-label="Teacher role ID" fluid />
          </div>
        </SettingRow>
        <template #footer>
          <EcButton label="Test connection" variant="ghost" :loading="testing" :disabled="!form.moodle_url" @click="test" />
          <EcButton v-if="changed" label="Save" variant="primary" :loading="saving" @click="save" />
        </template>
      </EcPanel>

      <EcPanel title="Classes in Moodle">
        <template #note>
          <EcButton v-if="data?.moodle.moodle_enabled" label="Sync now" size="sm" variant="ghost" @click="syncNow" />
        </template>
        <dl class="ec-facts">
          <div><dt>Classes</dt><dd>{{ data?.classes.total }}</dd></div>
          <div><dt>In Moodle</dt><dd>{{ data?.classes.in_moodle }}</dd></div>
          <div><dt>Last sync</dt><dd>{{ data?.moodle.last_sync_on ? formatDate(data?.moodle.last_sync_on) : "Never" }}</dd></div>
          <div v-if="data?.moodle.last_sync_result"><dt>Result</dt><dd>{{ data?.moodle.last_sync_result }}</dd></div>
        </dl>
        <table v-if="data?.classes.failed.length" class="ec-table failed">
          <thead><tr><th>Class</th><th>Moodle said</th></tr></thead>
          <tbody>
            <tr v-for="f in data?.classes.failed" :key="f.name"><td class="ec-nowrap">{{ f.name }}</td><td class="ec-muted">{{ f.error }}</td></tr>
          </tbody>
        </table>
      </EcPanel>
    </template>
  </section>
</template>

<style scoped>
.integrations {
  display: grid;
  gap: 1rem;
  max-width: 52rem;
}

.roles {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}

.failed {
  margin-top: 1rem;
}
</style>
