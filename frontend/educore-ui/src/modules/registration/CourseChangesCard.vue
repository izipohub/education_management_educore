<script setup lang="ts">
import Checkbox from "primevue/checkbox";
import InputText from "primevue/inputtext";
import { useToast } from "primevue/usetoast";
import { computed, onMounted, ref } from "vue";
import { formatDate } from "@/core/format";
import EcButton from "@/core/ui/EcButton.vue";
import EcPanel from "@/core/ui/EcPanel.vue";
import StatusTag from "@/core/ui/StatusTag.vue";
import { type ChangeCourse, type MyChanges, myChanges, requestChange } from "./courseChanges";

/**
 * Course changes after an approved registration: drop a registered course or add one from the programme, until
 * the year's course change date; the faculty officer approves. Emits "changed" once a change is approved at once
 * (no faculty approval), so the registration above shows the new courses.
 */
const emit = defineEmits<{ changed: [] }>();
const toast = useToast();
const state = ref<MyChanges | null>(null);
const drop = ref<string[]>([]);
const add = ref<string[]>([]);
const reason = ref("");
const busy = ref(false);

async function load() {
  state.value = await myChanges();
  drop.value = [];
  add.value = [];
  reason.value = "";
}
onMounted(() => void load().catch(() => (state.value = null)));

const courses = computed(() => state.value?.registration?.courses ?? []);
const registered = computed(() => courses.value.filter((c) => c.registered));
const addable = computed(() => courses.value.filter((c) => !c.registered && c.state !== "passed"));
const pending = computed(() => state.value?.changes.some((c) => c.status === "Submitted") ?? false);
const canAsk = computed(() => Boolean(state.value?.open) && !pending.value);
const credits = computed(
  () =>
    registered.value.filter((c) => !drop.value.includes(c.course)).reduce((t, c) => t + c.credits, 0) +
    addable.value.filter((c) => add.value.includes(c.course)).reduce((t, c) => t + c.credits, 0),
);
const overLimit = computed(() => Boolean(state.value?.max_credits) && credits.value > (state.value?.max_credits ?? 0));
const why = (c: ChangeCourse) => (c.state === "blocked" ? `Needs ${c.missing.join(", ")} passed first` : c.state === "repeat" ? "Not passed earlier" : `Year ${c.year}`);

async function ask() {
  busy.value = true;
  try {
    const before = state.value?.changes.length ?? 0;
    state.value = await requestChange(add.value, drop.value, reason.value.trim());
    const latest = state.value.changes[0];
    toast.add({ severity: "success", summary: latest?.status === "Approved" ? "Courses changed" : "Sent to the faculty", life: 3000 });
    if (latest?.status === "Approved" && state.value.changes.length > before) emit("changed");
    drop.value = [];
    add.value = [];
    reason.value = "";
  } catch (e) {
    toast.add({ severity: "error", summary: "Not sent", detail: e instanceof Error ? e.message : String(e), life: 8000 });
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <EcPanel
    v-if="state?.registration && (state.changes_until || state.changes.length)"
    title="Course changes"
    :note="state.open ? `Until ${formatDate(state.changes_until)}` : 'Closed'"
  >
    <template v-if="canAsk">
      <p class="group-label">Drop</p>
      <label v-for="c in registered" :key="c.course" class="course">
        <Checkbox v-model="drop" :value="c.course" :disabled="c.required && c.year === state.registration.year_of_study" :input-id="`drop-${c.course}`" />
        <span class="name">{{ c.course_name }} <span class="sub">{{ c.code }}<template v-if="c.required && c.year === state.registration.year_of_study"> · required this year</template></span></span>
        <span class="sub">{{ c.credits }} cr</span>
      </label>
      <template v-if="addable.length">
        <p class="group-label">Add</p>
        <label v-for="c in addable" :key="c.course" class="course" :class="{ blocked: c.state === 'blocked' }">
          <Checkbox v-model="add" :value="c.course" :disabled="c.state === 'blocked'" :input-id="`add-${c.course}`" />
          <span class="name">{{ c.course_name }} <span class="sub">{{ c.code }} · {{ why(c) }}</span></span>
          <span class="sub">{{ c.credits }} cr</span>
        </label>
      </template>
      <div class="ask">
        <InputText v-model="reason" placeholder="Reason (optional)" aria-label="Reason" fluid size="small" />
        <span class="sub" :class="{ over: overLimit }">{{ credits }} credits<template v-if="state.max_credits"> of {{ state.max_credits }}</template></span>
        <EcButton label="Send to the faculty" variant="primary" size="sm" :loading="busy" :disabled="(!add.length && !drop.length) || overLimit" @click="ask" />
      </div>
    </template>

    <ul v-if="state.changes.length" class="history">
      <li v-for="c in state.changes" :key="c.name">
        <div class="line">
          <span>{{ c.items.map((i) => `${i.action} ${i.course_name}`).join(" · ") }}</span>
          <StatusTag kind="change" :value="c.status" />
        </div>
        <div class="sub">
          {{ formatDate(c.submitted_on) }}<template v-if="c.reason"> · {{ c.reason }}</template>
          <template v-if="c.review_note"> · Faculty: {{ c.review_note }}</template>
        </div>
      </li>
    </ul>
  </EcPanel>
</template>

<style scoped>
.group-label {
  margin: 0.5rem 0 0.25rem;
  color: var(--ec-muted);
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.course {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0;
  border-top: 1px solid var(--ec-border);
}

.course.blocked .name {
  color: var(--ec-muted);
}

.name {
  flex: 1;
}

.sub {
  color: var(--ec-muted);
  font-size: 0.75rem;
}

.sub.over {
  color: var(--ec-danger, #b42318);
  font-weight: 600;
}

.ask {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 0.75rem;
}

.ask :deep(.p-inputtext) {
  flex: 1;
}

.history {
  display: grid;
  gap: 0.6rem;
  margin: 0.75rem 0 0;
  padding: 0.75rem 0 0;
  border-top: 1px solid var(--ec-border);
  list-style: none;
}

.line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
</style>
