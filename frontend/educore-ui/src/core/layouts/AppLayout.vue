<script setup lang="ts">
import {
  BookOpen,
  ClipboardCheck,
  FileText,
  GraduationCap,
  House,
  ListChecks,
  LogOut,
  Settings,
  UserCheck,
  UserPlus,
} from "@lucide/vue";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import { type Component, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useSession } from "@/core/auth/session";
import { useBranding } from "@/core/branding";

const session = useSession();
const router = useRouter();
const route = useRoute();
/** queues fill the window (list and record side by side); other screens scroll as a page */
const fill = computed(() => Boolean(route.meta.fill));
const { branding } = useBranding();

interface NavItem {
  label: string;
  icon: Component;
  to: string;
  /** shown to users with any of these roles; omitted: everyone */
  roles?: string[];
}

/** Everyone but students (whose home is My studies) */
const STAFF_HOME = ["University Staff", "Sponsor", "Guardian", "External Examiner", "System Manager"];

/** Each module adds its entry here as it is built; the server still checks every request */
const NAV: NavItem[] = [
  { label: "Home", icon: House, to: "/", roles: STAFF_HOME },
  { label: "My application", icon: FileText, to: "/application", roles: ["Applicant"] },
  { label: "My studies", icon: BookOpen, to: "/my-studies", roles: ["Student"] },
  { label: "Registration", icon: ClipboardCheck, to: "/registration", roles: ["Student"] },
  { label: "My teaching", icon: GraduationCap, to: "/my-teaching", roles: ["Lecturer"] },
  { label: "Admissions", icon: UserPlus, to: "/admissions", roles: ["Admissions Officer", "Registrar"] },
  { label: "Enrolment", icon: UserCheck, to: "/enrolment", roles: ["Registry Officer", "Registrar"] },
  { label: "Registrations", icon: ListChecks, to: "/registrations", roles: ["Faculty Officer", "Registrar"] },
  { label: "Admission setup", icon: Settings, to: "/admission-setup", roles: ["Registrar", "System Manager"] },
];

const nav = computed(() => NAV.filter((item) => !item.roles || session.hasRole(...item.roles)));
const initials = computed(() =>
  (session.me?.full_name ?? "")
    .split(/\s+/)
    // words only: "Registrar (demo)" is "R", not "R("
    .filter((part) => /^\p{L}/u.test(part))
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase(),
);

async function signOut() {
  await session.logout();
  await router.replace({ name: "login" });
}
</script>

<template>
  <div class="shell">
    <header class="topbar">
      <RouterLink to="/" class="brand">
        <img :src="branding.logo_on_dark || branding.logo" :alt="branding.institution_name" />
      </RouterLink>
      <div class="user">
        <div class="who">
          <span class="name">{{ session.me?.full_name }}</span>
          <span class="positions">{{ session.me?.positions.join(", ") }}</span>
        </div>
        <Avatar :label="initials" shape="circle" :image="session.me?.user_image || undefined" />
        <Button severity="secondary" text size="small" aria-label="Sign out" title="Sign out" @click="signOut">
          <LogOut :size="18" aria-hidden="true" />
        </Button>
      </div>
    </header>

    <div class="body">
      <nav class="sidebar" aria-label="Main">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-item" active-class="" exact-active-class="active">
          <component :is="item.icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
          {{ item.label }}
        </RouterLink>
      </nav>
      <main class="content" :class="{ fill }">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: var(--ec-topbar-height);
  box-sizing: border-box;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.5rem;
  background: var(--ec-second);
  color: var(--ec-on-second);
}

.topbar :deep(.p-button) {
  color: var(--ec-on-second-muted);
}

.topbar :deep(.p-avatar) {
  background: var(--ec-second-raised);
  color: var(--ec-on-second);
}

.brand img {
  height: 34px;
  display: block;
}

.user {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.who {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.2;
}

.name {
  font-weight: 600;
}

.positions {
  font-size: 0.75rem;
  color: var(--ec-on-second-muted);
}

.body {
  flex: 1;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.75rem;
  background: var(--ec-second);
}

.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  font-size: 0.9rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--ec-radius-sm);
  color: var(--ec-on-second-muted);
  text-decoration: none;
}

.nav-item:hover {
  background: var(--ec-second-raised);
  color: var(--ec-on-second);
}

/* the loud accent marks where you are */
.nav-item.active {
  background: var(--ec-second-raised);
  color: var(--ec-on-second);
  font-weight: 600;
}

.nav-item.active::before {
  content: "";
  position: absolute;
  left: -0.75rem;
  top: 0.45rem;
  bottom: 0.45rem;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--ec-loud);
}

.nav-item.active svg {
  color: var(--ec-loud);
}

.content {
  padding: 1.5rem clamp(16px, 3vw, 2rem);
  min-width: 0;
}

.content.fill {
  height: calc(100vh - var(--ec-topbar-height));
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow: hidden;
}

@media (max-width: 767px) {
  .who {
    display: none;
  }

  .body {
    grid-template-columns: minmax(0, 1fr);
  }

  .sidebar {
    display: flex;
    gap: 0.25rem;
    flex-direction: row;
    overflow-x: auto;
  }
}
</style>
