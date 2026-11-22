<script setup lang="ts">
import Column from "primevue/column";
import DataTable from "primevue/datatable";
import Message from "primevue/message";
import ProgressSpinner from "primevue/progressspinner";
import Select from "primevue/select";
import Tag from "primevue/tag";
import { computed, onMounted, ref, watch } from "vue";
import { type MyClasses, getMyClasses } from "./api";

const data = ref<MyClasses | null>(null);
const error = ref("");
const academicYear = ref<string | undefined>();
let adoptingYear = false;

async function load() {
  error.value = "";
  try {
    data.value = await getMyClasses(academicYear.value);
    if (!academicYear.value && data.value.academic_year) {
      adoptingYear = true;
      academicYear.value = data.value.academic_year;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  }
}

watch(academicYear, () => {
  if (adoptingYear) {
    adoptingYear = false;
    return;
  }
  void load();
});
onMounted(load);

/** different people: a student in three of your classes counts once */
const totalStudents = computed(() => new Set(data.value?.classes.flatMap((c) => c.students.map((s) => s.student))).size);
</script>

<template>
  <section class="teaching">
    <header class="head">
      <div>
        <h1>My teaching</h1>
        <p v-if="data?.linked" class="intro">
          {{ data.classes.length }} classes · {{ totalStudents }} students
        </p>
      </div>
      <Select
        v-if="data?.linked && data.academic_years.length"
        v-model="academicYear"
        :options="data.academic_years"
        aria-label="Academic year"
        class="year"
      />
    </header>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div v-else-if="!data" class="loading"><ProgressSpinner style="width: 2.5rem; height: 2.5rem" aria-label="Loading" /></div>

    <Message v-else-if="!data.linked" severity="info" :closable="false">
      Your login is not yet linked to your staff record. Ask HR to link your Employee record to this login, and the
      faculty to add you to your courses.
    </Message>

    <p v-else-if="!data.classes.length" class="empty">You are not assigned to any course in {{ academicYear }}.</p>

    <article v-for="cls in data?.classes ?? []" :key="cls.name" class="class">
      <header class="class-head">
        <div>
          <h2>
            <span class="code">{{ cls.code }}</span> {{ cls.course }}
          </h2>
          <p class="sub">
            {{ cls.campus }} · {{ cls.academic_year }}
            <template v-if="cls.credits"> · {{ cls.credits }} credits</template>
            <template v-if="cls.nqf_level"> · NQF level {{ cls.nqf_level }}</template>
          </p>
          <p v-if="cls.co_lecturers.length" class="sub">With {{ cls.co_lecturers.join(", ") }}</p>
        </div>
        <Tag :value="`${cls.students.length} ${cls.students.length === 1 ? 'student' : 'students'}`" severity="secondary" />
      </header>
      <DataTable :value="cls.students" data-key="student" size="small" class="table">
        <template #empty><p class="empty">No students in this class.</p></template>
        <Column field="student_name" header="Student" />
        <Column field="student" header="Student number" />
        <Column header="Programme">
          <template #body="{ data: s }">
            {{ s.programme }}
            <div class="sub">{{ s.offering }} · {{ s.mode_of_study }}</div>
          </template>
        </Column>
      </DataTable>
    </article>
  </section>
</template>

<style scoped>
.head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

h1 {
  margin: 0 0 0.25rem;
  font-size: 1.6rem;
}

.intro,
.sub {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.year {
  min-width: 9rem;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 3rem;
}

.class {
  margin-bottom: 1rem;
  padding: 1.25rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 0.75rem;
}

.class-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.class-head h2 {
  margin: 0 0 0.25rem;
  font-size: 1.1rem;
}

.code {
  color: var(--color-brand-navy);
}

.table {
  width: 100%;
}

.table :deep(table) {
  width: 100%;
}

.empty {
  margin: 1rem 0;
  text-align: center;
  color: #6b7280;
}
</style>
