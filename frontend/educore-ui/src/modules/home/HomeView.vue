<script setup lang="ts">
import Message from "primevue/message";
import Tag from "primevue/tag";
import { computed, onMounted, ref } from "vue";
import { useSession } from "@/core/auth/session";
import { formatDate, formatMoney, formatMoneyCompact } from "@/core/format";
import BarList from "@/core/ui/BarList.vue";
import DetailSection from "@/core/ui/DetailSection.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatTile from "@/core/ui/StatTile.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type DashboardStats, getStats } from "./api";

/** The staff home: the numbers each position needs, for the campuses and faculties the user works on */
const session = useSession();
const me = computed(() => session.me);
const stats = ref<DashboardStats | null>(null);
const error = ref("");

onMounted(async () => {
  try {
    stats.value = await getStats();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

const s = computed(() => stats.value?.sections ?? {});
const scope = computed(() => [me.value?.campuses.length ? me.value.campuses.join(", ") : "The whole university", formatDate(stats.value?.today)].filter(Boolean).join(" · "));
const greeting = computed(() => {
  const hour = new Date().getHours();
  return `${hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening"}, ${me.value?.first_name ?? ""}`;
});
const units = computed(() => (me.value?.units.length ? me.value.units.map((u) => u.replace(/ - [A-Z]+$/, "")).join(", ") : "All faculties and divisions"));
const collectionRate = computed(() => {
  const f = s.value.fees;
  return f && f.invoiced ? Math.round((f.collected / f.invoiced) * 100) : 0;
});
const hasAny = computed(() => Object.keys(s.value).length > 0);
</script>

<template>
  <section v-if="me" class="home">
    <PageHeader :title="greeting" :subtitle="scope" />

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <template v-else-if="!stats">
      <EcSkeleton shape="tiles" :rows="4" label="Loading the dashboard" />
      <div class="panels">
        <div v-for="i in 2" :key="i" class="card"><EcSkeleton shape="card" :rows="4" label="Loading" /></div>
      </div>
    </template>

    <template v-else>
      <!-- the headline numbers, each with where to act on it -->
      <div v-if="hasAny" class="tiles">
        <StatTile v-if="s.students" label="Students" :value="s.students.total" :hint="s.students.by_campus.length === 1 ? s.students.by_campus[0]!.label : `${s.students.by_campus.length} campuses`" />
        <StatTile
          v-if="s.admissions"
          label="Applications to decide"
          :value="s.admissions.pipeline[0]?.value ?? 0"
          :hint="`${s.admissions.fee_unpaid} with the fee unpaid`"
          to="/admissions"
          action="Review"
        />
        <StatTile
          v-if="s.admissions"
          label="Offers pending"
          :value="s.admissions.offers_pending"
          hint="Waiting for the applicant"
          to="/admissions"
          action="View offers"
        />
        <StatTile v-if="s.enrolment" label="Waiting to enrol" :value="s.enrolment.waiting" :hint="`${s.enrolment.enrolled} enrolled`" to="/enrolment" action="Enrol" />
        <StatTile
          v-if="s.registration?.academic_year"
          label="Registrations to approve"
          :value="s.registration.submitted ?? 0"
          :hint="`${s.registration.approved ?? 0} approved · ${s.registration.returned ?? 0} returned`"
          to="/registrations"
          action="Approve"
        />
        <StatTile v-if="s.fees" label="Fees outstanding" :value="formatMoneyCompact(s.fees.outstanding)" :hint="`${collectionRate}% collected in ${s.fees.year}`" />
      </div>

      <div class="panels">
        <article v-if="s.admissions" class="card panel">
          <header class="panel-head">
            <h2>Admissions {{ s.admissions.academic_year }}</h2>
            <span class="ec-muted">{{ s.admissions.unsuccessful }} unsuccessful · {{ s.admissions.declined_or_lapsed }} declined or lapsed</span>
          </header>
          <BarList :rows="s.admissions.pipeline" label="Applications by stage" />
        </article>

        <article v-if="s.admissions?.offerings.length" class="card panel">
          <header class="panel-head">
            <h2>Places offered</h2>
            <span class="ec-muted">Fullest first</span>
          </header>
          <BarList
            :rows="s.admissions.offerings.map((o) => ({ label: o.label, value: o.taken, max: o.capacity, note: `${o.applied} still applying` }))"
            full-label="Full"
            label="Places offered against capacity, per offering"
          />
        </article>

        <article v-if="s.fees" class="card panel">
          <header class="panel-head">
            <h2>Student fees {{ s.fees.year }}</h2>
            <span class="ec-muted">{{ formatMoney(s.fees.collected) }} of {{ formatMoney(s.fees.invoiced) }} collected</span>
          </header>
          <p class="hero">{{ collectionRate }}%<span class="ec-muted"> collected</span></p>
          <BarList
            :rows="s.fees.by_campus.map((c) => ({ label: c.label.replace(' Campus', ''), value: c.collected, max: c.invoiced }))"
            :format="formatMoneyCompact"
            label="Fees collected against invoiced, per campus"
          />
        </article>

        <article v-if="s.registration?.academic_year" class="card panel">
          <header class="panel-head">
            <h2>Registration {{ s.registration.academic_year }}</h2>
            <StatusTag kind="period" :value="s.registration.state" />
          </header>
          <BarList
            :rows="[
              { label: 'Submitted', value: s.registration.submitted ?? 0 },
              { label: 'Returned', value: s.registration.returned ?? 0 },
              { label: 'Approved', value: s.registration.approved ?? 0 },
            ]"
            label="Registrations by status"
          />
          <p v-if="s.registration.closes_on" class="ec-muted foot">Closes {{ formatDate(s.registration.closes_on) }}</p>
        </article>

        <article v-if="s.students && s.students.by_campus.length > 1" class="card panel">
          <header class="panel-head">
            <h2>Students by campus</h2>
          </header>
          <BarList :rows="s.students.by_campus.map((c) => ({ label: c.label.replace(' Campus', ''), value: c.value }))" label="Students by campus" />
        </article>
      </div>

      <article class="card access">
        <DetailSection title="Your access" collapsible>
          <template #summary>
            <span>{{ me.positions.join(", ") || "No position yet" }}</span>
          </template>
          <dl class="facts">
            <div>
              <dt>Positions</dt>
              <dd class="tags"><Tag v-for="p in me.positions" :key="p" :value="p" severity="secondary" /></dd>
            </div>
            <div><dt>Campus</dt><dd>{{ me.campuses.length ? me.campuses.join(", ") : "The whole university" }}</dd></div>
            <div><dt>Faculty / unit</dt><dd>{{ units }}</dd></div>
          </dl>
        </DetailSection>
      </article>
    </template>
  </section>
</template>

<style scoped>
.home {
  display: grid;
  gap: 1rem;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(12.5rem, 1fr));
  gap: 1rem;
}

.panels {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 24rem), 1fr));
  gap: 1rem;
}

.panel {
  display: grid;
  align-content: start;
  gap: 0.9rem;
}

.panel-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 0.25rem 0.75rem;
}

h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 650;
}

.hero {
  margin: 0;
  font-size: 2.25rem;
  font-weight: 650;
  line-height: 1;
  color: var(--ec-ink);
}

.hero .ec-muted {
  margin-left: 0.4rem;
  font-size: 0.9rem;
  font-weight: 400;
}

.foot {
  margin: 0;
}

.access {
  padding: 0;
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(14rem, 1fr));
  gap: 0.75rem 1.5rem;
  margin: 0;
}

.facts dt {
  font-size: 0.75rem;
  color: var(--ec-muted);
}

.facts dd {
  margin: 0.15rem 0 0;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
</style>
