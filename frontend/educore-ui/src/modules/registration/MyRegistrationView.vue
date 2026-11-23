<script setup lang="ts">
import StatusTag from "@/core/ui/StatusTag.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import Button from "primevue/button";
import Checkbox from "primevue/checkbox";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { formatDate, formatMoney } from "@/core/format";
import { type CurriculumCourse, type RegistrationState, myRegistration, saveCourses, submitRegistration } from "./api";

const toast = useToast();
const state = ref<RegistrationState | null>(null);
const loadError = ref("");
const busy = ref(false);
const chosen = ref<string[]>([]);
const showOther = ref(false);

function adopt(next: RegistrationState) {
  state.value = next;
  const year = next.year_of_study ?? 1;
  // a saved registration's courses; otherwise the year's courses, ready to submit
  chosen.value = next.registration?.courses.length
    ? [...next.registration.courses]
    : (next.courses ?? []).filter((c) => c.year === year).map((c) => c.course);
}

onMounted(async () => {
  try {
    adopt(await myRegistration());
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : String(e);
  }
});

const period = computed(() => state.value?.period ?? null);
const registration = computed(() => state.value?.registration ?? null);
const editable = computed(
  () => Boolean(period.value) && ["open", "late"].includes(period.value!.state) && (!registration.value || ["Draft", "Returned"].includes(registration.value.status)),
);
const year = computed(() => state.value?.year_of_study ?? 1);
const yearCourses = computed(() => (state.value?.courses ?? []).filter((c) => c.year === year.value));
const otherCourses = computed(() => (state.value?.courses ?? []).filter((c) => c.year !== year.value));
const credits = computed(() =>
  (state.value?.courses ?? []).filter((c) => chosen.value.includes(c.course)).reduce((sum, c) => sum + c.credits, 0),
);
const overLimit = computed(() => Boolean(state.value?.max_credits) && credits.value > state.value!.max_credits!);
const blocked = computed(() => (state.value?.blockers?.length ?? 0) > 0);
const locked = (c: CurriculumCourse) => c.required && c.year === year.value;

