<script setup lang="ts">
import Button from "primevue/button";
import Drawer from "primevue/drawer";
import InputNumber from "primevue/inputnumber";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import { computed, ref, watch } from "vue";
import type { Programme, Setup } from "./api";

const props = defineProps<{ programme: Programme | null; setup: Setup; saving: boolean }>();
const emit = defineEmits<{ close: []; save: [string, Partial<Programme>] }>();

const form = ref<Programme | null>(null);
watch(
  () => props.programme,
  (p) => (form.value = p ? { ...p, subject_requirements: p.subject_requirements.map((r) => ({ ...r })) } : null),
  { immediate: true },
);

/** grades on the university's points scale, per school level */
const grades = computed(() => {
  const byLevel: Record<string, string[]> = {};
  for (const row of props.setup.points_scale) (byLevel[row.level] ??= []).push(row.grade);
  return byLevel;
});
const addRequirement = () => form.value?.subject_requirements.push({ subject: "", level: "NSSCO", grade: "" });

function save() {
  if (!form.value) return;
  const { name, level, min_points, subject_requirements, min_prior_nqf, min_prior_average } = form.value;
  emit("save", name, {
    level,
    min_points,
    subject_requirements: subject_requirements.filter((r) => r.subject && r.grade),
    min_prior_nqf,
    min_prior_average,
  });
}
</script>

<template>
  <Drawer
    :visible="programme !== null"
    position="right"
    :header="programme ? `${programme.name} (${programme.code})` : ''"
    :pt="{ root: { style: 'width: min(40rem, 100vw)' } }"
    @update:visible="(v: boolean) => !v && emit('close')"
  >
    <div v-if="form" class="form">
      <div class="field">
        <label>Level of study</label>
        <SelectButton v-model="form.level" :options="['Undergraduate', 'Postgraduate']" :allow-empty="false" aria-label="Level of study" />
      </div>

      <template v-if="form.level === 'Undergraduate'">
        <div class="field narrow">
          <label for="pg-points">Minimum points (school leavers)</label>
          <InputNumber v-model="form.min_points" input-id="pg-points" :min="0" fluid />
        </div>
        <div class="field">
          <label>Subject requirements</label>
          <small class="sub">A higher level or a better grade also meets a requirement.</small>
          <div v-for="(req, index) in form.subject_requirements" :key="index" class="req-row">
            <Select v-model="req.subject" :options="setup.choices.subjects" placeholder="Subject" filter :aria-label="`Subject ${index + 1}`" class="subject" />
            <Select v-model="req.level" :options="setup.choices.school_levels" :aria-label="`Level ${index + 1}`" @change="req.grade = ''" />
            <Select v-model="req.grade" :options="grades[req.level] ?? []" placeholder="Grade" :aria-label="`Minimum grade ${index + 1}`" />
            <Button label="✕" text severity="secondary" :aria-label="`Remove requirement ${index + 1}`" @click="form.subject_requirements.splice(index, 1)" />
          </div>
          <Button label="Add a subject" text class="add" @click="addRequirement" />
        </div>
      </template>

      <div class="grid">
        <div class="field">
          <label for="pg-nqf">Prior qualification: NQF level at least</label>
          <InputNumber v-model="form.min_prior_nqf" input-id="pg-nqf" :min="0" :max="10" fluid />
        </div>
        <div class="field">
          <label for="pg-avg">Prior qualification: average at least</label>
          <InputNumber v-model="form.min_prior_average" input-id="pg-avg" :min="0" :max="100" suffix="%" fluid />
        </div>
      </div>
      <small class="sub">Used for postgraduate applicants; empty: no minimum.</small>
    </div>
    <template #footer>
      <div class="footer">
        <Button label="Cancel" text @click="emit('close')" />
        <Button label="Save" :loading="saving" @click="save" />
      </div>
    </template>
  </Drawer>
</template>

<style scoped>
.form {
  display: grid;
  gap: 1rem;
}

.grid {
  display: grid;
  align-items: start;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.9rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

.narrow {
  max-width: 16rem;
}

label {
  font-size: 0.875rem;
}

.sub {
  font-size: 0.8rem;
  color: #6b7280;
}

.req-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
}

.subject {
  flex: 1 1 12rem;
}

.add {
  justify-self: start;
}

.footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
