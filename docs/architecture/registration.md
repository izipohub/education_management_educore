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

## In the app

- **Curriculum**, laid out by the academic side (faculty officer, head of department, dean, each in their own
  faculty) and read by the Registrar's office, which publishes it: each programme's courses by year of study and
  when they run, Semester 1, Semester 2 or the full year, with credits per period. Registration, the approval page,
  the student record and the proof of registration all read it. Later: changes approved by Senate before they apply.
- **Registration setup** (Registrar): each academic year's period (opens, closes, late registration until, late
  fee) and the rules (outstanding balance allowed, deposit, most credits per year, faculty approval).

- **Student payments** (Finance): fees paid by EFT with the student number as the reference are matched hourly from
  the bank statement (educore.finance.student_payments): a Payment Entry against the oldest unpaid invoices, the bank
  line reconciled, any remainder kept as an advance, which counts towards the next year's deposit. Deposits without
  a student number wait for Finance to assign them. Students see the bank details and their reference on My studies.

- **Prerequisites and repeats** (from published results, educore.registration.rules.course_states): the faculty sets
  a course's prerequisites in the curriculum (on the course, so they hold wherever it is taught; no circles). At
  registration a course passed already is not offered; a course not passed earlier is a repeat, offered first and,
  if required, must be taken; a course whose prerequisite is not passed cannot be chosen, with the reason shown;
  the year's required courses must be taken unless a prerequisite blocks them. The approval page marks repeats.

## Later

- Academic standing set automatically from examination results (examinations module).