async function act(run: () => Promise<RegistrationState>, message: string) {
  busy.value = true;
  try {
    adopt(await run());
    toast.add({ severity: "success", summary: message, life: 3000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not done", detail: e instanceof Error ? e.message : String(e), life: 9000 });
  } finally {
    busy.value = false;
  }
}

async function submit() {
  busy.value = true;
  try {
    // the choice is saved first, then submitted
    await saveCourses(chosen.value);
    adopt(await submitRegistration());
    toast.add({ severity: "success", summary: "Registration submitted", life: 4000 });
  } catch (e) {
    toast.add({ severity: "error", summary: "Not submitted", detail: e instanceof Error ? e.message : String(e), life: 9000 });
  } finally {
    busy.value = false;
  }
}

const headerLine = computed(() => {
  const p = period.value;
  if (!p || !state.value) return undefined;
  const when = {
    upcoming: `opens ${formatDate(p.opens_on)}`,
    open: `closes ${formatDate(p.closes_on)}`,
    late: `late registration until ${formatDate(p.late_until)}`,
    closed: "closed",
  }[p.state];
  return `${state.value.programme} · year ${year.value} · ${when}`;
});
</script>

<template>
  <section class="registration">
    <div v-if="!state && !loadError" class="loading"><ProgressSpinner style="width: 2.5rem; height: 2.5rem" aria-label="Loading" /></div>
    <Message v-else-if="loadError" severity="error" :closable="false">{{ loadError }}</Message>

    <template v-else-if="state">
      <PageHeader :title="period ? `Registration ${period.academic_year}` : 'Registration'" :subtitle="headerLine">
        <template #actions>
          <StatusTag v-if="registration" kind="registration" :value="registration.status" />
          <StatusTag v-else-if="period" kind="period" :value="period.state" />
        </template>
      </PageHeader>

      <Message v-if="!period" severity="info" :closable="false">There is no registration period at the moment.</Message>

      <template v-else>
        <Message v-if="registration?.status === 'Returned'" severity="warn" :closable="false">
          Returned by the faculty: {{ registration.review_note }}
        </Message>
        <Message v-else-if="registration?.status === 'Submitted'" severity="info" :closable="false">
          Submitted {{ formatDate(registration.submitted_on) }}. The faculty officer will review it.
        </Message>
        <Message v-else-if="registration?.status === 'Approved'" severity="success" :closable="false">
          Registered for {{ period.academic_year }}. Your fees for the year are on your statement.
        </Message>

        <article v-if="blocked && editable" class="card blockers">
          <h2>Before you can register</h2>
          <ul>
            <li v-for="b in state.blockers" :key="b">{{ b }}</li>
          </ul>
          <p class="sub">Pay by EFT with your student number as the reference. Payments can take a few working days to show.</p>
        </article>

        <article v-if="period.state === 'late' && editable" class="card late">
          A late registration fee of {{ formatMoney(period.late_fee) }} is added to your fees.
        </article>

        <article class="card">
          <div class="courses-head">
            <h2>Year {{ year }} courses</h2>
            <span class="sub" :class="{ over: overLimit }">
              {{ credits }} credits<template v-if="state.max_credits"> of {{ state.max_credits }}</template>
            </span>
          </div>
          <label v-for="c in yearCourses" :key="c.course" class="course">
            <Checkbox v-model="chosen" :value="c.course" :disabled="!editable || locked(c)" :input-id="`c-${c.course}`" />
            <span class="name">{{ c.course_name }} <span class="sub">{{ c.code }} · {{ c.semester === "Year" ? "Full year" : c.semester }}</span></span>
            <span class="sub">{{ c.credits }} cr</span>
          </label>

          <template v-if="otherCourses.length && editable">
            <Button
              :label="showOther ? 'Hide other courses' : 'Add a course from another year'"
              text
              size="small"
              class="toggle"
              @click="showOther = !showOther"
            />
            <template v-if="showOther">
              <label v-for="c in otherCourses" :key="c.course" class="course">
                <Checkbox v-model="chosen" :value="c.course" :input-id="`c-${c.course}`" />
                <span class="name">{{ c.course_name }} <span class="sub">{{ c.code }} · year {{ c.year }}</span></span>
                <span class="sub">{{ c.credits }} cr</span>
              </label>
            </template>
          </template>
          <template v-else-if="!editable">
            <label v-for="c in otherCourses.filter((o) => chosen.includes(o.course))" :key="c.course" class="course">
              <Checkbox v-model="chosen" :value="c.course" disabled :input-id="`c-${c.course}`" />
              <span class="name">{{ c.course_name }} <span class="sub">{{ c.code }} · year {{ c.year }}</span></span>
              <span class="sub">{{ c.credits }} cr</span>
            </label>
          </template>
        </article>

        <!-- the year's fees; when something blocks registration, the card above already says what is owed -->
        <article v-if="state.fees && !(blocked && editable)" class="card fees">
          <div><span class="sub">Fees {{ period.academic_year }}</span><strong>{{ formatMoney(state.fees.year) }}</strong></div>
          <div v-if="state.fees.deposit_required">
            <span class="sub">Deposit</span>
            <strong v-if="state.fees.paid_in_advance >= state.fees.deposit_required">{{ formatMoney(state.fees.deposit_required) }} paid</strong>
            <strong v-else>{{ formatMoney(state.fees.paid_in_advance) }} of {{ formatMoney(state.fees.deposit_required) }}</strong>
          </div>
          <div><span class="sub">Owed from earlier</span><strong>{{ formatMoney(state.fees.outstanding) }}</strong></div>
        </article>

        <div v-if="editable" class="actions">
          <Button label="Save" severity="secondary" outlined :disabled="busy" @click="act(() => saveCourses(chosen), 'Saved')" />
          <Button label="Submit registration" :loading="busy" :disabled="blocked || overLimit || !chosen.length" @click="submit" />
        </div>
      </template>
    </template>
  </section>
</template>

<style scoped>
.registration {
  display: grid;
  gap: 1rem;
  max-width: 48rem;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

h2 {
  margin: 0 0 0.5rem;
  font-size: 1rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 400;
  color: #6b7280;
}


.blockers ul {
  margin: 0 0 0.5rem;
  padding-left: 1.1rem;
  color: #b45309;
}

.late {
  color: #b45309;
}

.courses-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.over {
  color: #b91c1c;
  font-weight: 600;
}

.course {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0;
  border-top: 1px solid #f3f4f6;
}

.name {
  flex: 1;
}

.toggle {
  margin-top: 0.5rem;
}

.fees {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 2rem;
}

.fees div {
  display: grid;
  gap: 0.15rem;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>
