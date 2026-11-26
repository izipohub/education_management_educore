<script setup lang="ts">
import PageHeader from "@/core/ui/PageHeader.vue";
import StudiesRequestsQueue from "./StudiesRequestsQueue.vue";

/** Students' requests to interrupt or cancel their studies or move campus, for the Registry to decide */
</script>

<template>
  <section class="list-page">
    <PageHeader title="Studies requests" subtitle="Interruptions, cancellations and campus transfers students ask for" />
    <StudiesRequestsQueue />
  </section>
</template>

<style scoped>
.list-page {
  display: grid;
  gap: 1rem;
}
</style>
