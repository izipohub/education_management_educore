# EduCore --- Project Architecture and Agent Instructions

> **Document purpose:** This file is the working source of truth for AI
> coding agents and developers contributing to EduCore. Read it before
> proposing architecture changes, creating modules, modifying
> integrations, or implementing features.
>
> **Status:** Architecture baseline --- decisions confirmed by the
> product owner are marked **Confirmed**. Items marked **Proposed**
> require technical validation before implementation.

------------------------------------------------------------------------

## 1. Product overview

**Product name:** EduCore

EduCore is an integrated university management and enterprise platform
built on the Frappe ecosystem (Frappe Framework v16). It is intended
initially for universities in Namibia, with a private deployment for
each institution. A single deployment serves one university and all of
its campuses.

The platform is intended to cover the university's academic,
administrative, financial, human-resource, operational and governance
functions. It is not just a student information system.

### 1.1 Confirmed product decisions

  -----------------------------------------------------------------------
  Decision                            Confirmed direction
  ----------------------------------- -----------------------------------
  Product                             EduCore

  Initial market                      Namibia

  Institution type                    Universities

  Deployment model                    Private institutional deployment

  Institution tenancy                 One university per installation

  Campus structure                    Multiple campuses under one
                                      university, served by the single
                                      installation

  Campus banking                      Central bank accounts shared by
                                      all campuses

  Backend foundation                  Frappe Framework v16

  ERP foundation                      ERPNext v16

  Academic foundation                 Frappe Education (v16-compatible
                                      release)

  HR foundation                       Frappe HRMS v16

  Primary frontend                    Vue 3

  Frontend coverage                   Vue for students, applicants,
                                      sponsors, academics, academic
                                      administration, front-desk finance,
                                      staff self-service and management
                                      (see 3.1)

  Frappe Desk                         For specialist back-office work
                                      ERPNext already does well (finance,
                                      payroll/HR administration,
                                      procurement, stores, assets) and
                                      technical administration; branded
                                      and trimmed (see 3.1)

  LMS                                 Moodle

  Practical IT learning platform      KodeBook

  KodeBook deployment                 Independently hosted, integrated
                                      with EduCore

  Integration depth                   Full integration

  Identity experience                 Single sign-on across EduCore,
                                      Moodle and KodeBook
  -----------------------------------------------------------------------

### 1.2 Product positioning

EduCore is the university's central operating and administrative
platform.

-   **EduCore:** university administration, student and academic
    records, finance, HR, procurement, assets, campus operations,
    governance and institutional reporting.
-   **Moodle:** learning management, teaching materials, online learning
    activities, assignments, forums and quizzes.
-   **KodeBook:** practical programming and IT learning, coding
    exercises, browser-based labs, practical assessments and competency
    evidence.

Keep these products complementary. Do not turn EduCore into a
replacement for Moodle or KodeBook, and do not duplicate their
specialist capabilities unnecessarily.

------------------------------------------------------------------------

## 2. High-level architecture

EduCore uses a dedicated Vue frontend over a Frappe-based backend.
ERPNext, Frappe Education and Frappe HRMS provide established business
capabilities. The custom `educore` Frappe app provides
university-specific functionality, orchestration, extensions and
integrations.

``` text
                         UNIVERSITY USERS
                                |
                                v
                   EDUCORE FRONTEND (Vue 3)
           Student | Lecturer | Administration | Finance
                    HR | Management | Campus
                                |
                     HTTPS / Versioned APIs
                                |
                                v
                 FRAPPE FRAMEWORK + EDUCORE
                  Business logic / Workflows
                   Permissions / Domain APIs
                                |
             +------------------+------------------+
             |                  |                  |
             v                  v                  v
          ERPNext        Frappe Education      Frappe HRMS
       Finance/ERP        Academic/SIS          Employees/HR
             |                  |                  |
             +------------------+------------------+
                                |
                             MariaDB
                    Redis / Workers / Scheduler

             Secure integration and identity services
                       /                  \
                      v                    v
                   Moodle               KodeBook
                Independent          Independently hosted
                LMS service           practical IT platform
```

### 2.1 Architectural style

-   Use a **modular monolith** for the Frappe/EduCore backend initially.
-   Keep domain boundaries explicit in the custom EduCore app.
-   Keep Moodle and KodeBook as separate applications/services.
-   Do not introduce microservices without a demonstrated operational or
    scaling need.
-   Deploy the Vue frontend independently from the Frappe backend.
-   Use APIs and asynchronous integration events between independently
    deployed systems.
-   Do not share databases between EduCore, Moodle and KodeBook.

### 2.2 System-of-record boundaries

Avoid creating duplicate master records. Each important data domain must
have one authoritative owner.

  -----------------------------------------------------------------------
  Data / function                     System of record
  ----------------------------------- -----------------------------------
  Student identity and registration   Frappe Education,
                                      extended/orchestrated by EduCore

  Employee and lecturer employment    Frappe HRMS
  records                             

  University organisational structure EduCore
  (university, campuses, faculties,   
  departments)                        

  Programmes, curriculum and academic Frappe Education plus EduCore
  policies                            extensions

  Academic enrolment                  Frappe Education, with EduCore
                                      workflows

  Learning content and LMS activities Moodle

  Programming labs and code execution KodeBook
  evidence                            

  Moodle learning activity            Moodle

  Practical submissions and execution KodeBook
  evidence                            

  Official academic results and       EduCore / Frappe Education
  transcripts                         

  Financial transactions and general  ERPNext
  ledger                              

  Procurement, stock and assets       ERPNext, with EduCore extensions

  Staff training content, if required Decide separately; Moodle can
                                      support it
  -----------------------------------------------------------------------

**Important:** Moodle and KodeBook assessment data are assessment
evidence. They do not become official university results merely because
they are synchronised. EduCore must apply institutional validation,
moderation and approval workflows before a result enters the official
academic record.

------------------------------------------------------------------------

## 3. Frontend architecture --- Vue app and back-office Desk

