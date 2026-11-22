<script setup lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Tag from "primevue/tag";
import { computed, onMounted, ref } from "vue";
import { useBranding } from "@/core/branding";
import { formatDate } from "@/core/format";
import { type ApplyOptions, getOptions } from "./api";

const { branding } = useBranding();
const options = ref<ApplyOptions | null>(null);
const error = ref("");
const search = ref("");

onMounted(async () => {
  try {
    options.value = await getOptions();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

/** one entry per programme, with the campuses and modes it is offered in */
const programmes = computed(() => {
  const byProgramme = new Map<string, { offering: ApplyOptions["offerings"][number]; places: string[] }>();
  for (const offering of options.value?.offerings ?? []) {
    const entry = byProgramme.get(offering.program) ?? { offering, places: [] };
    entry.places.push(`${offering.campus.replace(" Campus", "")} · ${offering.mode_of_study}`);
    byProgramme.set(offering.program, entry);
  }
  const term = search.value.trim().toLowerCase();
  return [...byProgramme.values()].filter(
    ({ offering }) => !term || `${offering.program} ${offering.faculty} ${offering.code}`.toLowerCase().includes(term),
  );
});
</script>

<template>
  <div class="apply">
    <header class="topbar">
      <img :src="branding.logo" :alt="branding.institution_name" class="logo" />
      <div class="actions">
        <RouterLink to="/login"><Button label="Sign in" text /></RouterLink>
        <RouterLink to="/apply/register"><Button label="Create an account" /></RouterLink>
      </div>
    </header>

    <main class="content">
      <h1>Apply to {{ branding.institution_name }}</h1>
      <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

      <template v-if="options">
        <section v-if="options.intakes.length" class="intakes">
          <article v-for="intake in options.intakes" :key="intake.name" class="intake">
            <h2>{{ intake.title }}</h2>
            <p>
              Applications are open until <strong>{{ formatDate(intake.admission_end_date) }}</strong>. Create an account, fill in
              your application in your own time, and submit it when it is complete.
            </p>
            <p class="sub">
              You can choose up to {{ options.max_choices }} programmes. You will need certified copies of your documents
              (certified within the last {{ options.certification_max_age_months }} months), scanned as PDF, JPG or PNG.
            </p>
          </article>
        </section>
        <Message v-else severity="info" :closable="false">Applications are closed at the moment.</Message>

        <section class="programmes">
          <div class="programmes-head">
            <h2>Programmes</h2>
            <InputText v-model="search" placeholder="Search programmes" aria-label="Search programmes" />
          </div>
          <Message v-if="options.scale_is_placeholder" severity="warn" :closable="false" class="note">
            Demo: the points scale is a sample, not the university's published scale.
          </Message>
          <article v-for="{ offering, places } in programmes" :key="offering.program" class="programme">
            <div class="programme-head">
              <h3>{{ offering.program }}</h3>
              <Tag v-if="offering.nqf_level" :value="`NQF ${offering.nqf_level}`" severity="secondary" />
            </div>
            <p class="sub">
              {{ offering.qualification }} · {{ offering.faculty }}<template v-if="offering.duration_years"> · {{ offering.duration_years }} years</template>
            </p>
            <p class="places">{{ places.join("  ·  ") }}</p>
            <p v-if="offering.min_points || offering.subject_requirements.length" class="requirements">
              Entry:
              <template v-if="offering.min_points">at least {{ offering.min_points }} points in your best {{ options.best_subjects }} subjects</template>
              <template v-for="req in offering.subject_requirements" :key="req.subject">; {{ req.subject }} at least {{ req.grade }} ({{ req.level }})</template>
            </p>
          </article>
        </section>
      </template>
    </main>
  </div>
</template>

<style scoped>
.apply {
  min-height: 100vh;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem clamp(16px, 4vw, 2.5rem);
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.logo {
  height: 34px;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.content {
  max-width: 64rem;
  margin: 0 auto;
  padding: 2rem 16px 4rem;
}

h1 {
  margin: 0 0 1.25rem;
  font-size: 1.8rem;
}

.intake,
.programme {
  margin-bottom: 1rem;
  padding: 1.25rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
}

.intake h2 {
  margin: 0 0 0.5rem;
  font-size: 1.2rem;
}

.intake p {
  margin: 0 0 0.5rem;
}

.programmes-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 2rem 0 1rem;
}

.programmes-head h2 {
  margin: 0;
  font-size: 1.2rem;
}

.note {
  margin-bottom: 1rem;
}

.programme-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.programme h3 {
  margin: 0 0 0.25rem;
  font-size: 1.05rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.places {
  margin: 0.5rem 0 0;
  font-size: 0.9rem;
}

.requirements {
  margin: 0.5rem 0 0;
  font-size: 0.85rem;
  color: #374151;
}
</style>
