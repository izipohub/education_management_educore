<script setup lang="ts">
import Button from "primevue/button";
import InputText from "primevue/inputtext";
import Message from "primevue/message";
import Password from "primevue/password";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useSession } from "@/core/auth/session";
import { useBranding } from "@/core/branding";
import { register } from "./api";

const router = useRouter();
const session = useSession();
const { branding } = useBranding();

const firstName = ref("");
const lastName = ref("");
const email = ref("");
const password = ref("");
const confirm = ref("");
const busy = ref(false);
const error = ref("");

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const mismatch = computed(() => Boolean(confirm.value) && confirm.value !== password.value);
const ready = computed(
  () =>
    firstName.value.trim() &&
    lastName.value.trim() &&
    EMAIL.test(email.value.trim()) &&
    password.value.length >= 8 &&
    password.value === confirm.value &&
    !busy.value,
);

async function createAccount() {
  if (!ready.value) return;
  busy.value = true;
  error.value = "";
  try {
    const { email: login } = await register({
      first_name: firstName.value.trim(),
      last_name: lastName.value.trim(),
      email: email.value.trim(),
      password: password.value,
    });
    await session.login(login, password.value);
    await router.replace({ name: "application" });
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e);
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <main class="register">
    <section class="card" aria-labelledby="register-title">
      <img :src="branding.logo" :alt="branding.institution_name" class="logo" />
      <h1 id="register-title">Create your applicant account</h1>
      <p class="sub">Use an email address you check: the university writes to you there.</p>

      <form novalidate @submit.prevent="createAccount">
        <div class="row">
          <div class="field">
            <label for="first-name">First name</label>
            <InputText id="first-name" v-model="firstName" autocomplete="given-name" fluid />
          </div>
          <div class="field">
            <label for="last-name">Last name</label>
            <InputText id="last-name" v-model="lastName" autocomplete="family-name" fluid />
          </div>
        </div>
        <div class="field">
          <label for="email">Email</label>
          <InputText id="email" v-model="email" type="email" autocomplete="email" fluid />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <Password v-model="password" input-id="password" toggle-mask fluid autocomplete="new-password" />
          <small class="sub">At least 8 characters; a longer passphrase is safer.</small>
        </div>
        <div class="field">
          <label for="confirm">Confirm password</label>
          <Password v-model="confirm" input-id="confirm" :feedback="false" toggle-mask fluid autocomplete="new-password" :invalid="mismatch" />
          <small v-if="mismatch" class="error-text">The passwords are not the same.</small>
        </div>

        <Message v-if="error" severity="error" :closable="false" role="alert">{{ error }}</Message>
        <Button type="submit" label="Create account" :loading="busy" :disabled="!ready" fluid class="submit" />
      </form>
      <p class="sub footer">Already have an account? <RouterLink to="/login">Sign in</RouterLink></p>
    </section>
  </main>
</template>

<style scoped>
.register {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 16px;
}

.card {
  width: min(32rem, 100%);
  padding: 2rem;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 1rem;
}

.logo {
  height: 34px;
}

h1 {
  margin: 1.25rem 0 0.25rem;
  font-size: 1.4rem;
}

.sub {
  margin: 0;
  font-size: 0.85rem;
  color: #6b7280;
}

form {
  display: grid;
  gap: 0.9rem;
  margin-top: 1.25rem;
}

.row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.9rem;
}

.field {
  display: grid;
  gap: 0.35rem;
}

label {
  font-size: 0.875rem;
}

.error-text {
  color: #b91c1c;
}

.submit {
  margin-top: 0.5rem;
}

.footer {
  margin-top: 1.25rem;
}

@media (max-width: 480px) {
  .row {
    grid-template-columns: 1fr;
  }
}
</style>
