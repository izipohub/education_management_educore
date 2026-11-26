# Roles and positions

Source of truth: `apps/educore/educore/access/roles.py`, synced on install and every migrate. Change
positions there, not in the Role Profile form, or the next migrate puts them back.

- **Role:** a permission building block. EduCore adds a role only where Frappe, ERPNext, HRMS or Education
  has none for the job; their own roles are reused.
- **Position:** a Role Profile, the EduCore role of the job plus the upstream roles it needs. A person can
  hold several positions (for example Head of Department and Lecturer).
- **Scope** (which campus, which faculty) is not a role. It will be User Permissions on Campus and Faculty,
  once those records exist (AGENT.md 5.1.1). Until then a role applies university-wide.
- Every staff position also has **University Staff**, **Employee** and **Employee Self Service**. ERPNext
  grants the last two only once HR links the person to an Employee record.

| Group | Position | EduCore role | Upstream roles |
|---|---|---|---|
| Executive and academic leadership | Vice-Chancellor | Executive Management | Prepared Report User |
| | Pro-Vice-Chancellor | Executive Management | Prepared Report User |
| | Campus Director | Campus Director | Prepared Report User |
| | Dean | Dean | Prepared Report User |
| | Head of Department | Head of Department | |
| Academic administration | Registrar | Registrar | Education Manager, Academics User, Prepared Report User |
| | Registry Officer | Registry Officer | Academics User |
| | Admissions Officer | Admissions Officer | Academics User |
| | Faculty Officer | Faculty Officer | Academics User |
| | Examinations Officer | Examinations Officer | Academics User |
| | Timetable Officer | Timetable Officer | Academics User |
| | Quality Assurance Officer | Quality Assurance Officer | Prepared Report User |
| Teaching | Lecturer | Lecturer | Instructor |
| Student services | Student Affairs Officer | Student Affairs Officer | |
| | Accommodation Officer | Accommodation Officer | |
| Finance | Bursar | Bursar | Accounts Manager, Prepared Report User |
| | Finance Officer | Finance Officer | Accounts User |
| | Student Fees Officer | Student Fees Officer | Accounts User |
| | Cashier | Cashier | Accounts User |
| | Financial Aid Officer | Financial Aid Officer | |
| | Internal Auditor | | Auditor, Prepared Report User |
| Human resources | HR Manager | | HR Manager, HR User |
| | HR Officer | | HR User |
| | Payroll Officer | | HR User |
| Procurement and stores | Procurement Manager | | Purchase Manager, Purchase Master Manager, Purchase User |
| | Procurement Officer | | Purchase User |
| | Stores Officer | | Stock User |
| Campus operations and ICT | Facilities Manager | Facilities Manager | |
| | ICT Administrator | | System Manager |
| Students and outside users | Student | | Student |
| | Applicant | Applicant (portal) | |
| | Guardian | | Guardian |
| | Sponsor | Sponsor (portal) | |
| | External Examiner | External Examiner (portal) | |

Positions whose modules are not built yet (Facilities Manager; the Guardian, Sponsor and External Examiner portals)
can log in but see only their home page; their screens come with those modules. Student Affairs, Financial Aid and
Accommodation officers read student records until their own modules exist.

## Who does what in the Vue app

Each screen belongs to the office whose work it is; others may read it where their own work needs it. The server
checks the same roles (the `*_ROLES` constants in `educore/api/v1`), and campus and faculty User Permissions narrow
what each person sees.

