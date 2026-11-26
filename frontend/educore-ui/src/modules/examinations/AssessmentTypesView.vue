<script setup lang="ts">
import PageHeader from "@/core/ui/PageHeader.vue";
import AssessmentTypesPanel from "./AssessmentTypesPanel.vue";

/** The faculty's assessment types, on their own page: kept by the Dean, read by the department and the faculty */
</script>

<template>
  <section class="types-page">
    <PageHeader title="Assessment types" subtitle="The kinds of continuous assessment the faculty's lecturers may plan" />
    <AssessmentTypesPanel />
  </section>
</template>

<style scoped>
.types-page {
  display: grid;
  gap: 1rem;
  max-width: 52rem;
}
</style>
