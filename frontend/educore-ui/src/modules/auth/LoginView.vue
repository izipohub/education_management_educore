<script setup lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ApiError } from "@/core/api/client";
import { useSession } from "@/core/auth/session";
import { signInFor } from "@/core/auth/signInFor";
import { useBranding } from "@/core/branding";

const session = useSession();
const router = useRouter();
const route = useRoute();
const { branding } = useBranding();

const email = ref("");
const password = ref("");
const error = ref("");

/** what went wrong, in words for the person signing in (never a raw server message) */
function loginError(e: unknown): string {
  if (!(e instanceof ApiError)) return "Sign-in did not go through. Check your connection and try again.";
  if (e.status === 401) return "The email or password is not correct.";
  if (e.status === 429) return "Too many attempts. Wait a few minutes, then try again.";
  if (e.status >= 500 || e.status === 0) return "Sign-in did not go through. Please try again.";
  return e.message;
}
const busy = ref(false);

/** The university's colours, as CSS variables for this page */
const brandStyle = computed(() => ({
  "--brand-night": branding.value.background_color,
  "--brand-accent": branding.value.accent_color,
  "--brand-on-accent": branding.value.text_on_accent,
  "--brand-primary": branding.value.primary_color,
}));

async function signIn() {
  error.value = "";
  busy.value = true;
  try {
    await session.login(email.value.trim(), password.value);
    // signing in for Moodle: back to EduCore's sign-in server, which sends them on
    const onward = signInFor(route.query["redirect-to"], window.location.origin);
    if (onward) {
      window.location.assign(onward);
      return;
    }
    const redirect = typeof route.query.redirect === "string" && route.query.redirect.startsWith("/") ? route.query.redirect : "/";
    await router.replace(redirect);
  } catch (e) {
    error.value = loginError(e);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="login" :style="brandStyle">
    <section class="hero" aria-hidden="false">
      <p class="eyebrow">
        {{ branding.institution_name }} · <span class="accent">{{ branding.login_subtitle }}</span>
      </p>
      <h1>
        {{ branding.login_heading }} <span class="accent">{{ branding.login_heading_accent }}</span>
      </h1>
      <p v-if="branding.login_text" class="lead">{{ branding.login_text }}</p>
      <dl v-if="branding.facts.length" class="facts">
        <div v-for="[title, caption] in branding.facts" :key="title">
          <dt>{{ title }}</dt>
          <dd>{{ caption }}</dd>
        </div>
      </dl>
    </section>

    <section class="card" aria-labelledby="sign-in-title">
      <img :src="branding.logo_on_dark" :alt="branding.institution_name" class="logo" />
      <h2 id="sign-in-title">Sign in</h2>
      <p class="subtitle">{{ branding.institution_name }}</p>

      <form novalidate @submit.prevent="signIn">
        <label for="email">Email</label>
        <InputText id="email" v-model="email" type="email" autocomplete="username" required fluid :disabled="busy" />

        <label for="password">Password</label>
        <Password
          v-model="password"
          input-id="password"
          :feedback="false"
          toggle-mask
          fluid
          autocomplete="current-password"
          :disabled="busy"
        />

        <Message v-if="error" severity="error" :closable="false" class="error" role="alert">{{ error }}</Message>

        <Button type="submit" label="Sign in" :loading="busy" :disabled="!email || !password" fluid class="submit" />
      </form>
      <p class="apply-link">Applying to study? <RouterLink to="/apply">See programmes and apply</RouterLink></p>
    </section>
  </main>
</template>

<style scoped>
.login {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 420px);
  align-items: center;
  gap: 4rem;
  padding: 3rem clamp(1rem, 6vw, 6rem);
  color: #e5e7eb;
  background:
    radial-gradient(560px circle at 100% 15%, color-mix(in srgb, var(--brand-accent) 9%, transparent), transparent 70%),
    radial-gradient(480px circle at 0% 85%, color-mix(in srgb, var(--brand-primary) 45%, transparent), transparent 70%),
    var(--brand-night);
}

.eyebrow {
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: color-mix(in srgb, var(--brand-primary) 40%, white);
}

.accent {
  color: var(--brand-accent);
}

h1 {
  margin: 1.25rem 0 1.5rem;
  font-size: clamp(2.25rem, 4.2vw, 3.6rem);
  font-weight: 700;
  line-height: 1.08;
  letter-spacing: -0.02em;
  color: #fff;
}

.lead {
  max-width: 36rem;
  font-size: 1.1rem;
  line-height: 1.7;
  color: #c9d3e3;
}

.facts {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
  max-width: 36rem;
  margin: 2.5rem 0 0;
  padding-top: 1.5rem;
  border-top: 1px solid rgb(255 255 255 / 0.1);
}

.facts dt {
  font-weight: 700;
  color: #fff;
}

.facts dd {
  margin: 0.25rem 0 0;
  font-size: 0.75rem;
  color: #94a3b8;
}

.card {
  padding: 2rem;
  border: 1px solid rgb(255 255 255 / 0.1);
  border-radius: 1.25rem;
  background: color-mix(in srgb, color-mix(in srgb, var(--brand-night) 78%, var(--brand-primary)) 75%, transparent);
  backdrop-filter: blur(16px);
  box-shadow: 0 25px 50px -12px color-mix(in srgb, var(--brand-primary) 40%, transparent);
}

.logo {
  height: 40px;
  width: auto;
}

h2 {
  margin: 1.5rem 0 0.25rem;
  font-size: 1.35rem;
  color: #fff;
}

.subtitle {
  margin: 0 0 1.5rem;
  color: #9ca3af;
}

form {
  display: grid;
  gap: 0.5rem;
}

label {
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #d1d5db;
}

.error {
  margin-top: 0.75rem;
}

.apply-link {
  margin: 1.25rem 0 0;
  font-size: 0.875rem;
  color: #9ca3af;
}

.apply-link a {
  color: var(--brand-accent);
}

.submit {
  margin-top: 1.25rem;
  --p-button-primary-background: var(--brand-accent);
  --p-button-primary-border-color: var(--brand-accent);
  --p-button-primary-color: var(--brand-on-accent);
  --p-button-primary-hover-background: color-mix(in srgb, var(--brand-accent) 85%, black);
  --p-button-primary-hover-border-color: color-mix(in srgb, var(--brand-accent) 85%, black);
  --p-button-primary-hover-color: var(--brand-on-accent);
  font-weight: 600;
}

@media (max-width: 991px) {
  .login {
    grid-template-columns: minmax(0, 1fr);
    gap: 2rem;
    padding: 2rem 16px;
  }

  .hero {
    text-align: center;
  }

  h1 {
    margin-bottom: 0;
    font-size: clamp(1.75rem, 7vw, 2.5rem);
  }

  .lead,
  .facts {
    display: none;
  }
}
</style>
