import { createRouter, createWebHistory } from "vue-router";
import { useSession } from "@/core/auth/session";
import { CURRICULUM_ROLES } from "@/modules/curriculum/api";
import { FEE_SETTINGS_ROLES, FINANCE_ROLES } from "@/modules/finance/api";
import { EXAMINATION_ROLES } from "@/modules/examinations/api";
import { ICT_ROLES } from "@/modules/integrations/api";
import { ALLOCATION_ROLES } from "@/modules/teaching/allocation";
import { RECORD_ROLES } from "@/modules/records/api";
import { REGISTRATION_ROLES } from "@/modules/registration/groups";

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
          path: "admissions/new",
          name: "capture-application",
          component: () => import("@/modules/admissions/CaptureApplicationPage.vue"),
          meta: { title: "New paper application", roles: ["Admissions Officer", "Registrar"] },
        },
        {
          path: "admissions/:name",
          name: "application-record",
          component: () => import("@/modules/admissions/ApplicationPage.vue"),
          props: true,
          meta: { title: "Application", roles: ["Admissions Officer", "Registrar"] },
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
          path: "registration",
          name: "registration",
          component: () => import("@/modules/registration/MyRegistrationView.vue"),
          meta: { title: "Registration", roles: ["Student"] },
        },
        {
          path: "admission-setup",
          name: "admission-setup",
          component: () => import("@/modules/setup/AdmissionSetupView.vue"),
          meta: { title: "Admission setup", roles: ["Registrar", "System Manager"] },
        },
        {
          path: "admission-setup/:section(pathways|documents|programmes)/:name",
          name: "setup-item",
          component: () => import("@/modules/setup/SetupItemPage.vue"),
          props: true,
          meta: { title: "Admission setup", roles: ["Registrar", "System Manager"] },
        },
        // Registration: first-year students (registry) and senior students (faculty), one menu item
        {
          path: "registrations",
          name: "registrations",
          component: () => import("@/modules/registration/RegistrationOfficeView.vue"),
          meta: { title: "Registration", roles: REGISTRATION_ROLES },
        },
        {
          path: "registrations/first-year/:name",
          name: "enrolment-record",
          component: () => import("@/modules/registry/EnrolmentPage.vue"),
          props: true,
          meta: { title: "Registration", roles: ["Registry Officer", "Registrar"] },
        },
        {
          path: "registrations/senior/:name",
          name: "registration-record",
          component: () => import("@/modules/registration/RegistrationPage.vue"),
          props: true,
          meta: { title: "Registration", roles: ["Faculty Officer", "Registrar"] },
        },
        {
          path: "students",
          name: "students",
          component: () => import("@/modules/records/StudentsView.vue"),
          meta: { title: "Students", roles: RECORD_ROLES },
        },
        {
          path: "students/:name",
          name: "student-record",
          component: () => import("@/modules/records/StudentPage.vue"),
          props: true,
          meta: { title: "Student", roles: RECORD_ROLES },
        },
        {
          path: "registration-setup",
          name: "registration-setup",
          component: () => import("@/modules/setup/RegistrationSetupView.vue"),
          meta: { title: "Registration setup", roles: ["Registrar", "System Manager"] },
        },
        {
          path: "registration-setup/periods/:name",
          name: "registration-period",
          component: () => import("@/modules/setup/PeriodPage.vue"),
          props: true,
          meta: { title: "Registration setup", roles: ["Registrar", "System Manager"] },
        },
        {
          path: "teaching",
          name: "teaching",
          component: () => import("@/modules/teaching/TeachingView.vue"),
          meta: { title: "Teaching", roles: ALLOCATION_ROLES },
        },
        {
          path: "teaching/:group",
          name: "teaching-class",
          component: () => import("@/modules/teaching/ClassPage.vue"),
          props: true,
          meta: { title: "Class", roles: ALLOCATION_ROLES },
        },
        {
          path: "examinations",
          name: "examinations",
          component: () => import("@/modules/examinations/ExaminationsView.vue"),
          meta: { title: "Examinations", roles: EXAMINATION_ROLES },
        },
        {
          path: "examinations/:group",
          name: "mark-sheet",
          component: () => import("@/modules/examinations/SheetPage.vue"),
          props: true,
          meta: { title: "Marks", roles: EXAMINATION_ROLES },
        },
        {
          path: "my-teaching/:group/marks",
          name: "class-marks",
          component: () => import("@/modules/examinations/MarkEntryPage.vue"),
          props: true,
          meta: { title: "Marks", roles: ["Lecturer"] },
        },
        {
          path: "integrations",
          name: "integrations",
          component: () => import("@/modules/integrations/IntegrationsView.vue"),
          meta: { title: "Integrations", roles: ICT_ROLES },
        },
        {
          path: "curriculum",
          name: "curriculum",
          component: () => import("@/modules/curriculum/CurriculumView.vue"),
          meta: { title: "Curriculum", roles: CURRICULUM_ROLES },
        },
        {
          path: "curriculum/:name",
          name: "curriculum-programme",
          component: () => import("@/modules/curriculum/CurriculumPage.vue"),
          props: true,
          meta: { title: "Curriculum", roles: CURRICULUM_ROLES },
        },
        {
          path: "student-payments",
          name: "student-payments",
          component: () => import("@/modules/finance/StudentPaymentsView.vue"),
          meta: { title: "Student payments", roles: FINANCE_ROLES },
        },
        {
          path: "fee-settings",
          name: "fee-settings",
          component: () => import("@/modules/finance/FeeSettingsView.vue"),
          meta: { title: "Fee settings", roles: FEE_SETTINGS_ROLES },
        },
        {
          path: "application-fees",
          name: "application-fees",
          component: () => import("@/modules/finance/ApplicationFeesView.vue"),
          meta: { title: "Application fees", roles: FINANCE_ROLES },
        },
        // the earlier addresses
        { path: "enrolment", redirect: { path: "/registrations", query: { group: "first-year" } } },
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
    /** a split view: fills the window, list and record side by side (core/ui/SplitView; setup lists) */
    fill?: boolean;
  }
}
