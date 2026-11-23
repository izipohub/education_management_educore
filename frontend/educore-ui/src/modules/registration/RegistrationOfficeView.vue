<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import EnrolmentView from "@/modules/registry/EnrolmentView.vue";
import RegistrationsView from "./RegistrationsView.vue";
import { type Group, allowedGroups, pickGroup } from "./groups";

/** Registration: first-year and senior students under one menu item, the group in the address */
const route = useRoute();
const router = useRouter();
const groups = allowedGroups();
const group = computed<Group>({
  get: () => pickGroup(route.query.group),
  // a new group starts from its own defaults (tab, year)
  set: (value) => void router.replace({ query: { group: value } }),
});
const switchable = computed(() => groups.length > 1);
</script>

<template>
  <EnrolmentView v-if="group === 'first-year'" :key="group" v-model:group="group" :groups="switchable ? groups : []" />
  <RegistrationsView v-else :key="group" v-model:group="group" :groups="switchable ? groups : []" />
</template>
