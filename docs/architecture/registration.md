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
  fee, course changes until) and the rules (outstanding balance allowed, deposit, most credits per year, faculty approval).

- **Sponsors** (Finance, Financial Aid): a sponsor pays a student's year in full, a percent or an amount; once the
  year is invoiced its share moves off the student's invoice (credit note, "Sponsored by ...") onto an invoice to the
  sponsor, on the same campus. The late fee stays the student's. The deposit is worked out on the student's own share;
  a year a sponsor took over after the student paid becomes a credit towards the next deposit. Sponsors pay by EFT
  with their number (SPN-00001) as the reference, matched hourly (`educore.finance.sponsors`).
- **Student payments** (Finance): fees paid by EFT with the student number as the reference are matched hourly from
  the bank statement (educore.finance.student_payments): a Payment Entry against the oldest unpaid invoices, the bank
  line reconciled, any remainder kept as an advance, which counts towards the next year's deposit. Deposits without
  a student number wait for Finance to assign them. Students see the bank details and their reference on My studies.

- **Academic standing** is set from published results (educore.academics.results): probation at the university's
  line of credits not passed, good standing otherwise; On hold and Excluded stay as set by hand.
- **Prerequisites and repeats** (from published results, educore.registration.rules.course_states): the faculty sets
  a course's prerequisites in the curriculum (on the course, so they hold wherever it is taught; no circles). At
  registration a course passed already is not offered; a course not passed earlier is a repeat, offered first and,
  if required, must be taken; a course whose prerequisite is not passed cannot be chosen, with the reason shown;
  the year's required courses must be taken unless a prerequisite blocks them. The approval page marks repeats.
- **Course changes** (educore.api.v1.course_changes): once their registration is approved, a student asks to add or
  drop courses until the year's course change date, one request at a time; the faculty officer approves or declines
  with a reason. The registration rules hold for the courses after the change (required courses stay, prerequisites,
  credit limit). Approving updates the registration's courses and Course Enrollments; the class lists then show as
  out of date on Teaching. The year's fees do not depend on the courses, so no invoice changes.
- **Interrupting or cancelling studies** (educore.api.v1.studies_requests): the student asks from My studies, with
  the last day attending, a reason and, to interrupt, the year they return in; the Registry (own campus) approves or
  declines with a reason. Either way the student comes off this year's class lists. Interrupted: registration is
  blocked until the return year (the Registry can lift it for an early return; approving the return year's
  registration clears it). Cancelled: the student is no longer active, and returning means applying again. What is
  owed or refunded is Finance's to decide.
- **Emails to students** (educore.academics.notify), when the Registrar's setting "Email students" is on: the
  registration approved or returned, a course change or a request about their studies decided (with the reason
  when declined), results published (one email per student, however many classes are published together),
  supplementary results published, and the programme completed. Queued through Frappe's Email Queue with the
  deciding record as the reference; without an outgoing email account, a note on that record's timeline instead.

## Later


