<script setup lang="ts">
import PageHeader from "@/core/ui/PageHeader.vue";
import Tag from "primevue/tag";
import { computed } from "vue";
import { useSession } from "@/core/auth/session";

const session = useSession();
const me = computed(() => session.me);

/** "Oshakati Campus" or "the whole university": what this user's records are limited to */
const campusScope = computed(() => (me.value?.campuses.length ? me.value.campuses.join(", ") : "The whole university"));
const unitScope = computed(() =>
  me.value?.units.length ? me.value.units.map((unit) => unit.replace(/ - [A-Z]+$/, "")).join(", ") : "All faculties and divisions",
);
</script>

<template>
  <section v-if="me" class="home">
    <PageHeader :title="`Welcome, ${me.first_name}`" subtitle="Your access in EduCore: positions, campuses and units." />

    <div class="cards">
      <article class="card">
        <h2>Your positions</h2>
        <div v-if="me.positions.length" class="tags">
          <Tag v-for="position in me.positions" :key="position" :value="position" />
        </div>
        <p v-else class="muted">No position yet. Ask your administrator.</p>
      </article>

      <article class="card">
        <h2>Campus</h2>
        <p>{{ campusScope }}</p>
      </article>

      <article class="card">
        <h2>Faculty / unit</h2>
        <p>{{ unitScope }}</p>
      </article>

      <article v-if="me.student" class="card">
        <h2>Student number</h2>
        <p>{{ me.student }}</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

.intro {
  margin: 0 0 1.5rem;
  color: #6b7280;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}


.card h2 {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6b7280;
}

.card p {
  margin: 0;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.muted {
  color: #6b7280;
}
</style>
