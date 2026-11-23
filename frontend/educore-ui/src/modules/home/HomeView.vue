<script setup lang="ts">
import Message from "primevue/message";
import Select from "primevue/select";
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useSession } from "@/core/auth/session";
import { formatDate, formatMoney, formatMoneyCompact } from "@/core/format";
import { offerLabel } from "@/core/status";
import BarList from "@/core/ui/BarList.vue";
import DonutChart from "@/core/ui/charts/DonutChart.vue";
import LineChart from "@/core/ui/charts/LineChart.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import EcSkeleton from "@/core/ui/EcSkeleton.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import StatTile from "@/core/ui/StatTile.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type Application, listApplications } from "@/modules/admissions/api";
import { type QueueRow, getQueue } from "@/modules/registration/api";
import { type DashboardStats, getStats } from "./api";

/**
 * The staff home: headline figures with where to act on them, the year in charts, and the work waiting (oldest
 * first, each row opens its record), for one campus or every campus the user works on.
 */
const session = useSession();
const route = useRoute();
const router = useRouter();
const me = computed(() => session.me);

/** "All campuses" in the picker; no campus in the address */
const ALL = "all";
const campus = ref<string>((route.query.campus as string) || ALL);
const chosen = computed(() => (campus.value === ALL ? "" : campus.value));
const stats = ref<DashboardStats | null>(null);
const applications = ref<Application[]>([]);
const registrations = ref<QueueRow[]>([]);
const loading = ref(false);
const error = ref("");

const LIST = 5;
const byDate = <T,>(rows: T[], key: (r: T) => string | null) => [...rows].sort((a, b) => (key(a) ?? "").localeCompare(key(b) ?? ""));

let workRead = false;
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const [s, a, r] = await Promise.all([
      getStats(chosen.value || undefined),
      // the work lists are read once; the campus filter narrows them here
      workRead || !session.hasRole("Admissions Officer", "Registrar") ? null : listApplications({ status: "Applied" }).catch(() => null),
      workRead || !session.hasRole("Faculty Officer", "Registrar") ? null : getQueue("Submitted").catch(() => null),
    ]);
    stats.value = s;
    if (a) applications.value = byDate(a.rows, (x) => x.application_date);
    if (r) registrations.value = byDate(r.rows, (x) => x.submitted_on);
    workRead = true;
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
}
onMounted(load);
watch(campus, () => {
  void router.replace({ query: chosen.value ? { campus: chosen.value } : {} });
  void load();
});

const inCampus = (c: string | null | undefined) => !chosen.value || c === chosen.value;
const toDecide = computed(() => applications.value.filter((a) => inCampus(a.campus)).slice(0, LIST));
const toApprove = computed(() => registrations.value.filter((r) => inCampus(r.campus)).slice(0, LIST));

const s = computed(() => stats.value?.sections ?? {});
const campusOptions = computed(() => [
  { label: "All campuses", value: ALL },
  ...(stats.value?.campuses ?? []).map((c) => ({ label: c, value: c })),
]);
const scope = computed(() =>
  [chosen.value || (me.value?.campuses.length ? me.value.campuses.join(", ") : "All campuses"), formatDate(stats.value?.today)].filter(Boolean).join(" · "),
);
const greeting = computed(() => {
  const hour = new Date().getHours();
  return `${hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening"}, ${me.value?.first_name ?? ""}`;
});
const collectionRate = computed(() => {
  const f = s.value.fees;
  return f && f.invoiced ? Math.round((f.collected / f.invoiced) * 100) : 0;
});
const share = (taken: number, capacity: number) => (capacity ? Math.min(100, (taken / capacity) * 100) : 0);
const offerResponses = computed(() => (s.value.admissions?.offer_responses ?? []).map((r) => ({ label: offerLabel(r.label), value: r.value })));
const genders = computed(() => (s.value.students?.by_gender ?? []).filter((g) => g.label !== "Not set"));
const showCampusDonut = computed(() => Boolean(s.value.students && !chosen.value && s.value.students.by_campus.length > 1));
</script>

