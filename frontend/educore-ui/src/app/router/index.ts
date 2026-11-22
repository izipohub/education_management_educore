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
    // applying: open to anyone
    {
      path: "/apply",
      name: "apply",
      component: () => import("@/modules/apply/ApplyLandingView.vue"),
      meta: { public: true, title: "Apply" },
    },
    {
      path: "/apply/register",
      name: "register",
      component: () => import("@/modules/apply/RegisterView.vue"),
      meta: { public: true, title: "Create an account" },
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
          path: "application",
          name: "application",
          component: () => import("@/modules/apply/ApplicationView.vue"),
          meta: { title: "My application", roles: ["Applicant"] },
        },
        {
          path: "my-studies",
          name: "my-studies",
          component: () => import("@/modules/student/MyStudiesView.vue"),
          meta: { title: "My studies", roles: ["Student"] },
        },
        {
          path: "my-teaching",
          name: "my-teaching",
          component: () => import("@/modules/teaching/MyTeachingView.vue"),
          meta: { title: "My teaching", roles: ["Lecturer"] },
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
    return (to.name === "login" || to.name === "register") && session.isSignedIn ? { name: "home" } : true;
  }
  if (!session.isSignedIn) {
    return { name: "login", query: to.fullPath !== "/" ? { redirect: to.fullPath } : {} };
  }
  // a screen for other roles: home instead (the server refuses its data anyway)
  if (to.meta.roles && !session.hasRole(...to.meta.roles)) {
    return { name: "home" };
  }
  // a student's home is their own studies; an applicant's, their application
  if (to.name === "home" && session.isStudent) {
    return { name: "my-studies" };
  }
  if (to.name === "home" && session.hasRole("Applicant") && !session.hasRole("University Staff")) {
    return { name: "application" };
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
