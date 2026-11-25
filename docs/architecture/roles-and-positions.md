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

Positions with an EduCore role but no upstream roles (Head of Department, Financial Aid Officer, Student
Affairs Officer, Accommodation Officer, Facilities Manager, the portal users) can log in but do not see
anything yet: their screens and permissions come with the EduCore modules that serve them.

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
| Interrupting or cancelling studies | Student asks; Registry Officer, Registrar decide (Students → Requests) | |
| Students (records, proof of registration) | Registry Officer, Registrar | Faculty Officer, Dean, Head of Department, Campus Director, Executive Management, Examinations Officer, Student Affairs Officer, Financial Aid Officer |
| Teaching (classes from approved registrations, lecturers allocated) | Head of Department, Dean (own department or faculty) | Faculty Officer, Timetable Officer, Registrar, Campus Director; lecturers see their own classes in My teaching |
| Marks (enter, submit) | Lecturer (own classes, from My teaching) | |
| Examinations: moderate, or return to the lecturer | Head of Department, Dean (own department or faculty) | Registrar, Faculty Officer |
| Examinations: approve (board meeting), return to the department, publish | Examinations Officer (own campus) | Registrar, Faculty Officer |
| Supplementary and special examinations: grant a special for an absence with a valid reason; publish the sitting's results (board meeting) | Examinations Officer (own campus) | Registrar, Faculty Officer |
| Supplementary and special marks (enter, submit) | Lecturer (own classes, once the first results are published) | |
| Examination rules (CA weight, admission, pass, supplementary band and cap, grading scale, probation) | Registrar | Examinations Officer and the others above read them |
| Results; academic record (PDF, interim until completion) | Student (own, once published) | Registry Officer, Registrar and the others who read Students download any student's record |
| Graduation: progress towards each programme's requirements (required courses passed, credits) | Examinations Officer, Faculty Officer, Dean (own campus or faculty) prepare the list for the Senate | Registry Officer |
| Graduation: record the completions the Senate approved (the academic record then reads final) | Registrar | |
| Award certificates and the graduation list (PDF; the original certificate is handed over once) | Registrar, Registry Officer | |
| Curriculum (courses by year and semester) | Faculty Officer, Head of Department, Dean (own faculty) | Registrar (publishes it), Timetable Officer, Examinations Officer, Quality Assurance Officer |
| Admission setup (rules, pathways, documents, entry requirements, points) | Registrar | |
| Registration setup (periods' dates, credit limit, faculty approval) | Registrar | |
| Integrations (Moodle: address, token, sync) | ICT Administrator (System Manager) | The class page shows its Moodle course to the faculty |
| Fee settings (application fees, ERPNext accounts, deposit, balance allowed, late fee) | Bursar | Finance Officer, Student Fees Officer; shown read only on the Registrar's setup screens |
| Application fees (outstanding, paid, waived; waiving) | Bursar, Finance Officer, Student Fees Officer | |
| Student payments (matched from the bank statement by student number; assigning deposits without one) | Bursar, Finance Officer, Student Fees Officer | |

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
