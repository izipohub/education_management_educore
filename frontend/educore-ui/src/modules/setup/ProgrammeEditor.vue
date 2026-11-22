<script setup lang="ts">
import { Plus, X } from "@lucide/vue";
import InputNumber from "primevue/inputnumber";
import Select from "primevue/select";
import SelectButton from "primevue/selectbutton";
import { computed, ref, watch } from "vue";
import DetailPane from "@/core/ui/DetailPane.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import EcButton from "@/core/ui/EcButton.vue";
import EcField from "@/core/ui/EcField.vue";
import type { Programme, Setup } from "./api";

/** A programme's level and entry requirements, docked beside the list */
const props = defineProps<{ programme: Programme; setup: Setup; saving: boolean }>();
const emit = defineEmits<{ save: [string, Partial<Programme>] }>();

const form = ref<Programme>({ ...props.programme });
const reset = () => (form.value = { ...props.programme, subject_requirements: props.programme.subject_requirements.map((r) => ({ ...r })) });
watch(() => props.programme, reset, { immediate: true });

/** grades on the university's points scale, per school level */
const grades = computed(() => {
  const byLevel: Record<string, string[]> = {};
  for (const row of props.setup.points_scale) (byLevel[row.level] ??= []).push(row.grade);
  return byLevel;
});
const addRequirement = () => form.value.subject_requirements.push({ subject: "", level: "NSSCO", grade: "" });

function save() {
  const { name, level, min_points, subject_requirements, min_prior_nqf, min_prior_average } = form.value;
  emit("save", name, { level, min_points, subject_requirements: subject_requirements.filter((r) => r.subject && r.grade), min_prior_nqf, min_prior_average });
}
</script>

<template>
  <DetailPane :title="programme.name" :subtitle="[programme.code, programme.qualification, programme.nqf_level ? `NQF ${programme.nqf_level}` : ''].filter(Boolean).join(' · ')">
    <DetailSection title="Level">
      <SelectButton v-model="form.level" :options="['Undergraduate', 'Postgraduate']" :allow-empty="false" aria-label="Level of study" size="small" />
    </DetailSection>

    <DetailSection v-if="form.level === 'Undergraduate'" title="School leavers">
      <div class="grid">
        <EcField label="Minimum points" for="pg-points">
          <InputNumber v-model="form.min_points" input-id="pg-points" :min="0" fluid />
        </EcField>
      </div>
      <p class="ec-muted spaced">Subject requirements: a higher level or a better grade also meets one.</p>
      <div v-for="(req, index) in form.subject_requirements" :key="index" class="req-row">
        <Select v-model="req.subject" :options="setup.choices.subjects" placeholder="Subject" filter :aria-label="`Subject ${index + 1}`" class="subject" size="small" />
        <Select v-model="req.level" :options="setup.choices.school_levels" :aria-label="`Level ${index + 1}`" size="small" @change="req.grade = ''" />
        <Select v-model="req.grade" :options="grades[req.level] ?? []" placeholder="Grade" :aria-label="`Minimum grade ${index + 1}`" size="small" />
        <EcButton :icon="X" size="sm" variant="ghost" :aria-label="`Remove requirement ${index + 1}`" @click="form.subject_requirements.splice(index, 1)" />
      </div>
      <EcButton label="Add a subject" :icon="Plus" size="sm" variant="ghost" @click="addRequirement" />
    </DetailSection>

    <DetailSection title="Prior qualification">
      <div class="grid">
        <EcField label="NQF level at least" for="pg-nqf" hint="Empty: no minimum">
          <InputNumber v-model="form.min_prior_nqf" input-id="pg-nqf" :min="0" :max="10" fluid />
        </EcField>
        <EcField label="Average at least" for="pg-avg" hint="Empty: no minimum">
          <InputNumber v-model="form.min_prior_average" input-id="pg-avg" :min="0" :max="100" suffix="%" fluid />
        </EcField>
      </div>
    </DetailSection>

    <template #actions>
      <EcButton label="Undo changes" variant="ghost" :disabled="saving" @click="reset" />
      <EcButton label="Save" variant="primary" :loading="saving" @click="save" />
    </template>
  </DetailPane>
</template>

<style scoped>
.grid {
  display: grid;
  align-items: start;
  grid-template-columns: repeat(auto-fill, minmax(12rem, 1fr));
  gap: 0.9rem;
}

.spaced {
  margin: 0.9rem 0 0.5rem;
}

.req-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem;
  margin-bottom: 0.5rem;
}

.subject {
  flex: 1 1 12rem;
}
</style>
