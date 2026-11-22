import { createRouter, createWebHistory } from "vue-router";
import { useSession } from "@/core/auth/session";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/login",
      name: "login",
      component: () => import("@/modules/auth/LoginView.vue"),
      meta: { public: true, title: "Sign in" },
    },
    {
      path: "/",
      component: () => import("@/core/layouts/AppLayout.vue"),
      children: [
        { path: "", name: "home", component: () => import("@/modules/home/HomeView.vue"), meta: { title: "Home" } },
        {
          path: "admissions",
          name: "admissions",
          component: () => import("@/modules/admissions/AdmissionsView.vue"),
          meta: { title: "Admissions", roles: ["Admissions Officer", "Registrar"] },
        },
        {
          path: "enrolment",
          name: "enrolment",
          component: () => import("@/modules/registry/EnrolmentView.vue"),
          meta: { title: "Enrolment", roles: ["Registry Officer", "Registrar"] },
        },
      ],
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  const session = useSession();
  if (!session.loaded) await session.load();

  if (to.meta.public) {
    // a signed-in user has no business on the login page
    return to.name === "login" && session.isSignedIn ? { name: "home" } : true;
  }
  if (!session.isSignedIn) {
    return { name: "login", query: to.fullPath !== "/" ? { redirect: to.fullPath } : {} };
  }
  // a screen for other roles: home instead (the server refuses its data anyway)
  if (to.meta.roles && !session.hasRole(...to.meta.roles)) {
    return { name: "home" };
  }
  return true;
});

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · EduCore` : "EduCore";
});

declare module "vue-router" {
  interface RouteMeta {
    public?: boolean;
    title?: string;
    /** shown to users with any of these roles */
    roles?: string[];
  }
}
