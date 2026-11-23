# Re-registration of continuing students

Status (2026-11-22): built (`educore/registration`, `educore.api.v1.registration`, Vue pages `/registration` for
students and `/registrations` for faculty officers).

## Decisions (product owner, 2026-11-22)

| Question | Decision |
|---|---|
| Who registers a returning student | **The student, online**; the faculty officer approves (or returns it with a note) |
| What blocks registration | **Outstanding fees**, a **registration deposit**, **academic standing** and the **registration window** (with late registration and a late fee); each set by the university |

## How it works

1. The Registrar opens a **Registration Period** for the academic year: opens, closes, late registration until,
   late fee.
2. A returning student (one with a submitted enrolment in an earlier year) opens Registration in the Vue app. Their
   year of study is the number of earlier years enrolled plus one. The year's courses come from the programme's
   curriculum (each Program Course has a year of study and a semester); required courses are chosen and cannot be
   dropped; courses from other years can be added (repeats, catch-up), within the credit limit.
3. What blocks them is listed in plain words: standing On hold or Excluded (with the faculty's note), fees owed
   from earlier years above the allowed balance, the deposit not yet paid (advance payments not yet set against an
   invoice), the period not open. They can save a draft while blocked, but not submit.
4. The faculty officer (scoped by faculty and campus) sees submitted registrations, opens the course list on
   request, and approves or returns them with a note the student sees. Approving submits the year's Program
   Enrollment as a system action: Education creates the course enrolments and EduCore invoices the year's fees,
   plus the late fee for a late registration, recording who approved.

| Setting | Where | Default |
|---|---|---|
| Largest outstanding balance allowed | Registration Settings | N$ 0 |
| Deposit: none, an amount, or a percent of the year's fees | Registration Settings | 20% |
| Most credits per year (0: no limit) | Registration Settings | 0 |
| Faculty officer approves (off: approved on submission) | Registration Settings | on |
| Dates, late registration, late fee | Registration Period (per academic year) | |
| Academic standing and note | Student | Good standing |

## Later

- **Next: course scheduling in the curriculum (academic side).** Each Program Course already carries its year of
  study and when it runs (`educore_semester`: Semester 1, Semester 2 or Year, i.e. full year), but it is set only
  in Desk. Wanted: a screen in the Vue app where the academic side (faculty officer, HOD, Registrar) lays out
  each programme's curriculum by year and semester, with credits per semester, and moves courses between Semester 1,
  Semester 2 and full year. The semester then shows on the proof of registration (a column, courses grouped by
  semester, credits per semester), in the student's course choice and in the registration approval page.
- Academic standing set automatically from examination results (examinations module).
- Repeats and prerequisites from results, instead of the student choosing other years' courses freely.
- Student fee payments matched from the bank statement by student number (as application fees are today).
- Registration screens for the Registrar: periods and settings in the Vue app (Desk for now).
