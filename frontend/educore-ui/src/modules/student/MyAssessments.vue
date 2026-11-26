<script setup lang="ts">
import { ExternalLink } from "@lucide/vue";
import Message from "primevue/message";
import { computed, onMounted, ref } from "vue";
import { formatDate } from "@/core/format";
import EcPanel from "@/core/ui/EcPanel.vue";
import { type MyModuleAssessments, getAssessments } from "./api";

/**
 * The student's assessments this year, module by module: each assessment's type, what it is marked out of, its share
 * of the CA, its due date and (online) its Moodle activity; the student's scores and CA as the university shows them.
 */
const modules = ref<MyModuleAssessments[]>([]);
const year = ref<string | null>(null);
const loaded = ref(false);
const error = ref("");
onMounted(async () => {
  try {
    const page = await getAssessments();
    modules.value = page.modules;
    year.value = page.academic_year;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loaded.value = true;
  }
});
const planned = computed(() => modules.value.filter((m) => m.assessments.length));
const unplanned = computed(() => modules.value.filter((m) => !m.assessments.length));
const note = (m: MyModuleAssessments) => {
  if (!m.scores_shown) return "Scores once the results are published";
  if (m.ca !== null) return `CA ${m.ca} · provisional until the results are published`;
  return `${m.marked} of ${m.assessments.length} marked`;
};
</script>

<template>
  <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
  <template v-else-if="loaded">
    <p v-if="!modules.length" class="ec-muted none">You are not in any module yet.</p>
    <EcPanel v-for="m in planned" :key="m.group" :title="`${m.code ?? ''} ${m.course}`" :note="note(m)" flush>
      <table class="ec-table">
        <thead>
          <tr><th>Assessment</th><th>Due</th><th class="num">Share of CA</th><th class="num">Score</th></tr>
        </thead>
        <tbody>
          <tr v-for="a in m.assessments" :key="a.title">
            <td>
              {{ a.title }}
              <div class="ec-muted">
                {{ a.kind }}
                <template v-if="a.moodle_url">
                  · <a :href="a.moodle_url" target="_blank" rel="noopener" class="link">Open in Moodle <ExternalLink :size="11" /></a>
                </template>
              </div>
            </td>
            <td>{{ formatDate(a.due_date) }}</td>
            <td class="num">{{ a.weight }}%</td>
            <td class="num">
              <template v-if="a.score !== null">{{ a.score }} / {{ a.out_of }}</template>
              <span v-else class="ec-muted">out of {{ a.out_of }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </EcPanel>
    <p v-if="unplanned.length" class="ec-muted none">
      No assessments set yet: {{ unplanned.map((m) => m.code ?? m.course).join(", ") }}
    </p>
  </template>
</template>

<style scoped>
.none {
  margin: 0;
}

.link {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
  color: var(--ec-accent);
  text-decoration: none;
}
</style>
