<script setup lang="ts">
import Avatar from "primevue/avatar";
import Button from "primevue/button";
import { computed } from "vue";
import { useRouter } from "vue-router";
import { useSession } from "@/core/auth/session";
import { useBranding } from "@/core/branding";

const session = useSession();
const router = useRouter();
const { branding } = useBranding();

interface NavItem {
  label: string;
  icon: string;
  to: string;
  /** shown to users with any of these roles; omitted: everyone */
  roles?: string[];
}

/** Everyone but students (whose home is My studies) */
const STAFF_HOME = ["University Staff", "Applicant", "Sponsor", "Guardian", "External Examiner", "System Manager"];

/** Each module adds its entry here as it is built; the server still checks every request */
const NAV: NavItem[] = [
  { label: "Home", icon: "⌂", to: "/", roles: STAFF_HOME },
  { label: "My studies", icon: "☰", to: "/my-studies", roles: ["Student"] },
  { label: "Admissions", icon: "✎", to: "/admissions", roles: ["Admissions Officer", "Registrar"] },
  { label: "Enrolment", icon: "✓", to: "/enrolment", roles: ["Registry Officer", "Registrar"] },
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
        <img :src="branding.logo" :alt="branding.institution_name" />
      </RouterLink>
      <div class="user">
        <div class="who">
          <span class="name">{{ session.me?.full_name }}</span>
          <span class="positions">{{ session.me?.positions.join(", ") }}</span>
        </div>
        <Avatar :label="initials" shape="circle" :image="session.me?.user_image || undefined" />
        <Button label="Sign out" severity="secondary" text size="small" @click="signOut" />
      </div>
    </header>

    <div class="body">
      <nav class="sidebar" aria-label="Main">
        <RouterLink v-for="item in nav" :key="item.to" :to="item.to" class="nav-item" active-class="" exact-active-class="active">
          <span aria-hidden="true">{{ item.icon }}</span>
          {{ item.label }}
        </RouterLink>
      </nav>
      <main class="content">
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.75rem 1.5rem;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
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
  color: #6b7280;
}

.body {
  flex: 1;
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
}

.sidebar {
  padding: 1rem 0.75rem;
  background: #fff;
  border-right: 1px solid #e5e7eb;
}

.nav-item {
  display: flex;
  gap: 0.6rem;
  padding: 0.55rem 0.75rem;
  border-radius: 0.5rem;
  color: #374151;
  text-decoration: none;
}

.nav-item:hover {
  background: #f3f4f6;
}

.nav-item.active {
  background: color-mix(in srgb, var(--color-brand-navy) 10%, white);
  color: var(--color-brand-navy);
  font-weight: 600;
}

.content {
  padding: 2rem clamp(16px, 3vw, 2.5rem);
  min-width: 0;
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
    overflow-x: auto;
    border-right: 0;
    border-bottom: 1px solid #e5e7eb;
  }
}
</style>