<template>
  <section v-if="me" class="home">
    <PageHeader :title="greeting" :subtitle="scope">
      <template v-if="(stats?.campuses.length ?? 0) > 1" #actions>
        <Select v-model="campus" :options="campusOptions" option-label="label" option-value="value" aria-label="Campus" size="small" class="campus" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <template v-else-if="!stats">
      <EcSkeleton shape="tiles" :rows="4" label="Loading the dashboard" />
      <div class="row two">
        <div class="card"><EcSkeleton shape="card" :rows="4" label="Loading" /></div>
        <div class="card"><EcSkeleton shape="card" :rows="3" label="Loading" /></div>
      </div>
    </template>

    <div v-else class="board" :class="{ busy: loading }" :aria-busy="loading">
      <!-- the headline figures, each with where to act on it -->
      <div class="tiles">
        <StatTile v-if="s.students" label="Students" :value="s.students.total" :hint="chosen || `${s.students.by_campus.length} campuses`" />
        <StatTile
          v-if="s.admissions"
          :label="`Applications ${s.admissions.academic_year ?? ''}`"
          :value="s.admissions.total"
          :hint="`${s.admissions.by_channel[0]?.value ?? 0} online · ${s.admissions.by_channel[1]?.value ?? 0} paper`"
          to="/admissions"
          action="All applications"
        />
        <StatTile
          v-if="s.admissions"
          label="To decide"
          :value="s.admissions.pipeline[0]?.value ?? 0"
          :hint="`${s.admissions.fee_unpaid} with the fee outstanding`"
          :to="{ path: '/admissions', query: { status: 'Applied' } }"
          action="Review"
        />
        <StatTile
          v-if="s.admissions"
          label="Offers pending"
          :value="s.admissions.offers_pending"
          hint="Awaiting the applicant"
          :to="{ path: '/admissions', query: { status: 'Approved' } }"
          action="View offers"
        />
        <StatTile
          v-if="s.enrolment"
          label="To register"
          :value="s.enrolment.waiting"
          :hint="`${s.enrolment.enrolled} first-year students registered`"
          :to="{ path: '/registrations', query: { group: 'first-year' } }"
          action="Register"
        />
        <StatTile
          v-if="s.registration?.academic_year"
          label="Registrations to approve"
          :value="s.registration.submitted ?? 0"
          :hint="`${s.registration.approved ?? 0} approved · ${s.registration.returned ?? 0} returned`"
          :to="{ path: '/registrations', query: { group: 'senior' } }"
          action="Approve"
        />
        <StatTile v-if="s.fees" label="Fees outstanding" :value="formatMoneyCompact(s.fees.outstanding)" :hint="`${collectionRate}% collected in ${s.fees.year}`" />
      </div>

      <!-- admissions: over time, how they arrived -->
      <div v-if="s.admissions" class="row wide-narrow">
        <EcPanel title="Applications received" note="Last 12 months">
          <LineChart :points="s.admissions.by_month" label="Applications received per month" />
        </EcPanel>
        <EcPanel title="How applications arrived">
          <DonutChart :slices="s.admissions.by_channel" label="Applications by channel" centre-label="Applications" />
        </EcPanel>
      </div>

      <div v-if="s.admissions" class="row three">
        <EcPanel :title="`Admissions ${s.admissions.academic_year ?? ''}`">
          <BarList :rows="s.admissions.pipeline" label="Applications by stage" />
          <p class="ec-muted foot">{{ s.admissions.unsuccessful }} unsuccessful · {{ s.admissions.declined_or_lapsed }} declined or lapsed</p>
        </EcPanel>
        <EcPanel title="Entry pathway">
          <DonutChart :slices="s.admissions.by_pathway" label="Applications by entry pathway" centre-label="Applications" />
        </EcPanel>
        <EcPanel title="Offer responses">
          <DonutChart :slices="offerResponses" label="Offers by response" centre-label="Offers" />
        </EcPanel>
      </div>

      <div v-if="s.admissions?.by_programme.length" class="row two">
        <EcPanel title="Applications by programme" note="Most applied for">
          <BarList :rows="s.admissions.by_programme" label="Applications by programme" />
        </EcPanel>
        <EcPanel v-if="s.admissions.offerings.length" title="Places offered" note="Fullest first" flush>
          <table class="ec-table">
            <thead>
              <tr><th>Offering</th><th class="meter-col wide" aria-hidden="true"></th><th class="num">Offered</th></tr>
            </thead>
            <tbody>
              <tr v-for="o in s.admissions.offerings" :key="o.label">
                <td class="ec-nowrap">{{ o.label }}</td>
                <td class="wide"><span class="meter" aria-hidden="true"><span :style="{ width: `${share(o.taken, o.capacity)}%` }" /></span></td>
                <td class="num ec-nowrap">
                  {{ o.taken }} <span class="ec-muted">of {{ o.capacity }}</span><span v-if="o.capacity && o.taken >= o.capacity" class="full"> · Full</span>
                </td>
              </tr>
            </tbody>
          </table>
        </EcPanel>
      </div>

      <!-- the work waiting -->
      <div v-if="s.admissions || s.registration?.academic_year" class="row two">
        <EcPanel v-if="s.admissions" title="Awaiting a decision" flush>
          <template #note><RouterLink :to="{ path: '/admissions', query: { status: 'Applied' } }" class="more">View all</RouterLink></template>
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
          <template #note><RouterLink :to="{ path: '/registrations', query: { group: 'senior' } }" class="more">View all</RouterLink></template>
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
      </div>

      <!-- students, registration and fees -->
      <div v-if="showCampusDonut || genders.length > 1 || s.registration?.academic_year || s.fees" class="row three">
        <EcPanel v-if="showCampusDonut" title="Students by campus">
          <DonutChart :slices="s.students!.by_campus.map((c) => ({ label: c.label.replace(' Campus', ''), value: c.value }))" label="Students by campus" centre-label="Students" />
        </EcPanel>
        <EcPanel v-if="genders.length > 1" title="Students by gender">
          <DonutChart :slices="genders" label="Students by gender" centre-label="Students" />
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
      </div>
    </div>
  </section>
</template>

<style scoped>
.home,
.board {
  display: grid;
  gap: 1.25rem;
}

.board {
  transition: opacity 0.15s ease;
}

.board.busy {
  opacity: 0.6;
}

.campus {
  min-width: 12rem;
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 11rem), 1fr));
  gap: 1rem;
}

.row {
  display: grid;
  gap: 1rem;
  align-items: start;
}

.row.two {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 26rem), 1fr));
}

.row.three {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 20rem), 1fr));
}

.row.wide-narrow {
  grid-template-columns: minmax(0, 2fr) minmax(min(100%, 20rem), 1fr);
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
  width: 45%;
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
  .row.wide-narrow {
    grid-template-columns: minmax(0, 1fr);
  }
}

@media (max-width: 767px) {
  .wide {
    display: none;
  }
}
</style>
