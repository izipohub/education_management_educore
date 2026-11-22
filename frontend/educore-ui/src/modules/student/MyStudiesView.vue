<script setup lang="ts">
import PageHeader from "@/core/ui/PageHeader.vue";
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Tag from "primevue/tag";
import { computed, onMounted, ref } from "vue";
import { formatDate, formatMoney } from "@/core/format";
import { type StudentOverview, getOverview } from "./api";

const data = ref<StudentOverview | null>(null);
const error = ref("");

onMounted(async () => {
  try {
    data.value = await getOverview();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
});

const current = computed(() => data.value?.enrolments[0] ?? null);
const totalCredits = computed(() => current.value?.courses.reduce((sum, c) => sum + (c.credits ?? 0), 0) ?? 0);

const feeStatus = computed(() => {
  const fees = data.value?.fees;
  if (!fees) return null;
  if (fees.overdue > 0) return { severity: "danger", label: `${formatMoney(fees.overdue)} overdue` };
  if (fees.owing > 0) return { severity: "warn", label: `Due ${formatDate(fees.next_due)}` };
  return { severity: "success", label: "Paid up" };
});
</script>

<template>
  <section class="my-studies">
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-else-if="!data" class="loading"><ProgressSpinner style="width: 2.5rem; height: 2.5rem" aria-label="Loading" /></div>

    <template v-else>
      <PageHeader :title="data.student.name" :subtitle="[`Student number ${data.student.number}`, data.student.campus].filter(Boolean).join(' · ')" />

      <div class="cards">
        <article v-if="current" class="card programme">
          <h2>Programme</h2>
          <p class="big">{{ current.program }}</p>
          <p class="sub">
            {{ current.qualification }}<template v-if="current.nqf_level"> · NQF level {{ current.nqf_level }}</template>
          </p>
          <dl class="facts">
            <div><dt>Offering</dt><dd>{{ current.offering }}</dd></div>
            <div><dt>Mode</dt><dd>{{ current.mode_of_study }}</dd></div>
            <div><dt>Academic year</dt><dd>{{ current.academic_year }}</dd></div>
            <div><dt>Enrolled from</dt><dd>{{ formatDate(current.enrollment_date) }}</dd></div>
          </dl>
        </article>
        <article v-else class="card">
          <h2>Programme</h2>
          <p class="sub">You are not enrolled on a programme yet.</p>
        </article>

        <article class="card fees">
          <h2>Fees</h2>
          <p class="big">{{ formatMoney(data.fees.owing) }}</p>
          <p class="sub">owing of {{ formatMoney(data.fees.billed) }} billed</p>
          <Tag v-if="feeStatus" :severity="feeStatus.severity" :value="feeStatus.label" />
        </article>
      </div>

      <section v-if="current" class="block">
        <h2>Courses this year <span class="sub">({{ current.courses.length }} courses, {{ totalCredits }} credits)</span></h2>
        <DataTable :value="current.courses" data-key="course" class="table" size="small">
          <Column field="code" header="Code" />
          <Column field="course" header="Course" />
          <Column field="credits" header="Credits" />
          <Column header="NQF level">
            <template #body="{ data: course }">{{ course.nqf_level ?? "" }}</template>
          </Column>
        </DataTable>
      </section>

      <section class="block">
        <h2>Fee statement</h2>
        <DataTable :value="data.fees.entries" data-key="reference" class="table" size="small">
          <template #empty><p class="empty">No fees charged yet.</p></template>
          <Column header="Date">
            <template #body="{ data: entry }"><span class="nowrap">{{ formatDate(entry.date) }}</span></template>
          </Column>
          <Column header="Description">
            <template #body="{ data: entry }">
              {{ entry.description }}
              <div class="sub">{{ entry.reference }}</div>
            </template>
          </Column>
          <Column header="Charged" header-class="num" body-class="num">
            <template #body="{ data: entry }">
              <span v-if="entry.amount > 0" class="nowrap">{{ formatMoney(entry.amount) }}</span>
            </template>
          </Column>
          <Column header="Paid" header-class="num" body-class="num">
            <template #body="{ data: entry }">
              <span v-if="entry.amount < 0" class="nowrap paid">{{ formatMoney(-entry.amount) }}</span>
            </template>
          </Column>
          <Column header="Balance" header-class="num" body-class="num">
            <template #body="{ data: entry }"><strong class="nowrap">{{ formatMoney(entry.balance) }}</strong></template>
          </Column>
        </DataTable>
      </section>
    </template>
  </section>
</template>

<style scoped>
.loading {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.head h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 400;
  color: #6b7280;
}

.cards {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(0, 1fr);
  gap: 1rem;
  margin: 1.5rem 0;
}


.card h2,
.block h2 {
  margin: 0 0 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #6b7280;
}

.big {
  margin: 0 0 0.25rem;
  font-size: 1.25rem;
  font-weight: 600;
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9rem, 1fr));
  gap: 0.75rem;
  margin: 1rem 0 0;
}

.facts dt {
  font-size: 0.75rem;
  color: #6b7280;
}

.facts dd {
  margin: 0.15rem 0 0;
}

.fees :deep(.p-tag) {
  margin-top: 0.75rem;
}

.block {
  margin-bottom: 1.5rem;
}

.table {
  width: 100%;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
  overflow: hidden;
}

.table :deep(table) {
  width: 100%;
}

:deep(.num) {
  text-align: right;
}

:deep(th.num .p-datatable-column-header-content) {
  justify-content: flex-end;
}

.nowrap {
  white-space: nowrap;
}

.paid {
  color: #15803d;
}

.empty {
  margin: 1rem 0;
  text-align: center;
  color: #6b7280;
}

@media (max-width: 767px) {
  .cards {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
