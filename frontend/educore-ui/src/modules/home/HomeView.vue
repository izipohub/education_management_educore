<script setup lang="ts">
import Message from "primevue/message";
import { computed, onMounted, ref } from "vue";
import { useSession } from "@/core/auth/session";
import { formatDate, formatMoney, formatMoneyCompact } from "@/core/format";
import BarList from "@/core/ui/BarList.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatTile from "@/core/ui/StatTile.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Application, listApplications } from "@/modules/admissions/api";
import { type QueueRow, getQueue } from "@/modules/registration/api";
import { type DashboardStats, getStats } from "./api";

/**
 * The staff home: the headline numbers, then the work waiting (oldest first, each row opens its record) beside
 * the year's figures, for the campuses and faculties the user works on.
 */
const session = useSession();
const me = computed(() => session.me);
const stats = ref<DashboardStats | null>(null);
const toDecide = ref<Application[]>([]);
const toApprove = ref<QueueRow[]>([]);
const error = ref("");

const LIST = 5;
const byDate = <T,>(rows: T[], key: (r: T) => string | null) => [...rows].sort((a, b) => (key(a) ?? "").localeCompare(key(b) ?? ""));

onMounted(async () => {
  try {
    const [s, applications, registrations] = await Promise.all([
      getStats(),
      session.hasRole("Admissions Officer", "Registrar") ? listApplications({ status: "Applied" }).catch(() => null) : null,
      session.hasRole("Faculty Officer", "Registrar") ? getQueue("Submitted").catch(() => null) : null,
    ]);
    stats.value = s;
    toDecide.value = byDate(applications?.rows ?? [], (r) => r.application_date).slice(0, LIST);
    toApprove.value = byDate(registrations?.rows ?? [], (r) => r.submitted_on).slice(0, LIST);
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
const collectionRate = computed(() => {
  const f = s.value.fees;
  return f && f.invoiced ? Math.round((f.collected / f.invoiced) * 100) : 0;
});
const share = (taken: number, capacity: number) => (capacity ? Math.min(100, (taken / capacity) * 100) : 0);
</script>

<template>
  <section v-if="me" class="home">
    <PageHeader :title="greeting" :subtitle="scope" />

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <template v-else-if="!stats">
      <EcSkeleton shape="tiles" :rows="4" label="Loading the dashboard" />
      <div class="layout">
        <div class="card"><EcSkeleton shape="list" :rows="4" label="Loading" /></div>
        <div class="card"><EcSkeleton shape="card" :rows="3" label="Loading" /></div>
      </div>
    </template>

    <template v-else>
      <!-- the headline numbers, each with where to act on it -->
      <div class="tiles">
        <StatTile v-if="s.students" label="Students" :value="s.students.total" :hint="s.students.by_campus.length === 1 ? s.students.by_campus[0]!.label : `${s.students.by_campus.length} campuses`" />
        <StatTile
          v-if="s.admissions"
          label="Applications to decide"
          :value="s.admissions.pipeline[0]?.value ?? 0"
          :hint="`${s.admissions.fee_unpaid} with the fee outstanding`"
          to="/admissions"
          action="Review"
        />
        <StatTile v-if="s.admissions" label="Offers pending" :value="s.admissions.offers_pending" hint="Awaiting the applicant" to="/admissions?status=Approved" action="View offers" />
        <StatTile v-if="s.enrolment" label="To register" :value="s.enrolment.waiting" :hint="`${s.enrolment.enrolled} registered`" to="/registrations?group=first-year" action="Register" />
        <StatTile
          v-if="s.registration?.academic_year"
          label="Registrations to approve"
          :value="s.registration.submitted ?? 0"
          :hint="`${s.registration.approved ?? 0} approved · ${s.registration.returned ?? 0} returned`"
          to="/registrations?group=senior"
          action="Approve"
        />
        <StatTile v-if="s.fees" label="Fees outstanding" :value="formatMoneyCompact(s.fees.outstanding)" :hint="`${collectionRate}% collected in ${s.fees.year}`" />
      </div>

      <div class="layout">
        <!-- the work waiting -->
        <div class="column">
          <EcPanel v-if="s.admissions" title="Awaiting a decision" flush>
            <template #note><RouterLink to="/admissions" class="more">View all</RouterLink></template>
            <table v-if="toDecide.length" class="ec-table">
              <thead>
                <tr><th>Applicant</th><th>Programme</th><th class="wide">Applied</th><th>Fee</th></tr>
              </thead>
              <tbody>
                <tr v-for="a in toDecide" :key="a.name">
                  <td><RouterLink :to="{ name: 'application-record', params: { name: a.name } }" class="record">{{ a.applicant }}</RouterLink></td>
                  <td>{{ a.offering }}</td>
                  <td class="wide ec-nowrap">{{ formatDate(a.application_date) }}</td>
                  <td><StatusTag v-if="a.online" kind="fee" :value="a.fee_status" /><span v-else class="ec-muted">Paper</span></td>
                </tr>
              </tbody>
            </table>
            <p v-else class="none ec-muted">No applications waiting.</p>
          </EcPanel>

          <EcPanel v-if="s.registration?.academic_year" title="Registrations to approve" flush>
            <template #note><RouterLink to="/registrations?group=senior" class="more">View all</RouterLink></template>
            <table v-if="toApprove.length" class="ec-table">
              <thead>
                <tr><th>Student</th><th>Programme</th><th class="wide">Submitted</th><th class="num">Credits</th></tr>
              </thead>
              <tbody>
                <tr v-for="r in toApprove" :key="r.name">
                  <td><RouterLink :to="{ name: 'registration-record', params: { name: r.name } }" class="record">{{ r.student_name }}</RouterLink></td>
                  <td>{{ r.offering }}</td>
                  <td class="wide ec-nowrap">{{ formatDate(r.submitted_on) }}</td>
                  <td class="num">{{ r.credits }}</td>
                </tr>
              </tbody>
            </table>
            <p v-else class="none ec-muted">No registrations waiting.</p>
          </EcPanel>

          <EcPanel v-if="s.admissions?.offerings.length" title="Places offered" note="Fullest first" flush>
            <table class="ec-table">
              <thead>
                <tr><th>Offering</th><th class="meter-col wide" aria-hidden="true"></th><th class="num">Offered</th><th class="num">Applying</th></tr>
              </thead>
              <tbody>
                <tr v-for="o in s.admissions.offerings" :key="o.label">
                  <td class="ec-nowrap">{{ o.label }}</td>
                  <td class="wide">
                    <span class="meter" aria-hidden="true"><span :style="{ width: `${share(o.taken, o.capacity)}%` }" /></span>
                  </td>
                  <td class="num ec-nowrap">
                    {{ o.taken }} <span class="ec-muted">of {{ o.capacity }}</span><span v-if="o.capacity && o.taken >= o.capacity" class="full"> · Full</span>
                  </td>
                  <td class="num">{{ o.applied }}</td>
                </tr>
              </tbody>
            </table>
          </EcPanel>
        </div>

        <!-- the year's figures -->
        <div class="column">
          <EcPanel v-if="s.admissions" :title="`Admissions ${s.admissions.academic_year ?? ''}`">
            <BarList :rows="s.admissions.pipeline" label="Applications by stage" />
            <p class="ec-muted foot">{{ s.admissions.unsuccessful }} unsuccessful · {{ s.admissions.declined_or_lapsed }} declined or lapsed</p>
          </EcPanel>

          <EcPanel v-if="s.registration?.academic_year" :title="`Registration ${s.registration.academic_year}`">
            <template #note><StatusTag kind="period" :value="s.registration.state" /></template>
            <dl class="ec-facts counts">
              <div><dt>Submitted</dt><dd>{{ s.registration.submitted ?? 0 }}</dd></div>
              <div><dt>Returned</dt><dd>{{ s.registration.returned ?? 0 }}</dd></div>
              <div><dt>Approved</dt><dd>{{ s.registration.approved ?? 0 }}</dd></div>
            </dl>
            <p v-if="s.registration.closes_on" class="ec-muted foot">Closes {{ formatDate(s.registration.closes_on) }}</p>
          </EcPanel>

          <EcPanel v-if="s.fees" :title="`Student fees ${s.fees.year}`" :note="`${collectionRate}% collected`">
            <BarList
              :rows="s.fees.by_campus.map((c) => ({ label: c.label.replace(' Campus', ''), value: c.collected, max: c.invoiced }))"
              :format="formatMoneyCompact"
              label="Fees collected against invoiced, per campus"
            />
            <p class="ec-muted foot">{{ formatMoney(s.fees.collected) }} of {{ formatMoney(s.fees.invoiced) }}</p>
          </EcPanel>

          <EcPanel v-if="s.students && s.students.by_campus.length > 1" title="Students by campus" flush>
            <table class="ec-table">
              <tbody>
                <tr v-for="c in s.students.by_campus" :key="c.label">
                  <td>{{ c.label.replace(" Campus", "") }}</td>
                  <td class="num">{{ c.value }}</td>
                </tr>
              </tbody>
            </table>
          </EcPanel>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.home {
  display: grid;
  gap: 1.25rem;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 12.5rem), 1fr));
  gap: 1rem;
}

.layout {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(min(100%, 18rem), 1fr);
  gap: 1rem;
  align-items: start;
}

.column {
  display: grid;
  gap: 1rem;
  min-width: 0;
}

.more {
  color: var(--ec-accent);
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
}

.more:hover,
.record:hover {
  text-decoration: underline;
}

.record {
  color: var(--ec-ink);
  font-weight: 600;
  text-decoration: none;
}

.none {
  margin: 0;
  padding: 1rem 1.25rem;
}

.foot {
  margin: 0.9rem 0 0;
}

.meter-col {
  width: 40%;
}

.meter {
  display: block;
  height: 0.4rem;
  border-radius: 999px;
  background: color-mix(in srgb, var(--ec-accent) 12%, white);
}

.meter span {
  display: block;
  height: 100%;
  min-width: 2px;
  border-radius: 999px;
  background: var(--ec-accent);
}

.full {
  color: var(--ec-ink);
  font-weight: 600;
}

.counts {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.counts dd {
  font-size: 1.375rem;
  font-weight: 600;
  color: var(--ec-ink);
}

@media (max-width: 1023px) {
  .layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .wide {
    display: none;
  }
}
</style>
