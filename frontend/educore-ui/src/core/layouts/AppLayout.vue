<script setup lang="ts">
import {
  BookOpen,
  ClipboardCheck,
  FileText,
  GraduationCap,
  House,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
  Settings,
  UserCheck,
  UserPlus,
} from "@lucide/vue";
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import { type Component, computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useSession } from "@/core/auth/session";
import { useBranding } from "@/core/branding";
import { REGISTRATION_ROLES } from "@/modules/registration/groups";

const session = useSession();
const router = useRouter();
const route = useRoute();
/** queues fill the window (list and record side by side); other screens scroll as a page */
const fill = computed(() => Boolean(route.meta.fill));
const { branding } = useBranding();

/** the menu folds to its icons; remembered on this browser */
const COLLAPSED_KEY = "ec-sidebar-collapsed";
function readCollapsed() {
  try {
    return localStorage.getItem(COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}
const collapsed = ref(readCollapsed());
watch(collapsed, (value) => {
  try {
    localStorage.setItem(COLLAPSED_KEY, value ? "1" : "0");
  } catch {
    // private browsing: the choice lasts for this visit
  }
});

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
  { label: "Registration", icon: UserCheck, to: "/registrations", roles: REGISTRATION_ROLES },
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

    <div class="body" :class="{ collapsed }">
      <nav class="sidebar" aria-label="Main">
        <!-- a list stays marked while one of its records is open; Home only on itself -->
        <RouterLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :active-class="item.to === '/' ? '' : 'active'"
          exact-active-class="active"
          :title="collapsed ? item.label : undefined"
        >
          <component :is="item.icon" :size="18" :stroke-width="1.75" aria-hidden="true" />
          <span class="label">{{ item.label }}</span>
        </RouterLink>
        <button
          type="button"
          class="nav-item fold"
          :aria-label="collapsed ? 'Expand the menu' : 'Collapse the menu'"
          :title="collapsed ? 'Expand the menu' : 'Collapse the menu'"
          :aria-expanded="!collapsed"
          @click="collapsed = !collapsed"
        >
          <component :is="collapsed ? PanelLeftOpen : PanelLeftClose" :size="18" :stroke-width="1.75" aria-hidden="true" />
          <span class="label">Collapse</span>
        </button>
      </nav>
      <main class="content" :class="{ fill }">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
/* the top bar and the menu stay put; only the content scrolls */
.shell {
  height: 100vh;
  height: 100dvh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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
  border-bottom: 1px solid var(--ec-second-line);
  box-shadow: 0 1px 0 rgb(0 0 0 / 0.25);
  position: relative;
  z-index: 2;
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
  min-height: 0;
  display: grid;
  grid-template-columns: 228px minmax(0, 1fr);
  transition: grid-template-columns 0.18s ease;
}

.body.collapsed {
  grid-template-columns: 4.25rem minmax(0, 1fr);
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.75rem;
  overflow-x: hidden;
  overflow-y: auto;
  background: var(--ec-second);
  border-right: 1px solid var(--ec-second-line);
}

.label {
  min-width: 0;
}

.collapsed .label {
  display: none;
}

.collapsed .nav-item {
  justify-content: center;
  padding-left: 0;
  padding-right: 0;
}

/* the fold button sits at the foot of the menu, set off by a line */
.fold {
  margin-top: auto;
  padding-top: 0.75rem;
  border: 0;
  border-top: 1px solid var(--ec-second-line);
  border-radius: 0;
  background: none;
  font: inherit;
  font-size: 0.9rem;
  cursor: pointer;
}

.fold:hover {
  background: none;
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
  min-height: 0;
  overflow-y: auto;
}

.content.fill {
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

  .body,
  .body.collapsed {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
  }

  .sidebar {
    display: flex;
    gap: 0.25rem;
    flex-direction: row;
    overflow-x: auto;
    overflow-y: hidden;
    border-right: 0;
    border-bottom: 1px solid var(--ec-second-line);
  }

  /* a phone's menu is a row of tabs: always labelled, no fold button */
  .collapsed .label {
    display: inline;
  }

  .fold {
    display: none;
  }

  .nav-item {
    flex: none;
  }

  .nav-item.active::before {
    display: none;
  }
}
</style>
