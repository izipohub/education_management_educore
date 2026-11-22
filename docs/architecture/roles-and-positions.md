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
