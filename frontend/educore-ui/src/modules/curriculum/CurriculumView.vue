<script setup lang="ts">
import { Search } from "@lucide/vue";
import IconField from "primevue/iconfield";
import InputIcon from "primevue/inputicon";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import { computed, onMounted, ref } from "vue";
import DataTable, { type Column } from "@/core/ui/DataTable.vue";
import PageHeader from "@/core/ui/PageHeader.vue";
import { type ProgrammeRow, listProgrammes } from "./api";

/** The programmes whose curriculum this user may lay out; a row opens the programme's curriculum */
const rows = ref<ProgrammeRow[]>([]);
const loading = ref(true);
const error = ref("");
const search = ref("");

onMounted(async () => {
  try {
    rows.value = await listProgrammes();
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    loading.value = false;
  }
});

const shown = computed(() => {
  const q = search.value.trim().toLowerCase();
  const list = q ? rows.value.filter((r) => `${r.name} ${r.code} ${r.faculty}`.toLowerCase().includes(q)) : rows.value;
  return list as unknown as Record<string, unknown>[];
});
const row = (r: Record<string, unknown>) => r as unknown as ProgrammeRow;
const columns: Column[] = [
  { key: "name", label: "Programme" },
  { key: "faculty", label: "Faculty", wide: true },
  { key: "duration", label: "Years", align: "right", wide: true },
  { key: "courses", label: "Courses", align: "right" },
  { key: "credits", label: "Credits", align: "right", wide: true },
];
</script>

<template>
  <section class="list-page">
    <PageHeader title="Curriculum" subtitle="Each programme's courses by year of study and semester, as the faculties set them" />

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <DataTable
      :columns="columns"
      :rows="shown"
      row-key="name"
      :to="(r) => ({ name: 'curriculum-programme', params: { name: String(r.name) } })"
      :loading="loading"
      noun="programmes"
      empty-title="No programmes"
    >
      <template #toolbar>
        <IconField class="search">
          <InputIcon><Search :size="15" /></InputIcon>
          <InputText v-model="search" placeholder="Programme, code or faculty" aria-label="Search programmes" fluid size="small" />
        </IconField>
      </template>
      <template #cell-name="{ row: r }">
        <span class="who">{{ row(r).name }}</span>
        <span class="sub">{{ [row(r).code, row(r).qualification, row(r).nqf_level ? `NQF ${row(r).nqf_level}` : ""].filter(Boolean).join(" · ") }}</span>
      </template>
      <template #cell-duration="{ row: r }">{{ row(r).duration ?? "" }}</template>
      <template #cell-courses="{ row: r }">
        {{ row(r).courses }}
        <span v-if="(row(r).duration ?? 0) > row(r).years_laid_out" class="sub">{{ row(r).years_laid_out }} of {{ row(r).duration }} years</span>
      </template>
    </DataTable>
  </section>
</template>

<style scoped>
.list-page {
  display: grid;
  gap: 1rem;
}

.search {
  flex: 1;
  max-width: 22rem;
}

.who {
  display: block;
}

.sub {
  display: block;
  margin-top: 0.1rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 400;
  white-space: nowrap;
}
</style>
