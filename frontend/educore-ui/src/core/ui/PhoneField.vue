<script setup lang="ts">
import InputText from "primevue/inputtext";
import Select from "primevue/select";
import { computed, ref, watch } from "vue";

/**
 * A phone number with its country's calling code: the code picked from a list (the home country's first), the
 * number typed beside it. The value is kept as +<code><number>, e.g. +264811234567; a number typed with its
 * trunk 0 (081 ...) drops the 0.
 */
const props = withDefaults(
  defineProps<{
    dialCodes: { country: string; code: string }[];
    /** the country picked when the value has no code yet */
    homeCountry?: string;
    inputId?: string;
    invalid?: boolean;
  }>(),
  { homeCountry: "Namibia", inputId: undefined, invalid: false },
);
const value = defineModel<string | null | undefined>({ default: "" });

const home = computed(() => props.dialCodes.find((d) => d.country === props.homeCountry));
const options = computed(() => {
  const rest = props.dialCodes.filter((d) => d.country !== props.homeCountry);
  return [...(home.value ? [home.value] : []), ...rest].map((d) => ({ ...d, label: `${d.country} ${d.code}` }));
});

const country = ref<string>("");
const number = ref("");

/** the value split into a country and the number after its code (the longest code that matches) */
function split(v: string | null | undefined) {
  const text = (v ?? "").replace(/[\s\-().]/g, "");
  if (!text.startsWith("+")) return { country: home.value?.country ?? "", number: text };
  const match = [...props.dialCodes]
    .filter((d) => text.startsWith(d.code.replace(/[\s-]/g, "")))
    .sort((a, b) => b.code.length - a.code.length || (a.country === props.homeCountry ? -1 : 1))[0];
  return match ? { country: match.country, number: text.slice(match.code.replace(/[\s-]/g, "").length) } : { country: home.value?.country ?? "", number: text };
}

/** set while this field writes the value, so its own change is not split back into the inputs */
let writing = false;
function join() {
  const digits = number.value.replace(/\D/g, "").replace(/^0/, "");
  const dial = props.dialCodes.find((d) => d.country === country.value)?.code.replace(/[\s-]/g, "") ?? "";
  const next = digits ? `${dial}${digits}` : "";
  if (next === (value.value ?? "")) return;
  writing = true;
  value.value = next;
}

function show() {
  const parts = split(value.value);
  country.value = parts.country;
  number.value = parts.number;
}
watch(value, () => {
  if (writing) {
    writing = false;
    return;
  }
  show();
});
// the codes arrive with the form's options
watch(() => props.dialCodes.length, show, { immediate: true });
const code = computed(() => props.dialCodes.find((d) => d.country === country.value)?.code ?? "");
</script>

<template>
  <div class="phone" :class="{ invalid }">
    <Select
      v-model="country"
      :options="options"
      option-label="label"
      option-value="country"
      filter
      filter-placeholder="Country or code"
      class="code"
      :aria-label="inputId ? `Country code for ${inputId}` : 'Country code'"
      :invalid="invalid"
      @change="join"
    >
      <template #value>{{ code || "Code" }}</template>
    </Select>
    <InputText :id="inputId" v-model="number" type="tel" inputmode="tel" autocomplete="tel-national" placeholder="81 123 4567" fluid :invalid="invalid" @update:model-value="join" />
  </div>
</template>

<style scoped>
.phone {
  display: grid;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  gap: 0.4rem;
}

.code {
  min-width: 0;
}
</style>
