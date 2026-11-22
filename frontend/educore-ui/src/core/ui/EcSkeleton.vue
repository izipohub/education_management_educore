<script setup lang="ts">
/**
 * The loader: grey shapes where the content will be, with a slow shimmer, so the page keeps its layout while it
 * loads. Shapes: `list` (queue rows), `pane` (a record), `tiles` (headline numbers), `card` (a panel), `lines`.
 */
withDefaults(defineProps<{ shape?: "list" | "pane" | "tiles" | "card" | "lines"; rows?: number; label?: string }>(), {
  shape: "lines",
  rows: 3,
  label: "Loading",
});
</script>

<template>
  <div class="ec-skeleton" :class="`shape-${shape}`" role="status" :aria-label="label" aria-busy="true">
    <template v-if="shape === 'list'">
      <div v-for="i in rows" :key="i" class="list-row">
        <div class="line-row"><span class="bone w-40" /><span class="bone w-20" /></div>
        <div class="line-row"><span class="bone w-25 thin" /><span class="bone w-15 thin" /></div>
      </div>
    </template>

    <template v-else-if="shape === 'pane'">
      <div class="pane-head">
        <span class="bone w-35 tall" />
        <span class="bone w-55 thin" />
        <span class="bone w-100 block" />
      </div>
      <div v-for="i in rows" :key="i" class="pane-row"><span class="bone w-15" /><span class="bone w-45" /></div>
    </template>

    <template v-else-if="shape === 'tiles'">
      <div v-for="i in rows" :key="i" class="tile">
        <span class="bone w-50 thin" />
        <span class="bone w-25 big" />
        <span class="bone w-60 thin" />
      </div>
    </template>

    <template v-else-if="shape === 'card'">
      <div class="card-body">
        <span class="bone w-35" />
        <div v-for="i in rows" :key="i" class="bar-row"><span class="bone w-20" /><span class="bone grow" /><span class="bone w-10" /></div>
      </div>
    </template>

    <template v-else>
      <span v-for="i in rows" :key="i" class="bone" :class="i === rows ? 'w-60' : 'w-100'" />
    </template>
  </div>
</template>

<style scoped>
.ec-skeleton {
  display: grid;
  gap: 0.6rem;
}

.bone {
  display: block;
  height: 0.75rem;
  border-radius: 999px;
  background: linear-gradient(90deg, #ebe8e1 0%, #f4f2ed 40%, #ebe8e1 80%);
  background-size: 300% 100%;
  animation: shimmer 1.6s ease-in-out infinite;
}

.thin {
  height: 0.55rem;
}

.tall {
  height: 1.1rem;
}

.big {
  height: 1.6rem;
  border-radius: 0.4rem;
}

.block {
  height: 2.2rem;
  border-radius: var(--ec-radius-sm);
}

.grow {
  flex: 1;
}

.w-10 { width: 10%; }
.w-15 { width: 15%; }
.w-20 { width: 20%; }
.w-25 { width: 25%; }
.w-35 { width: 35%; }
.w-40 { width: 40%; }
.w-45 { width: 45%; }
.w-50 { width: 50%; }
.w-55 { width: 55%; }
.w-60 { width: 60%; }
.w-100 { width: 100%; }

.shape-list {
  gap: 0;
}

.list-row {
  display: grid;
  gap: 0.45rem;
  padding: 0.85rem 1rem;
  border-top: 1px solid var(--ec-border-soft);
}

.list-row:first-child {
  border-top: 0;
}

.line-row,
.pane-row,
.bar-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.shape-pane {
  gap: 0;
}

.pane-head {
  display: grid;
  gap: 0.55rem;
  padding: 1.1rem 1.25rem;
  border-bottom: 1px solid var(--ec-border);
}

.pane-row {
  justify-content: flex-start;
  gap: 2rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--ec-border-soft);
}

.shape-tiles {
  grid-template-columns: repeat(auto-fill, minmax(12.5rem, 1fr));
  gap: 1rem;
}

.tile {
  display: grid;
  gap: 0.6rem;
  padding: 1rem 1.1rem;
  background: var(--ec-surface);
  border: 1px solid var(--ec-border);
  border-radius: var(--ec-radius);
}

.card-body {
  display: grid;
  gap: 0.9rem;
}

@keyframes shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: 0 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .bone {
    animation: none;
  }
}
</style>
