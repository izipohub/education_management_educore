import { defineStore } from "pinia";
import { computed, ref } from "vue";
import { ApiError, get, post, setCsrfToken } from "@/core/api/client";
import type { Me } from "@/types/session";

/**
 * The signed-in user. Today this is Frappe's own session (email + password, an HttpOnly cookie); single
 * sign-on through OIDC is an open decision (AGENT.md 7, 14) and will replace login()/logout() here only.
 * Hiding screens by role is convenience: the server checks every request.
 */
export const useSession = defineStore("session", () => {
  const me = ref<Me | null>(null);
  const loaded = ref(false);

  const isSignedIn = computed(() => me.value !== null);
  const isStudent = computed(() => Boolean(me.value?.student));

  function hasRole(...roles: string[]) {
    return roles.some((role) => me.value?.roles.includes(role));
  }

  async function load() {
    try {
      const data = await get<Me>("educore.api.v1.session.me");
      me.value = data;
      setCsrfToken(data.csrf_token);
    } catch (error) {
      // a guest gets 403 from a login-only method: not signed in, not an error
      if (!(error instanceof ApiError) || (error.status !== 401 && error.status !== 403)) throw error;
      me.value = null;
      setCsrfToken(null);
    } finally {
      loaded.value = true;
    }
  }

  async function login(usr: string, pwd: string) {
    await post("login", { usr, pwd });
    await load();
    if (!me.value) throw new ApiError("Signed in, but the session could not be loaded. Try again.", 0, null);
  }

  async function logout() {
    try {
      await post("logout");
    } finally {
      me.value = null;
      setCsrfToken(null);
    }
  }

  return { me, loaded, isSignedIn, isStudent, hasRole, load, login, logout };
});
