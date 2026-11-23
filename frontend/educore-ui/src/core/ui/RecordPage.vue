<script setup lang="ts">
import { ChevronLeft } from "@lucide/vue";
import Message from "primevue/message";
import type { RouteLocationRaw } from "vue-router";
import ChecklistPanel from "./ChecklistPanel.vue";
import EcSkeleton from "./EcSkeleton.vue";

/**
 * One record on its own page: a link back to its list, the title with its status, the decisions on the right,
 * then the record in panels (main column) beside a summary (side column). Nothing colours the page: what is
 * outstanding is listed in a panel, in words.
 */
withDefaults(
  defineProps<{
    back: { to: RouteLocationRaw; label: string };
    title?: string;
    subtitle?: string;
    loading?: boolean;
    error?: string;
    /** what is still to be done, in words: first in the side column, above the record on a narrow screen */
    outstanding?: string[];
  }>(),
  { title: undefined, subtitle: undefined, loading: false, error: "", outstanding: () => [] },
);
</script>

<template>
  <article class="record">
    <RouterLink :to="back.to" class="back"><ChevronLeft :size="16" aria-hidden="true" />{{ back.label }}</RouterLink>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <template v-else-if="loading || !title">
      <div class="card"><EcSkeleton shape="pane" :rows="4" label="Loading the record" /></div>
    </template>

    <template v-else>
      <header class="head">
        <div class="titles">
          <div class="title-row">
            <h1>{{ title }}</h1>
            <slot name="tags" />
          </div>
          <p v-if="subtitle" class="ec-muted">{{ subtitle }}</p>
        </div>
        <div v-if="$slots.actions" class="actions"><slot name="actions" /></div>
      </header>

      <div class="layout" :class="{ 'has-aside': $slots.aside || outstanding.length }">
        <div class="main">
          <ChecklistPanel :items="outstanding" class="narrow-only" />
          <slot />
        </div>
        <aside v-if="$slots.aside || outstanding.length" class="aside">
          <ChecklistPanel :items="outstanding" class="wide-only" />
          <slot name="aside" />
        </aside>
      </div>
    </template>
  </article>
</template>

<style scoped>
.record {
  display: grid;
  gap: 1rem;
}

.back {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  justify-self: start;
  color: var(--ec-muted);
  font-size: 0.8125rem;
  text-decoration: none;
}

.back:hover {
  color: var(--ec-accent);
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid var(--ec-border);
}

.titles {
  min-width: 0;
}

.title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.75rem;
}

h1 {
  margin: 0;
  font-size: 1.625rem;
  line-height: 1.2;
}

.titles p {
  margin: 0.3rem 0 0;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.layout {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.layout.has-aside {
  grid-template-columns: minmax(0, 1fr) minmax(16rem, 20rem);
}

.main,
.aside {
  display: grid;
  gap: 1rem;
  min-width: 0;
}

@media (max-width: 1023px) {
  .layout.has-aside {
    grid-template-columns: minmax(0, 1fr);
  }

  .wide-only {
    display: none;
  }
}

@media (min-width: 1024px) {
  .narrow-only {
    display: none;
  }
}
</style>
