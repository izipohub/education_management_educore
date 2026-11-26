import { createRouter, createWebHistory } from "vue-router";
import { useSession } from "@/core/auth/session";
import { signInFor } from "@/core/auth/signInFor";
import { CURRICULUM_ROLES } from "@/modules/curriculum/api";
import { FEE_SETTINGS_ROLES, FINANCE_ROLES, PAYMENT_ROLES } from "@/modules/finance/api";
import { APPROVAL_ROLES, ASSESSMENT_TYPE_ROLES, EXAMINATION_ROLES } from "@/modules/examinations/api";
import { GRADUATION_ROLES } from "@/modules/graduation/api";
import { ICT_ROLES } from "@/modules/integrations/api";
import { ALLOCATION_ROLES } from "@/modules/teaching/allocation";
import { RECORD_ROLES } from "@/modules/records/api";
import { DECIDE_ROLES } from "@/modules/records/studiesRequests";
import { ISSUE_ROLES } from "@/modules/records/transcripts";
import { CATEGORY_ROLES, SERVICE_ROLES } from "@/modules/records/serviceRequests";
import { REGISTRATION_ROLES } from "@/modules/registration/groups";
import { STAFF_ROLES } from "@/modules/staff/api";
import { SPONSOR_ROLES } from "@/modules/finance/sponsors";
import { TIMETABLE_ROLES } from "@/modules/teaching/timetable";
import { CLEARANCE_ROLES } from "@/modules/finance/clearance";
import { WAIVER_ROLES } from "@/modules/finance/waivers";

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
        // the student's other pages, each a menu item
        {
          path: "my-studies/assessments",
          name: "my-assessments",
          component: () => import("@/modules/student/MyStudiesView.vue"),
          props: { view: "assessments" },
          meta: { title: "Assessments", roles: ["Student"] },
        },
        {
          path: "my-studies/timetable",
          name: "my-study-timetable",
          component: () => import("@/modules/student/MyStudiesView.vue"),
          props: { view: "timetable" },
          meta: { title: "Timetable", roles: ["Student"] },
        },
        {
          path: "my-studies/fees",
          name: "my-fees",
          component: () => import("@/modules/student/MyStudiesView.vue"),
          props: { view: "fees" },
          meta: { title: "Fees", roles: ["Student"] },
        },
        {
          path: "my-studies/requests",
          name: "my-requests",
          component: () => import("@/modules/student/MyStudiesView.vue"),
          props: { view: "requests" },
          meta: { title: "Requests", roles: ["Student"] },
        },
        {
          path: "my-studies/requests/:name",
          name: "my-service-request",
          component: () => import("@/modules/student/MyServiceRequestPage.vue"),
          props: true,
          meta: { title: "Request", roles: ["Student"] },
        },
        {
          path: "my-modules",
          name: "my-teaching",
          component: () => import("@/modules/teaching/MyTeachingView.vue"),
          meta: { title: "My modules", roles: ["Lecturer"] },
        },
        // the page was "My teaching" before: old links still work
        { path: "my-teaching/:rest(.*)*", redirect: (to) => `/my-modules/${[to.params.rest].flat().join("/")}`.replace(/\/$/, "") },
        // the lecturer's daily work, each from the menu: the modules to take a register for, keep a gradebook or
        // enter marks in (a row opens that tab of the module), and their week
        {
          path: "attendance",
          name: "my-attendance",
          component: () => import("@/modules/teaching/MyTeachingView.vue"),
          props: { focus: "attendance" },
          meta: { title: "Attendance", roles: ["Lecturer"] },
        },
        {
          path: "gradebook",
          name: "my-gradebook",
          component: () => import("@/modules/teaching/MyTeachingView.vue"),
          props: { focus: "gradebook" },
          meta: { title: "Gradebook", roles: ["Lecturer"] },
        },
        {
          path: "marks",
          name: "my-marks",
          component: () => import("@/modules/teaching/MyTeachingView.vue"),
          props: { focus: "marks" },
          meta: { title: "Marks", roles: ["Lecturer"] },
        },
        {
          path: "my-timetable",
          name: "my-timetable",
          component: () => import("@/modules/teaching/MyTeachingView.vue"),
          props: { focus: "timetable" },
          meta: { title: "My timetable", roles: ["Lecturer"] },
        },
        {
          path: "my-modules/:group",
          name: "my-class",
          component: () => import("@/modules/teaching/MyClassPage.vue"),
          props: (route) => ({ group: route.params.group, tab: "students" }),
          meta: { title: "Module", roles: ["Lecturer"] },
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
          path: "admission-setup/:section(pathways|documents|funding|programmes)/:name",
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
          path: "studies-requests",
          name: "studies-requests",
          component: () => import("@/modules/records/StudiesRequestsView.vue"),
          meta: { title: "Studies requests", roles: DECIDE_ROLES },
        },
        {
          path: "transcripts",
          name: "transcripts",
          component: () => import("@/modules/records/TranscriptsView.vue"),
          meta: { title: "Transcripts", roles: ISSUE_ROLES },
        },
        {
          path: "service-requests",
          name: "service-requests",
          component: () => import("@/modules/records/ServiceRequestsView.vue"),
          meta: { title: "Service requests", roles: SERVICE_ROLES },
        },
        {
          path: "service-requests/:name",
          name: "service-request",
          component: () => import("@/modules/records/ServiceRequestPage.vue"),
          props: true,
          meta: { title: "Service request", roles: SERVICE_ROLES },
        },
        {
          path: "service-request-categories",
          name: "service-request-categories",
          component: () => import("@/modules/setup/ServiceCategoriesView.vue"),
          meta: { title: "Service request categories", roles: CATEGORY_ROLES },
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
          path: "academic-staff",
          name: "academic-staff",
          component: () => import("@/modules/staff/AcademicStaffView.vue"),
          meta: { title: "Academic staff", roles: STAFF_ROLES },
        },
        {
          path: "workload",
          name: "workload",
          component: () => import("@/modules/staff/AcademicStaffView.vue"),
          props: { view: "workload" },
          meta: { title: "Workload", roles: STAFF_ROLES },
        },
        {
          path: "academic-staff/:name",
          name: "lecturer",
          component: () => import("@/modules/staff/LecturerPage.vue"),
          props: true,
          meta: { title: "Lecturer", roles: STAFF_ROLES },
        },
        {
          path: "examinations",
          name: "examinations",
          component: () => import("@/modules/examinations/ExaminationsView.vue"),
          meta: { title: "Examinations", roles: EXAMINATION_ROLES },
        },
        {
          path: "examination-timetable",
          name: "examination-timetable",
          component: () => import("@/modules/examinations/ExaminationsView.vue"),
          props: { view: "timetable" },
          meta: { title: "Examination timetable", roles: EXAMINATION_ROLES },
        },
        {
          path: "examination-rules",
          name: "examination-rules",
          component: () => import("@/modules/examinations/ExaminationsView.vue"),
          props: { view: "rules" },
          meta: { title: "Examination rules", roles: EXAMINATION_ROLES },
        },
        {
          path: "approvals",
          name: "approvals",
          component: () => import("@/modules/examinations/ApprovalsView.vue"),
          meta: { title: "Approvals", roles: APPROVAL_ROLES },
        },
        {
          path: "assessment-types",
          name: "assessment-types",
          component: () => import("@/modules/examinations/AssessmentTypesView.vue"),
          meta: { title: "Assessment types", roles: ASSESSMENT_TYPE_ROLES },
        },
        {
          path: "examinations/:group",
          name: "mark-sheet",
          component: () => import("@/modules/examinations/SheetPage.vue"),
          props: true,
          meta: { title: "Marks", roles: EXAMINATION_ROLES },
        },
        {
          path: "graduation",
          name: "graduation",
          component: () => import("@/modules/graduation/GraduationView.vue"),
          meta: { title: "Graduation", roles: GRADUATION_ROLES },
        },
        {
          path: "my-modules/:group/attendance",
          name: "class-attendance",
          component: () => import("@/modules/teaching/MyClassPage.vue"),
          props: (route) => ({ group: route.params.group, tab: "attendance" }),
          meta: { title: "Attendance", roles: ["Lecturer"] },
        },
        {
          path: "my-modules/:group/gradebook",
          name: "class-gradebook",
          component: () => import("@/modules/teaching/MyClassPage.vue"),
          props: (route) => ({ group: route.params.group, tab: "gradebook" }),
          meta: { title: "Gradebook", roles: ["Lecturer"] },
        },
        {
          path: "my-modules/:group/marks",
          name: "class-marks",
          component: () => import("@/modules/teaching/MyClassPage.vue"),
          props: (route) => ({ group: route.params.group, tab: "marks" }),
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
          meta: { title: "Student payments", roles: PAYMENT_ROLES },
        },
        {
          path: "timetable",
          name: "timetable",
          component: () => import("@/modules/teaching/TimetableView.vue"),
          meta: { title: "Timetable", roles: TIMETABLE_ROLES },
        },
        {
          path: "rooms",
          name: "rooms",
          component: () => import("@/modules/teaching/TimetableView.vue"),
          props: { view: "rooms" },
          meta: { title: "Rooms", roles: TIMETABLE_ROLES },
        },
        {
          path: "sponsors",
          name: "sponsors",
          component: () => import("@/modules/finance/SponsorsView.vue"),
          meta: { title: "Sponsors", roles: SPONSOR_ROLES },
        },
        {
          path: "sponsors/:name",
          name: "sponsor",
          component: () => import("@/modules/finance/SponsorPage.vue"),
          props: true,
          meta: { title: "Sponsor", roles: SPONSOR_ROLES },
        },
        {
          path: "clearance",
          name: "clearance",
          component: () => import("@/modules/finance/ClearanceView.vue"),
          meta: { title: "Financial clearance", roles: CLEARANCE_ROLES },
        },
        {
          path: "clearance/:name",
          name: "clearance-student",
          component: () => import("@/modules/finance/ClearancePage.vue"),
          props: true,
          meta: { title: "Financial clearance", roles: CLEARANCE_ROLES },
        },
        {
          path: "waivers",
          name: "waivers",
          component: () => import("@/modules/finance/WaiversView.vue"),
          meta: { title: "Fee waivers", roles: WAIVER_ROLES },
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
    // signed in already, and signing in for Moodle: straight on to it
    const onward = to.name === "login" && session.isSignedIn ? signInFor(to.query["redirect-to"], window.location.origin) : null;
    if (onward) {
      window.location.assign(onward);
      return false;
    }
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