| Screen | Does the work | Reads it as well |
|---|---|---|
| Admissions (decide, capture paper forms) | Admissions Officer | Registrar (oversight, reconsiders rejections) |
| Registration: first-year students | Registry Officer | Registrar |
| Registration: senior students (approve) | Faculty Officer | Registrar (exceptions) |
| Course changes after approval (add or drop, until the course change date) | Student asks; Faculty Officer approves or declines | Registrar |
| Interrupting or cancelling studies, or moving to another campus | Student asks; Registry Officer (of the student's campus), Registrar decide (Students → Requests) | After a move, the new campus's Registry and Finance look after the student |
| A student's status history (admission, registrations, interruptions, moves, holds, completion) | | Everyone who reads Students sees it on the student's record |
| Students (records, proof of registration) | Registry Officer, Registrar | Faculty Officer, Dean, Head of Department, Campus Director, Executive Management, Examinations Officer, Student Affairs Officer, Financial Aid Officer, Accommodation Officer |
| Teaching (classes from approved registrations, lecturers allocated) | Head of Department, Dean (own department or faculty) | Faculty Officer, Timetable Officer, Registrar, Campus Director, Examinations Officer, Quality Assurance Officer, Executive Management (own campus where limited to one); lecturers see their own classes in My modules |
| Academic staff (lecturers: department, campuses, left or active; each lecturer's classes). A login given the Lecturer position gets its lecturer record automatically, department and campuses from its User Permissions | Head of Department, Dean (own department or faculty); HR Manager, HR User link the HR staff record | Faculty Officer, Registrar, Campus Director, Timetable Officer, Quality Assurance Officer, Executive Management |
| Lecturer workload (each lecturer's modules, students, contact hours a week from the timetable and invigilation hours, per semester; also shown when allocating) | Head of Department, Dean and the others who read Academic staff (own department or faculty) | The rule (contact hours a week, at least and at most) is the Registrar's |
| Class attendance (a register per lesson, from the timetable; per day for a module with no timetable; excused absences left out; below the minimum flagged) | Lecturer (own modules, from My modules) | Head of Department, Dean and the others who read Teaching (class page); the student (own, My studies); minimum set by the Registrar with the examination rules |
| Gradebook (the module's assessments, of the faculty's types: each marked out of what the lecturer chooses, with its share of the CA; the scores, an online assessment's brought in from its Moodle activity; the CA worked out) | Lecturer (own modules, while the marks are with them; scores once the plan is approved) | The department sees the CA on the mark sheet and may adjust it when moderating |
| Assessment plan (the module's assessments and shares, before scores go in) | Lecturer proposes; Head of Department or Dean (own department or faculty, not of a module they teach) approves, or returns it with the reason | Examinations Officer, Registrar and the others who read Examinations |
| A student's assessments (each module's approved plan, due dates, Moodle links; their own scores and provisional CA) | Student (own, My studies → Assessments) | Whether scores show as marked or once published is the Registrar's (examination rules) |
| Assessment types (per faculty: online in Moodle or not, the highest share of the CA, in use or not) | Dean (own faculty) | Head of Department, Faculty Officer, Registrar, Examinations Officer, Quality Assurance Officer, Executive Management |
| Marks (enter, submit) | Lecturer (own modules, from My modules) | |
| Examinations: moderate, or return to the lecturer | Head of Department, Dean (own department or faculty) | Registrar, Faculty Officer, Campus Director, Quality Assurance Officer, Executive Management |
| Examinations: approve (board meeting), return to the department, publish | Examinations Officer (own campus) | Registrar, Faculty Officer |
| Supplementary and special examinations: grant a special for an absence with a valid reason; publish the sitting's results (board meeting) | Examinations Officer (own campus) | Registrar, Faculty Officer |
| Examination timetable: sessions, each class's paper (date, hours, rooms, invigilators) | Examinations Officer (own campus); the Registrar publishes the session | Registry Officer, Head of Department, Dean, Faculty Officer, Campus Director, Timetable Officer; students see their papers and invigilators their duties on the Timetable tab |
| Supplementary and special marks (enter, submit) | Lecturer (own classes, once the first results are published) | |
| Examination rules (CA weight, admission, pass, supplementary band and cap, grading scale, probation) | Registrar | Examinations Officer and the others above read them |
| Results; academic record (PDF, interim until completion) | Student (own, once published) | Registry Officer, Registrar and the others who read Students download any student's record |
| Graduation: progress towards each programme's requirements (required courses passed, credits) | Examinations Officer, Faculty Officer, Dean (own campus or faculty) prepare the list for the Senate | Registry Officer, Head of Department, Campus Director, Executive Management |
| Graduation: record the completions the Senate approved (the academic record then reads final) | Registrar | |
| Disciplinary cases (confidential: report, investigation, hearing, decision, appeal) | Any member of staff who teaches the student or works with their record reports; Student Affairs Officer (the student's campus) investigates, decides minor cases and records the committee's decision on serious ones; the Registrar decides appeals and sets the days to appeal | The student sees their case from the hearing on (never the investigation) and appeals on My studies; the reporter is told only that it reached Student Affairs |
| Service requests (a letter, a card replacement, a change of name, a results query, an IT account...: the student asks, the office answers) | The office the category names (Registry Officer, Student Affairs Officer, Faculty Officer, Examinations Officer, Student Fees Officer, Financial Aid Officer, Accommodation Officer, ICT), for its campuses and faculty | The Registrar oversees every office's; the categories (office, working days, fee, document needed) are the Registrar's; the student asks and follows on My studies, Requests |
| Official transcripts (students' requests: copies, collected, emailed or posted; issued once the fee is paid and the student is cleared, or declined with the reason) | Registrar, Registry Officer (own campus) | The student asks and follows it on My studies; the transcript fee and whether clearance is needed are the Bursar's (Fee settings) |
| Award certificates and the graduation list (PDF; the original certificate is handed over once) | Registrar, Registry Officer | |
| Timetable (each class's weekly times and rooms per semester) | Timetable Officer (own campus) | Head of Department, Dean, Faculty Officer, Registrar, Registry Officer, Facilities Manager, Campus Director, Examinations Officer, Executive Management; lecturers and students see their own week |
| Rooms (name, type, seats, in use) | Timetable Officer, Facilities Manager (own campus) | Everyone who reads the timetable |
| Curriculum (courses by year and semester) | Faculty Officer, Head of Department, Dean (own faculty) | Registrar (publishes it), Timetable Officer, Examinations Officer, Quality Assurance Officer, Registry Officer, Campus Director, Executive Management |
| Admission setup (rules, pathways, documents, funding routes and their documents, entry requirements, points) | Registrar | |
| Registration setup (periods' dates, credit limit, faculty approval) | Registrar | |
| Integrations (Moodle: address, token, sync) | ICT Administrator (System Manager) | The class page shows its Moodle course to the faculty |
| Fee settings (instalments: each year's due dates and shares; the transcript fee and whether transcripts need clearance; application fees by nationality: home, regional, international; the funding routes that pay no application fee; ERPNext accounts, deposit, balance allowed, late fee) | Bursar | Finance Officer, Student Fees Officer; shown read only on the Registrar's setup screens |
| Application fees (outstanding, paid, waived; waiving) | Bursar, Finance Officer, Student Fees Officer | |
| Student payments (matched from the bank statement by student number; assigning deposits without one to a student or a sponsor) | Bursar, Finance Officer, Student Fees Officer, Cashier | |
| Financial clearance (holds with a reason, placed and lifted; what each student owes; graduation and the award certificate need clearance, a setting) | Bursar, Finance Officer, Student Fees Officer (own campus) | Registry and the others who read Students see the hold on the record; the student sees it on My studies |
| Fee waivers (part of a student's fees for a year not charged: requested with the reason, then approved or rejected; an approved one is taken off the year's invoice by credit note) | Bursar decides (never their own request); Bursar, Finance Officer, Student Fees Officer (own campus) request | The waiver shows on the student's clearance page |
| Sponsors (bursaries, loan funds, employers: the students each pays for in a year, its invoices, payments by sponsor number, statement PDF) | Bursar, Finance Officer, Student Fees Officer, Financial Aid Officer | Student record shows who pays (Registry and the others who read Students) |

## Demo users (development only)

```
docker compose -f docker/frappe/docker-compose.yml exec frappe bash -lc \
  'cd frappe-bench && bench --site educore.localhost execute educore.access.demo_users.create'
```

One user per position, `<position>@educore.localhost` (for example `registrar@educore.localhost`,
`faculty-officer@educore.localhost`), password `Campus-Demo-2026` unless `EDUCORE_DEMO_PASSWORD` is set.
The script refuses to run on any site that is not `*.localhost`.

Then `educore.access.test_users.create` adds 77 users limited by campus and/or faculty and department
(`registry-officer.osh@…`, `dean.fst@…`, `lecturer.comp.osh@…`), through User Permissions on Campus,
Branch and Department. The full list is in `CREDS.md` (git-ignored).

Every staff role can read the Department tree (`educore/setup/permissions.py`); User Permissions then
narrow what each user sees.