### 3.1 Confirmed decision (revised 2026-11-22)

EduCore has two user interfaces, split by who the user is. The earlier
decision ("Vue for all university-facing interfaces") was revised by the
product owner: rebuilding ERPNext's mature finance, payroll, procurement
and stock screens in Vue would take years and fall behind every upstream
release.

**Vue app** --- high-volume, university-specific work by non-specialists:

-   Students, applicants, sponsors and guardians.
-   Lecturers, heads of department and deans.
-   Admissions, registry, faculty and examinations officers.
-   Cashiers and the student fees front desk.
-   Every staff member's self-service (leave, payslips, requests).
-   Management dashboards and campus-operations requests.

**Frappe Desk** --- specialist back-office work that ERPNext, HRMS and
Education already do well, by a small number of trained staff:

-   Finance: general ledger, journals, bank reconciliation, financial
    reports, period closing.
-   Payroll and HR administration.
-   Procurement, stores and asset management.
-   ICT / technical administration.

Rules:

-   Desk access is deliberate: only positions that carry the EduCore
    **Desk Access** role (and System Managers) can open the Desk; everyone
    else is sent to the Vue app (`educore/access/desk.py`). Frappe's API
    stays available to all signed-in users, because the Vue app uses it.
-   Desk users see a trimmed Desk: a Module Profile hides modules a
    university does not use (manufacturing, CRM and so on), and the
    EduCore theme brands it.
-   Business rules and permissions live on the server, so they apply
    identically in both interfaces.
-   Do not build Vue screens for back-office work the Desk already does
    well, and do not send Vue-app users to the Desk to finish a task.
-   Any Desk area that proves painful for its users can get a Vue screen
    later, module by module, as a recorded decision.

### 3.2 Recommended frontend stack

  Concern                      Technology
  ---------------------------- -----------------------
  UI framework                 Vue 3
  Language                     TypeScript
  Build tooling                Vite
  Routing                      Vue Router
  State management             Pinia
  Component library            PrimeVue
  Styling                      Tailwind CSS
  HTTP client                  Axios
  Authentication               OpenID Connect (OIDC)
  Charts                       Apache ECharts
  Unit/component testing       Vitest
  Browser/end-to-end testing   Playwright

These are the selected architectural recommendations. Verify
compatibility and choose pinned, mutually compatible versions when
bootstrapping the repository.

