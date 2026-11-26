<script setup lang="ts">
import PageHeader from "@/core/ui/PageHeader.vue";
import TranscriptsQueue from "./TranscriptsQueue.vue";

/** Students' official transcript requests, issued by the Registry once paid and, where required, cleared */
</script>

<template>
  <section class="list-page">
    <PageHeader title="Transcripts" subtitle="Official transcript requests, issued once paid and cleared" />
    <TranscriptsQueue />
  </section>
</template>

<style scoped>
.list-page {
  display: grid;
  gap: 1rem;
}
</style>