**PrimeVue licence (Confirmed, 2026-11-22):** PrimeVue 5 and later are
commercial (PrimeTek's PrimeUI licence). EduCore uses **PrimeVue 4.5.5
with `@primeuix/themes` 1.2.5, the last MIT-licensed release**, pinned
exactly. Do not upgrade PrimeVue to 5.x without a licence decision. If
4.x stops receiving fixes, the alternatives are a paid PrimeVue licence or
an MIT library such as Reka UI. Every dependency's licence must be checked
before it is added; the pinned versions live in
`frontend/educore-ui/package.json`.

### 3.3 Design system

Create one EduCore design system shared by all modules.

It should define: - Colour tokens, typography, spacing, elevation and
responsive breakpoints. - Navigation, page headers, breadcrumbs and
contextual actions. - Form controls, validation states and accessible
error messages. - Data tables, filtering, sorting, pagination and bulk
actions. - Dialogs, drawers, notifications and confirmation patterns. -
Loading, empty, error and permission-denied states. - Dashboard cards,
charts and reporting layouts. - Accessibility standards and keyboard
interaction.

Use PrimeVue for complex reusable controls and Tailwind for layout and
visual consistency. Do not allow each module to invent its own design
language.

### 3.4 Role-specific experiences

Use one Vue application with role-aware navigation and views. Do not
assume that hiding a route or button is sufficient security; the backend
must enforce every permission.

Roles and positions (Role Profiles) are defined in
`apps/educore/educore/access/roles.py` and listed in
`docs/architecture/roles-and-positions.md`. Add or change a position
there, not in the Role Profile form.

Every experience is also **campus-aware** (see section 5.1.1). A user's
role applies within the campuses they are authorised for: a campus
registrar sees their campus, a university registrar sees all campuses.
Provide a campus context/switcher for users with access to more than
one campus, and default management views to a consolidated university
view with per-campus drill-down.

  -----------------------------------------------------------------------
  Experience                          Main responsibilities
  ----------------------------------- -----------------------------------
  Student                             Applications, registration,
                                      timetable, fees, results,
                                      transcripts, services, Moodle and
                                      KodeBook access

  Lecturer                            Teaching assignments, course
                                      rosters, attendance, assessment,
                                      moderation and student progress

  Registrar / Academic administration Admissions, programme management,
                                      registration, academic records,
                                      examinations and graduation

  Finance                             Student billing, receipts,
                                      payments, scholarships,
                                      sponsorships, reconciliations and
                                      finance reporting

  HR                                  Employee records, recruitment,
                                      leave, payroll workflows and staff
                                      administration

  Procurement / Stores                Requisitions, approvals,
                                      purchasing, inventory and suppliers

  Campus operations                   Facilities, rooms, laboratories,
                                      bookings, maintenance and asset
                                      custody

  Management                          Institutional dashboards,
                                      enrolment, finance, staffing,
                                      performance and governance reports

  Technical operator                  Technical administration in Frappe
                                      Desk

  *Interface:* the finance (back office), HR administration and
  procurement / stores rows work in the Desk; the others work in the Vue
  app (3.1).
  -----------------------------------------------------------------------

### 3.5 Suggested frontend structure

``` text
educore-ui/
├── src/
│   ├── app/
│   │   ├── App.vue
│   │   ├── router/
│   │   └── providers/
│   ├── core/
│   │   ├── auth/
│   │   ├── api/
│   │   ├── permissions/
│   │   ├── layouts/
│   │   └── notifications/
│   ├── modules/
│   │   ├── admissions/
│   │   ├── academics/
│   │   ├── students/
│   │   ├── examinations/
│   │   ├── finance/
│   │   ├── human-resources/
│   │   ├── procurement/
│   │   ├── inventory/
│   │   ├── assets/
│   │   ├── campus/
│   │   ├── research/
│   │   ├── governance/
│   │   ├── learning/
│   │   └── analytics/
│   ├── components/
│   │   ├── forms/
│   │   ├── tables/
│   │   ├── dialogs/
│   │   ├── charts/
│   │   └── navigation/
│   ├── stores/
│   ├── composables/
│   ├── types/
│   └── styles/
├── public/
├── tests/
└── package.json
```

This is a suggested logical structure. Adjust it when the actual
repository and build requirements are inspected; preserve domain
boundaries.

------------------------------------------------------------------------

## 4. Backend architecture --- Frappe ecosystem

### 4.1 Responsibilities

-   **Frappe Framework v16:** application framework, DocTypes,
    permissions, workflows, APIs, background jobs, scheduler and hooks.
-   **ERPNext:** accounting, finance, purchasing, suppliers, stock,
    assets and other enterprise capabilities.
-   **Frappe Education:** student and academic foundation, including
    supported student, programme, course and enrolment records.
-   **Frappe HRMS:** employee and human-resource foundation.
-   **Custom EduCore app:** university-specific records, business rules,
    workflows, integration orchestration, APIs and reporting.

### 4.2 Target version --- Frappe v16 (Confirmed)

-   The backend targets the **Frappe v16** release line: Frappe
    Framework v16, ERPNext v16 and HRMS v16.
-   Frappe Education must be pinned to a release that officially
    supports Frappe v16. Verify this during M0; if no supported release
    exists, raise it before proceeding rather than patching upstream.
-   Pin exact v16 patch versions for every app in the bench and upgrade
    them together.
-   Use the Python, Node.js, MariaDB and Redis versions required by the
    official v16 release notes. Do not assume v15 runtime requirements.
-   Do not follow v14/v15-era tutorials or APIs without checking that the
    behaviour is unchanged in v16. Check deprecations and removed APIs
    in the v16 migration notes before using a framework API.
-   Custom `educore` app code, hooks and patches must declare and test
    against v16 only; do not add backward-compatibility code for older
    Frappe versions.

### 4.3 Extension rules

-   Do not fork or modify upstream ERPNext, Education or HRMS code
    unless there is a documented, approved reason.
-   Prefer custom DocTypes, custom fields, hooks, fixtures, domain
    services, whitelisted APIs and versioned patches.
-   Inspect the exact installed upstream versions, DocTypes, fields,
    relationships, hooks and dependencies before implementing
    extensions.
-   Reuse canonical Student, Employee, Company, Department, Account and
    other existing master records where appropriate.
-   Do not create duplicate masters simply to make a custom module
    easier.
-   Keep custom university logic inside the `educore` app.
-   Keep integration adapters isolated from core academic and finance
    domain logic.

### 4.4 Proposed API structure

Expose stable, versioned APIs for the Vue application. The following is
a proposed route organisation, not a claim that these endpoints already
exist.

``` text
/api/v1/
├── auth/
├── institution/
├── admissions/
├── students/
├── academics/
├── examinations/
├── graduation/
├── finance/
├── hr/
├── procurement/
├── inventory/
├── assets/
├── campus/
├── research/
├── governance/
├── learning/
└── analytics/
```

Use domain services for complex operations. API controllers should
validate inputs, authenticate and authorise the caller, invoke domain
services and return consistent response structures.

Do not expose internal database tables or rely on frontend code to
enforce business rules.

------------------------------------------------------------------------

## 5. University domain model and modules

The platform is intended to cover the university as a whole. Implement
in phases, but preserve a coherent domain model.

### 5.1 Institution foundation

Potential EduCore records and concepts: - University Profile - Campus -
Faculty - Academic Department - Administrative Division - Academic
Unit - Institutional Calendar - Academic Policy - Institutional Approval
Matrix - Academic Committee

### 5.1.1 Multi-campus model (Confirmed)

One EduCore installation serves **one university with multiple
campuses**. Campuses are not separate tenants or separate installations;
they share one database, one identity domain and one set of
university-wide policies, while operational data is scoped by campus.

``` text
University (one per installation)
├── Campus A (e.g. main campus)
│   ├── Faculties / Schools offered at this campus
│   ├── Buildings, rooms, laboratories
│   ├── Campus staff and campus administration
│   └── Students whose home campus is A
├── Campus B
│   └── ...
└── University-wide
    ├── Academic policies, qualification framework, curriculum
    ├── Central finance, HR, procurement
    └── Consolidated reporting and governance
```

Rules:

-   **Campus is a first-class master record** owned by EduCore. Every
    campus-specific record (student registration, programme offering,
    course schedule, room, facility booking, staff assignment, fee
    policy, service request, asset custody) must carry a mandatory
    `campus` link where campus is meaningful.
-   **University-wide records stay campus-neutral:** programmes,
    curriculum versions, qualifications, academic policies and the
    approval matrix are defined once at university level. A campus
    *offers* a programme through a campus-level offering record rather
    than duplicating the programme.
-   **Faculties may span campuses.** Do not assume a faculty or
    department belongs to exactly one campus; model the relationship
    explicitly.
-   **Students have a home campus** and may take courses at, or transfer
    to, another campus. Keep campus history in Student Status History /
    transfer records.
-   **Staff have a primary campus** and may teach or work across
    campuses. Lecturer workload and teaching assignments carry campus.
-   **Campus-scoped permissions:** restrict campus users to their
    authorised campuses using Frappe User Permissions on Campus (or an
    equivalent backend mechanism), enforced server-side in every API and
    report. University-level roles see all campuses.
-   **Reporting** must support both consolidated university views and
    per-campus breakdowns.
-   **Mapping to upstream apps (Proposed --- validate in M0):**
    -   ERPNext: one Company for the university by default, so campus
        finances are reported without splitting the ledger. Use separate
        Companies only if campuses are separate legal or statutory
        reporting entities. See section 5.1.2 for the cost center model.
    -   HRMS: use the Branch field (or a custom Campus link) on Employee
        for the staff member's campus.
    -   Frappe Education: link Student, Program Enrollment, Student
        Group, Course Schedule and Room to Campus via custom fields
        where upstream has no campus concept.
    -   Moodle / KodeBook: map campus to course categories, cohorts or
        equivalent grouping only where the institution needs
        campus-separated learning spaces.
-   Never hard-code a single campus, a default campus name or a campus
    count in code or fixtures.

### 5.1.2 Campus cost centers (Implemented: campus cost centers; department dimension still Proposed)

With one ERPNext Company, each campus gets its own cost center under a
university parent, plus a central cost center for shared university
costs:

``` text
<University> (Company)
└── <University>                     (group cost center)
    ├── Central Administration       (shared/central costs; ERPNext's
    │                                 "Main", renamed by the setup)
    ├── <Campus A>                   (leaf: campus postings)
    └── <Campus B>                   (leaf)
```

ERPNext posts only to leaf cost centers, so a campus cost center is a
leaf. If a campus later needs sub-budgets, it becomes a group with a
"<Campus> General" child for its own postings plus the budget holders'
children.

-   **Campus = cost center.** Each Campus record creates and links its
    cost center (and an HR Branch) when it is saved
    (`educore/institution/doctype/campus`). Per-campus P&L and budgets come from filtering on it; the
    parent cost center gives the consolidated university view.
-   **Department = accounting dimension**, not a cost center. This keeps
    campus and department as independent filters and avoids duplicating
    departments per campus (e.g. "Campus A - Science", "Campus B -
    Science"). Confirm that v16 budgeting against accounting dimensions
    meets the institution's needs before relying on it.
-   **Child cost centers** under a campus are created only where a
    budget holder at that campus needs a separately controlled budget.
-   **Central costs** (executive office, central IT, central finance)
    post to Central Administration. If campus-level reporting must
    include a share of them, use cost center allocation or periodic
    allocation journal entries --- agree the basis with finance.
-   **Defaulting:** EduCore sets the cost center automatically from the
    campus of the student, employee, facility or request on fee
    invoices, payments, purchases, payroll entries and asset records.
    Do not rely on users selecting it manually.
-   **Central banking (Confirmed):** the university uses central bank
    accounts shared by all campuses. Do not create per-campus bank
    ledger accounts. Payments and receipts into the central accounts
    must still carry the campus cost center so collections can be
    reported per campus. Bank reconciliation is performed centrally.
-   Never hard-code cost center names; resolve them from the Campus
    record.

### 5.2 Academic and curriculum extensions

Reuse supported Frappe Education records where they fit, including
Student, Student Applicant, Program, Course, Academic Year, Academic
Term, Program Enrollment, Student Group, Course Schedule, Assessment
Plan/Result and Student Attendance. Confirm exact names and fields
against the installed version before coding.

Potential EduCore extensions: - Qualification Framework -
Qualification - Programme Accreditation - Programme Curriculum Version -
Curriculum Course - Course Prerequisite - Programme Requirement -
Academic Progression Rule - Graduation Application / Clearance - Degree
Award - Academic Transcript Request - Examination Session / Venue -
Invigilation Assignment - Results Approval

### 5.3 Student lifecycle

Potential EduCore records: - Admission Evaluation - Admission Decision -
Student Registration - Student Status History - Student Financial
Clearance - Student Disciplinary Case - Student Accommodation
Application / Allocation - Student Service Request - Student Graduation
Clearance

### 5.4 Human capital

HRMS remains authoritative for Employee and employment/payroll records,
including supported Employee, Employee Grade, Employment Type,
Department, Job Applicant, Job Opening, Leave Application, Salary
Structure, Salary Slip and Employee Performance Feedback records. Verify
exact upstream DocTypes before implementation.

Potential EduCore academic-staff extensions: - Academic Appointment -
Academic Rank / Promotion - Lecturer Qualification - Lecturer Workload -
Teaching Assignment - Research Supervision Assignment - Academic
Appraisal - Visiting Lecturer Appointment

### 5.5 Student finance

ERPNext remains authoritative for accounting and financial transactions,
including Sales Invoice, Payment Entry, Journal Entry and General Ledger
records.

Potential EduCore records: - Student Fee Policy - Student Fee
Assessment - Scholarship Scheme / Award - Sponsorship Agreement -
Student Financial Hold - Fee Waiver Request - Payment Allocation
Exception - Student Financial Clearance

### 5.6 Procurement, inventory, assets and campus

ERPNext owns procurement, stock and asset accounting records. Potential
EduCore extensions: - Departmental Procurement Request - Procurement
Approval - Campus Facility - Classroom - Laboratory - Facility Booking -
Campus Maintenance Request - Asset Custodian Assignment

Facilities, rooms, laboratories, stock locations (warehouses) and assets
belong to a specific campus. Procurement may be campus-initiated with
central approval where the approval matrix requires it.

### 5.7 Governance, research and analytics

Plan for institutional governance, committees, policy management,
research administration, supervision, research projects, ethics-related
workflows where applicable, and management analytics. Define detailed
records and regulatory requirements with the institution before
implementation.

------------------------------------------------------------------------

## 6. Moodle and KodeBook learning ecosystem

### 6.1 Platform responsibilities

**Moodle** - Course learning materials and resources. - Online
assignments, quizzes, question banks and gradebook. - Forums,
discussions and collaboration. - Supported learning activities and
external learning tools. - Learning progress and activity reporting.

**KodeBook** - Programming exercises and coding environments. -
Practical IT labs and technical exercises. - Database and programming
practice. - Operating-system, networking, server and security practical
activities as supported by the product. - Code submissions, execution
results, automated tests and practical assessment evidence. - Practical
competency evidence.

Do not assume every advertised KodeBook language, lab or feature is
already implemented. Inspect the real KodeBook product and API before
designing detailed integration contracts.

### 6.2 Confirmed KodeBook decisions

  -----------------------------------------------------------------------
  Decision                            Direction
  ----------------------------------- -----------------------------------
  Integration                         Full integration with EduCore

  Identity                            SSO across EduCore, Moodle and
                                      KodeBook

  Hosting                             KodeBook remains independently
                                      hosted

  Application boundary                KodeBook is not embedded in the
                                      Frappe bench

  Data exchange                       Secure APIs and events

  Academic authority                  EduCore approves and records
                                      official academic results
  -----------------------------------------------------------------------

### 6.3 EduCore Learning Integration module

Potential DocTypes: - Learning Platform Configuration - External User
Mapping - External Course Mapping - External Enrolment - Practical Lab -
Practical Assessment - Assessment Result Import - Competency Record -
Learning Activity Record - Integration Event - Integration Error Log -
Academic Result Approval

Inspect existing DocTypes and avoid duplication before creating these
records.

### 6.4 Full integration workflows

1.  A student is admitted and registered in EduCore.
2.  EduCore provisions or links the student's identity in Moodle and
    KodeBook.
3.  Approved academic courses are mapped to corresponding Moodle courses
    and KodeBook learning spaces/labs.
4.  Student and lecturer enrolments are synchronised.
5.  Moodle manages learning materials and online activities.
6.  KodeBook manages practical coding and IT lab activities.
7.  Platforms report relevant assessment outcomes and evidence to
    EduCore.
8.  EduCore validates, maps and stores incoming outcomes.
9.  Authorised academic staff review, moderate and approve marks.
10. Only approved results enter official academic records and
    transcripts.

### 6.5 Integration reliability

Use asynchronous jobs for non-interactive provisioning and
synchronisation. Design for: - Idempotency and duplicate-event
protection. - Retries with bounded backoff. - Dead-letter or
failed-event handling. - Reconciliation jobs. - Correlation IDs and
traceable logs. - Explicit event schemas and versioning. -
Authentication and signature validation. - Monitoring of sync lag and
failure rates.

A proposed event may look like this:

``` json
{
  "event": "assessment.completed",
  "version": "1.0",
  "event_id": "unique-event-id",
  "occurred_at": "2026-11-20T12:00:00Z",
  "student_id": "EDU-000123",
  "course_id": "COMP101",
  "assessment_id": "LAB-001",
  "attempt_id": "ATT-00045",
  "score": 85,
  "maximum_score": 100,
  "status": "completed"
}
```

This is an illustrative contract only. Confirm identifiers, fields,
scoring rules and actual KodeBook capabilities with the KodeBook
implementation before adopting it.

------------------------------------------------------------------------

## 7. Identity and single sign-on

### 7.1 Architecture

Use a central identity provider supporting OpenID Connect (OIDC).
Keycloak is a candidate, subject to compatibility testing with the
selected Frappe, Moodle and KodeBook versions.

``` text
                  UNIVERSITY IDENTITY PROVIDER
                           OIDC / MFA
                               |
                 +-------------+-------------+
                 |             |             |
                 v             v             v
              EduCore        Moodle       KodeBook
              Vue UI         LMS           Platform
```

### 7.2 Identity principles

-   One stable university identity per person.
-   A stable subject identifier (`sub`) or equivalent external identity
    key for account linking.
-   EduCore remains authoritative for university user records and access
    eligibility.
-   Map university roles/groups to each platform's own permissions.
-   Provision, update, suspend and deactivate linked accounts.
-   Support institutional MFA policies.
-   Use secure token, session, logout and expiry practices.
-   Never synchronise or copy user passwords between applications.
-   Do not assume role names or permission semantics are identical
    across platforms.

### 7.3 Authentication and browser security

The implementation must explicitly decide and test: - OIDC flow
appropriate for browser-based public clients, normally Authorization
Code with PKCE. - Redirect URI registration and validation. - Token
storage and refresh strategy. - Secure session handling and logout. -
CSRF protection where cookie-based sessions are used. - CORS allowlists
if separate origins are used. - SameSite and Secure cookie settings. -
Service-to-service credentials distinct from human-user tokens. - Key
rotation, secret storage and incident response.

Do not store long-lived sensitive tokens in browser local storage by
default. Prefer a carefully designed secure session or
backend-for-frontend approach where appropriate.

------------------------------------------------------------------------

## 8. API and integration security

### 8.1 Vue to Frappe

-   Vue must never connect directly to MariaDB or Redis.
-   All protected data access goes through authenticated backend APIs.
-   Enforce role, document, field and operation permissions on the
    backend.
-   Validate all user input server-side.
-   Use pagination, filtering and bounded result sizes.
-   Apply rate limits and sensible request timeouts.
-   Avoid exposing unrestricted generic database operations to the
    browser.
-   Return consistent error structures without leaking secrets or stack
    traces.

### 8.2 Platform-to-platform integrations

-   Use HTTPS.
-   Use scoped credentials or tokens.
-   Validate webhook signatures and timestamps.
-   Protect against replay and duplicate events.
-   Rotate secrets and keep them out of source control.
-   Restrict network access where feasible.
-   Log security-relevant integration actions.
-   Never trust a result payload solely because it came from an external
    platform; validate its identity, mapping, context and integrity.

### 8.3 KodeBook code execution isolation

KodeBook executes student-provided code. Its execution environment must
be isolated from the application host and university systems.

Require and validate: - Sandboxed execution environments. - CPU, memory,
disk and execution-time limits. - No unrestricted host filesystem
access. - Controlled outbound network access. - Isolation between
students and lab sessions. - Secure handling of uploaded files and
credentials. - Logging and audit trails for submissions and assessment
changes. - Patch and image lifecycle management for execution
environments.

Do not expose EduCore databases, internal services or privileged
credentials to student code execution environments.

------------------------------------------------------------------------

## 9. Namibia and institutional configuration

Initial market: Namibia.

Proposed defaults, to be validated with the institution and relevant
professional advisers: - Currency: NAD. - Time zone: Africa/Windhoek. -
Primary language: English. - Date display: DD-MM-YYYY where
appropriate. - Configurable academic year and financial year. - Local
banking and EFT workflows as required. - Payroll statutory rules and tax
configuration must be validated against current Namibian requirements
before production use. - Accreditation, qualification and reporting
requirements must be confirmed with the relevant Namibian authorities
and institution.

Do not hard-code local policy or statutory rates into frontend code. Use
configurable backend records and versioned effective dates where
appropriate.

------------------------------------------------------------------------

## 10. Deployment and infrastructure

### 10.1 Private institutional deployment

Each university receives its own EduCore installation. Do not design the
initial deployment as a shared multi-tenant SaaS database.

All campuses of that university use the same installation. Do not deploy
a separate EduCore instance per campus. Plan for campuses connecting
over WAN links of varying quality: keep the frontend lightweight, and
validate performance from the furthest campus during staging.

### 10.2 Logical deployment separation

``` text
University private infrastructure
|
+-- EduCore frontend
|   +-- Vue production build
|   +-- Nginx / reverse proxy
|
+-- EduCore backend
|   +-- Frappe Framework v16
|   +-- ERPNext v16
|   +-- Frappe Education (v16-compatible)
|   +-- Frappe HRMS v16
|   +-- MariaDB
|   +-- Redis
|   +-- Workers
|   +-- Scheduler
|
+-- Moodle environment
|   +-- Moodle application
|   +-- Moodle database
|   +-- Moodle data storage
|
+-- Identity provider
|   +-- OIDC
|   +-- MFA and identity policies
|
+-- Independent KodeBook service
    +-- KodeBook application
    +-- Execution/lab infrastructure
    +-- KodeBook data storage
```

The Moodle and KodeBook deployment locations may be separate from the
university's EduCore infrastructure, subject to institutional security,
data residency, connectivity and contractual requirements.

### 10.3 Frontend/backend hosting

Recommended initial pattern: - Build Vue as static production assets. -
Serve through Nginx or an equivalent controlled web server/CDN. - Deploy
Frappe separately with its supported application, worker and scheduler
processes. - Use HTTPS throughout. - Choose same-origin reverse-proxy
routing or separate subdomains deliberately. Configure CORS, CSRF and
cookies accordingly. - Keep secrets and environment-specific
configuration outside frontend bundles.

### 10.4 Environments and operations

Maintain separate: - Development - Automated test / CI - Staging -
Production

Establish: - Version-pinned dependencies. - Reproducible builds. -
Database and file backups. - Offsite backup storage. - Tested
restoration procedures. - Monitoring, centralised logs and alerting. -
Documented disaster recovery objectives approved by the institution. -
Security patching and upgrade windows. - Release and rollback
procedures.

Any RPO/RTO targets must be agreed and tested; do not treat illustrative
targets as guarantees.

------------------------------------------------------------------------

## 11. Repository and engineering organisation

A possible repository organisation is:

``` text
educore/
├── backend/
│   └── educore/                 # Custom Frappe application
│       ├── api/
│       ├── services/
│       ├── integrations/
│       ├── workflows/
│       └── doctype/
│
├── frontend/
│   └── educore-ui/              # Vue 3 application
│       ├── src/
│       ├── tests/
│       └── package.json
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   ├── deployment/
│   └── monitoring/
│
├── docs/
│   ├── architecture/
│   ├── api/
│   ├── integrations/
│   ├── security/
│   └── operations/
│
└── README.md
```

This is a proposed logical layout, not a requirement to force all code
into one repository. Separate repositories for frontend, backend and
deployment are acceptable if ownership, versioning and CI/CD remain
clear.

### 11.1 Engineering standards

-   Use Python for Frappe backend development.
-   Use Vue 3 and TypeScript for the frontend.
-   Follow Frappe conventions for DocTypes, hooks, patches and
    permissions.
-   Keep business logic in backend domain services.
-   Keep UI components reusable and accessible.
-   Use typed API contracts and versioned endpoints.
-   Add automated tests for business rules and workflows.
-   Add integration tests for Frappe and external platforms.
-   Use browser tests for critical end-to-end workflows.
-   Use linting and formatting consistently.
-   Document non-obvious design decisions.
-   Use migrations/patches for schema changes; never rely on manual
    production database edits.
-   Review security and permissions as part of every feature.

------------------------------------------------------------------------

## 12. Implementation roadmap

The roadmap is phased. Do not implement every module at once.

  -----------------------------------------------------------------------
  Phase                               Main deliverables
  ----------------------------------- -----------------------------------
  M0 --- Foundation                   Pin Frappe v16 ecosystem versions
                                      and confirm Education v16
                                      compatibility; repository;
                                      CI/CD; Docker/deployment
                                      foundation; Vue foundation;
                                      identity architecture; API
                                      conventions; design system

  M1 --- Institution                  University profile, multi-campus
                                      structure, faculties, departments,
                                      roles, campus-scoped permissions,
                                      academic policies and
                                      institutional configuration

  M2 --- Student and academics        Admissions, applicants, student
                                      lifecycle, programmes, curriculum,
                                      registration, course enrolment and
                                      timetables

  M3 --- Moodle and academic UI       Student and lecturer Vue
                                      experiences; Moodle SSO,
                                      user/course provisioning and
                                      enrolment integration

  M4 --- KodeBook integration         KodeBook API contract; SSO;
                                      identity mapping; course/lab
                                      mapping; user and enrolment
                                      provisioning

  M5 --- Practical learning           Lab assignments, practical
                                      submissions, assessment imports,
                                      competency evidence, moderation and
                                      official result workflows

  M6 --- Enterprise operations        Finance, HR, payroll workflows,
                                      procurement, stock, assets and
                                      campus operations

  M7 --- Academic completion and      Examinations, graduation,
  production                          transcripts, analytics, governance,
                                      security hardening, performance and
                                      production readiness

  M8 --- Integrations and services    AI assistant, online payments,
                                      SMS, funder (NSFAF, NTA, sponsors)
                                      and authority (NQA, NTA) reporting,
                                      Microsoft 365 / Google Workspace
                                      sign-in
  -----------------------------------------------------------------------

### 12.0 Status and committed scope (as of 2026-11-26)

EduCore is now also offered to private training institutes (multi-campus,
NQA-accredited, certificate to degree level), not only universities.
Client proposals present the full scope below as part of the product, so
it is **committed**: build it before the client's campuses reach it in
their rollout.

**Built (in the app):** multi-campus institution and roles; admissions
(online and paper applications, entry rules and pathways, funding routes
with their documents (NSFAF and NTA applicants pay no application fee),
application fees by nationality (home, regional, international) matched
by EFT reference, offers and letters); student records;
curriculum by year and semester with prerequisites; registration with
faculty approval, deposit and fee rules, late fees, proof of
registration; course changes; interruption and cancellation of studies; campus transfers (the same programme at another campus from a year not yet registered for; the student then belongs to that campus and registers there); each student's status history (admission, registrations, interruptions, transfers, holds, completion, read from the records themselves);
teaching allocation and class lists; timetables (each class's weekly times per semester in a room on its campus, refused when a room, lecturer or student would be in two places at once; rooms with type and seats; each lecturer's and student's week); class attendance (the lecturer's register per lesson, from the timetable, the university's minimum flagged to lecturer, department and student); the lecturer's My modules (a row per module; each module's page with its students, attendance, gradebook and marks, searchable for large classes; their week on its own tab); the gradebook (the lecturer's assessments, of the faculty's assessment types, each marked out of what they choose with its share of the CA, the CA worked out from the scores; the plan approved by the Head of Department or the Dean before scores go in, returned with the reason for a change); assessment types per faculty, kept by the Dean (online in Moodle or not, the highest share of the CA); online assessments linked to their Moodle activity, the grades brought in for the lecturer to check and save, then moderated with the rest; the student's Assessments tab (each module's approved assessments with due dates and Moodle links, their scores and provisional CA, as marked or once published, as the university decides); examination timetables (sessions per semester, main or supplementary and special; each class's paper with its date, hours, rooms and invigilators, refused when a student writes two papers at once, a room has fewer seats than those writing in it, or an invigilator is in two rooms; published by the Registrar, then each student's papers and each invigilator's duties on their Timetable tab); lecturers set up from the Lecturer position, with an Academic staff screen; lecturer workload (each lecturer's modules, students, contact hours a week from the timetable, a co-taught class counting for each lecturer, and invigilation hours per semester, against the university's rule of contact hours a week at least and at most, set by the Registrar; Over, Within, Light or Not allocated; each lecturer's hours shown when allocating); marks, moderation, board approval,
publication, supplementary and special examinations, academic standing;
graduation list, academic record, award certificate, QR verification; official transcript requests (the student asks for copies collected, emailed or posted; the fee per copy invoiced; the Registry issues once paid and, where required, financially cleared, emailing the academic record PDF itself);
student fees with EFT matching by student number; instalment plans (each year's due dates and shares on every invoice of the year); fee waivers (requested by Finance with the reason, approved or rejected by the Bursar, never their own; a percent of the year's fees, an amount or the late registration fee, taken off the year's invoice by credit note, after sponsors; the registration deposit on what is left); financial holds and clearance (Finance's holds block registration; graduation and the award certificate need clearance); sponsor accounts (sponsors invoiced for their share of a student's year by credit note and sponsor invoice, paid by EFT with the sponsor number, statement PDF; the registration deposit on the student's own share); Moodle course and
enrolment sync; registrar dashboard; each person's home (what is waiting for them from every queue their positions work on, a lecturer's lessons today, a student's classes, assessments due and examinations ahead); a menu with an item for each frequent operation (a lecturer's attendance, gradebook and marks; the department's approvals and workload), in sections; email to applicants and students.

**Committed, not yet built:**

| Area | Still to build | Milestone |
|---|---|---|
| Institution | Institutional calendar and policies UI, approval matrix, committees and policy register | M1, M7 |
| Programmes | Curriculum versions (changes apply to new intakes), programme accreditation records, NQF levels on qualifications | M2 |
| Student records | Disciplinary cases, service requests | M2 |
| HR | Vue staff self-service (leave, payslips, details); lecturer qualifications and appointments; payroll validated for Namibian statutory rules | M6 |
| Procurement and assets | Purchase requests with budget-holder approval, stores per campus, asset custody per campus | M6 |
| Campus facilities | Rooms and laboratories, booking, maintenance requests | M6 |
| Learning | Moodle single sign-on | M3 |
| Management | Dashboards for results, fees and staff per campus; Excel export of every report | M7 |
| Integrations | AI assistant (applicant and student questions, staff drafting; suggests only, staff decide); payment gateway (card, instant EFT); SMS notices; NSFAF, NTA and sponsor invoicing and reports; NQA and NTA returns; Microsoft 365 / Google Workspace sign-in | M8 |

**Service commitments in proposals:** support Monday to Friday, 08:00
to 17:00 by email and telephone; response within 2 working hours
(critical), the same working day (high), 2 working days (normal);
updates outside working hours with notice; monitoring; daily backups
to a separate location and a disaster-recovery plan, with a full
restore tested before go-live and regularly after it; training by
role at each campus before it goes live, with a guide per role.

### 12.1 First engineering tasks

Before creating many custom DocTypes: 1. Inspect the actual repository
and current implementation state. 2. Inspect the selected Frappe,
ERPNext, Education and HRMS versions and compatibility. 3. Inspect
upstream DocTypes, fields, links, hooks and workflows relevant to the
first release. 4. Confirm the Vue app bootstrap, build, routing, API
connectivity and design system. 5. Define the authentication/session
architecture and test it end to end. 6. Define the API response/error
conventions and permission strategy. 7. Implement one vertical slice,
such as viewing and managing a student record, from Vue through a
permission-checked Frappe API. 8. Add tests and deployment automation
before expanding to more modules.

------------------------------------------------------------------------

## 13. Agent operating instructions

Any AI coding agent working on EduCore must follow these instructions.

### 13.1 Before making changes

-   Read this file in full.
-   Inspect the existing repository before assuming a folder structure,
    framework version or implementation state.
-   Identify whether the task belongs to the Vue frontend, EduCore
    backend, infrastructure or an external integration.
-   Check existing DocTypes, APIs, components and services before
    creating duplicates.
-   Verify current installed versions and official documentation for
    version-sensitive framework behaviour.
-   Ask a focused clarification if a required product decision is
    genuinely missing. Do not repeatedly ask questions already answered
    in this document.

### 13.2 During implementation

-   Preserve the confirmed architecture and product decisions.
-   Put each screen in the interface its users work in (3.1): the Vue
    app for students, academics, officers and self-service; the Desk for
    specialist back-office work.
-   Do not rebuild in Vue what ERPNext's Desk already does well for
    back-office staff, and do not leave Vue-app users a Desk-only step.
-   Keep Frappe as the backend authority for business rules and
    permissions.
-   Reuse ERPNext, Frappe Education and HRMS capabilities instead of
    duplicating them.
-   Keep KodeBook and Moodle independently deployed.
-   Use APIs and defined contracts rather than direct database coupling.
-   Keep official academic result approval inside EduCore.
-   Target Frappe v16 APIs and conventions only.
-   Design every operational record, API and report to be campus-aware
    and campus-permission-checked; never assume a single campus.
-   Make integrations idempotent, observable and retryable.
-   Treat student-submitted code as untrusted and isolate execution.
-   Avoid introducing new infrastructure or dependencies without a clear
    reason.

### 13.3 Before finishing a task

-   Run relevant automated tests, linting and type checks.
-   Report exactly what changed.
-   Report commands/tests run and their outcomes.
-   Identify migrations, configuration changes and deployment steps.
-   Identify assumptions, incomplete work and known risks.
-   Do not claim tests passed if they were not run.
-   Do not silently change confirmed architecture decisions. Explain the
    trade-off and request approval for material changes.

### 13.4 Decision hierarchy

1.  Explicit, confirmed product-owner decisions in this document.
2.  Existing approved architecture and documented technical decisions.
3.  Existing repository conventions and tested implementation.
4.  Official documentation for the exact installed versions.
5.  New recommendations, clearly labelled as proposals.

If the repository contradicts this document, do not blindly overwrite
working code. Explain the discrepancy and propose a safe migration path.

------------------------------------------------------------------------

## 14. Open technical decisions

These items are not fully settled and must be validated during M0:

-   Exact v16 patch versions of Frappe, ERPNext and HRMS, and which
    Frappe Education release supports v16.
-   ERPNext mapping of campuses: single Company with campus cost centers
    (section 5.1.2) versus separate Companies per campus (depends on
    whether campuses are separate legal/statutory reporting entities);
    how central costs are allocated to campuses.
-   Campus-level variations the institution needs: fees, academic
    calendar, approval chains, timetables.
-   Exact Vue, PrimeVue and Tailwind versions.
-   Keycloak versus another OIDC identity provider.
-   Same-origin reverse proxy versus separate frontend/API subdomains.
-   Browser session and token-handling implementation.
-   Exact Moodle SSO and API configuration.
-   KodeBook's current technology stack, API capabilities, identity
    model and event support.
-   Whether KodeBook needs university-specific instances later, while
    retaining independent hosting.
-   Detailed university regulatory, accreditation, payroll and reporting
    requirements.
-   Backup, retention, availability, RPO and RTO requirements.
-   Repository split and release/versioning strategy.
-   M8 providers and formats (waiting on third parties): payment
    gateway provider; SMS provider; NSFAF, NTA and NQA data formats
    and submission channels; AI assistant model provider, what data
    it may see, and where it runs.

Do not present these open items as already implemented or confirmed.

------------------------------------------------------------------------

### 14.1 Known upstream issues

Bugs in Frappe or its apps that EduCore works around. Report each upstream; remove the workaround once fixed.

| Issue | Seen in | Workaround |
|---|---|---|
| Login fails with `(1305, 'SAVEPOINT … does not exist')` when the same user signs in twice at the same moment: `frappe.sessions.update_user_metadata` wraps the User row update in a savepoint to absorb deadlocks, but MariaDB rolls back the whole transaction on a deadlock, so rolling back to the savepoint fails | Frappe v16.60.2 | The Vue app retries a sign-in once on a server error (`core/auth/session.ts`) and never shows the raw message |

## 15. Core architectural principles

1.  **The right interface per user:** the Vue app for students,
    academics, officers and self-service; a trimmed Frappe Desk for
    specialist back-office staff.
2.  **Frappe-backed operations:** Frappe and its apps provide backend
    business capabilities.
3.  **One source of truth:** avoid duplicate student, employee, finance
    and academic masters.
4.  **Modular monolith first:** keep the core manageable; integrate
    external platforms through clear boundaries.
5.  **Independent learning platforms:** Moodle and KodeBook remain
    separate services.
6.  **Unified identity:** OIDC-based SSO across EduCore, Moodle and
    KodeBook.
7.  **Official academic control:** EduCore owns validation, moderation
    and approval of official results.
8.  **Security by design:** enforce permissions server-side and isolate
    code execution.
9.  **Upgradeability:** extend upstream applications without unnecessary
    forks.
10. **Evidence-based implementation:** inspect the actual repository,
    installed versions and product capabilities before coding.
11. **Frappe v16 baseline:** build and test against the v16 release line
    only.
12. **One university, many campuses:** a single installation serves all
    campuses, with campus-scoped data and permissions and consolidated
    university reporting.

**The goal is to build a maintainable university operating platform, not
merely a collection of screens or disconnected applications.**
