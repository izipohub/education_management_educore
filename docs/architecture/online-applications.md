# Online applications — proposal

Status (2026-11-22): **phases 1 to 4 built**: applicant portal, EFT fee matching and document verification (DPO
cards wait for the merchant account), offers and notifications, and the pathways (applicant portal: `educore.api.v1.apply`,
`educore/admissions`, the Vue pages `/apply`, `/apply/register`, `/application`). Phase 5 is a proposal. Decisions still open are marked
**Decide**.

## 1. How Namibian universities do it today

From the universities' own published guides (sources at the end):

| | UNAM | NUST |
|---|---|---|
| System | Online application page on unam.edu.na | Adapt IT **ITS Integrator** with its web front end **Student iEnabler** (ienabler.nust.na) |
| Application fee | N$ 150 Namibian, N$ 300 international | N$ 150 online (undergraduate); N$ 240 on the manual form |
| Paying | Bank deposit / EFT to the university account, **proof of payment uploaded**; no application processed without it | Debit or credit card online |
| Documents | **Certified copies** (ID, birth certificate, school leaving certificate); UNAM keeps them | Scanned **PDFs**, certified, in English; foreign qualifications first evaluated by the **NQA** |
| School results | Typed in by the applicant | Typed in by the applicant (Grade 11/12) |
| Selection | Points on the UNAM Evaluation Scale: at least 24 (NSSCO/NSSCH), English at least D; schemes with lower bars | Points on the NUST Admission Point Scale: at least 25 in five subjects, English at least E; programmes set more |
| Login | — | Applicant-chosen **5-digit PIN** |
| Not online | — | Postgraduate, Mature Age Entry, Advanced Standing, Resumption: **manual forms only** |
| Tracking | — | Confirmation and progress tracking |

What this shows, and where EduCore can do better:

1. **Payment is reconciled by hand.** A bank deposit plus an uploaded proof of payment means someone matches
   slips to applications. A unique payment reference per application, matched automatically against the bank
   statement in ERPNext, removes that work; card payment removes it entirely.
2. **Certified copies of scans add cost, not trust.** An applicant pays a commissioner of oaths, then uploads a
   scan of the stamp, which proves little. Checking originals once, at registration, would be cheaper for
   applicants. *Decided: certified copies stay required at application (section 4); EduCore makes checking the
   stamp part of each document's verification.*
3. **Self-reported results are re-checked by eye.** Results typed by the applicant must be compared with the
   uploaded certificate. Structured entry lets EduCore compute the points and flag eligibility at once; a
   reviewer then only confirms the certificate matches.
4. **Whole groups of applicants are still on paper.** Mature age, advanced standing, resumption and
   postgraduate applications belong online too, with their own document lists.
5. **A PIN is weak authentication.** Applicants get a proper account (email + password, verified email), later
   single sign-on (AGENT.md 7).

## 2. Proposed applicant journey

```
Create account (email verified)
  → Start application for an intake (one per intake)
      → Pathway: school leaver · mature age · advanced standing / RPL · postgraduate · international
      → Personal details, national ID / passport
      → Up to 3 ranked choices of programme offering (programme + campus + mode)
      → School results (subject, level, grade) → points and eligibility computed per choice
      → Documents: the list for the pathway, uploaded as PDF/JPG
      → Application fee: card, or EFT with the application's own reference, or approved waiver
      → Submit (declaration = e-signature)
  → Track: checklist of what is complete / verified / missing; re-upload a rejected document
  → Decision per choice (existing admission workflow, capacity-checked)
  → Offer letter (PDF) → accept or decline by a deadline
  → Accepted offer → registry enrolment (existing), where originals are checked
```

## 3. Requirements by area

### 3.1 Intakes and windows
- An **intake** (Education's *Student Admission*) has the academic year, opening and closing dates, an optional
  late window with a late fee, and the offerings it admits to.
- One application per applicant per intake; choices replace multiple applications. Duplicate detection on
  national ID / passport number.

### 3.2 Entry requirements and points
- A **points scale** per university, configurable (NSSCO, NSSCAS/NSSCH grade → points); EduCore does not hard-code
  UNAM's or NUST's tables (AGENT.md 9: no hard-coded policy).
- **Requirements per offering**: minimum points over the best *n* subjects, required subjects with minimum
  grades (English, Mathematics…), and alternative routes (mature age test, a lower bar for a recognised scheme).
- The system **flags** each choice: meets / does not meet / needs review. People still decide; the flag makes the
  queue sortable and catches obvious errors.

### 3.3 Documents
- A **requirement matrix** by pathway and nationality, configurable. Typical: ID or passport, birth certificate,
  NSSC statement or certificate, marriage certificate when the name differs, NQA evaluation (foreign
  qualifications), transcripts (advanced standing, postgraduate), CV and employer letter (mature age), study
  permit (international).
- Upload rules: PDF or image, size limit, stored as **private** files, a checksum kept for audit.
- **Verification per document**: Pending → Verified / Rejected with a reason (unreadable, expired, name
  mismatch, wrong document). A rejection notifies the applicant to replace that one document.
- An application is **complete** when every required document is verified and the fee is settled.

### 3.4 Application fee
- Amount by intake and applicant type (Namibian / international), non-refundable; late fee in the late window.
- **EFT**: each application gets a unique reference; ERPNext's bank statement import matches it and marks the fee
  paid (no proof-of-payment upload). **Card**: through **DPO** (decided, section 4).
- **Waivers**: recorded with a reason and approver (e.g. a scheme for marginalised applicants).
- Accounting: an application-fee income account, posted to the campus cost center of the first choice, money into
  the central bank account (AGENT.md 5.1.2).

### 3.5 Staff side (extends the existing admissions queue)
- Columns for completeness (documents verified, fee paid) and eligibility per choice; filters for "ready to decide".
- A document verification screen: the file beside the applicant's typed details.
- Bulk decisions for clear cases; the existing campus scope, roles, capacity checks and reasons stay.
- Faculty officers can comment on applications for their programmes (**Decide** whether they also decide).

### 3.6 Offers and acceptance
- An offer letter per approved choice (PDF, university branding), with an acceptance deadline.
- Accept → ready for enrolment; decline or no answer by the deadline → the place returns to capacity.

### 3.7 Notifications, privacy, audit
- Email (and SMS, **Decide** provider) at submission, document rejection, decision, offer, deadline reminders.
- Applicant data is personal data: private files, campus-scoped staff access (already enforced), a retention
  period for unsuccessful applications (**Decide**), and every decision and verification logged.

### 3.8 Secondary schools
- How ITS does it: ITS Integrator keeps its own secondary-school code table, maintained by university staff
  ("Maintain Secondary School Information", SSCHL-1), offered as a pick-list on the application form.
- EduCore: a **Secondary School** list maintained by admissions: name, region, town, Ministry **EMIS number**,
  DNEA **examination centre number** (as printed on NSSC results), government / private, active.
- Loaded from the Ministry of Education's school register; no current downloadable register with codes was found
  publicly, so ask the Ministry's EMIS unit and DNEA for it.
- Applicants search and pick their school; "my school is not listed" takes a typed name, flagged for admissions to
  add or merge. Foreign schools: country and name.

## 4. Decisions

Decided 2026-11-22 by the product owner:

| # | Decision | Outcome |
|---|---|---|
| 1 | Certified copies at application? | **Required.** Admissions checks the certification stamp when verifying each document; a maximum age of the certification date is configurable |
| 2 | Payment methods | **Card through DPO** and **EFT** with the application's unique reference |
| 3 | Card payment gateway | **DPO** (holds a payment facilitator licence in Namibia). The university opens a DPO merchant account; API tokens and NAD settlement terms come from DPO at onboarding |
| 4 | Number of choices per application | **3, ranked** (Admission Settings: the university can change it) |
| 7 | Pathways | **All online**: school leaver, mature age entry, advanced standing / transfer, resumption of studies (undergraduate); postgraduate. International is the applicant's status, on any pathway |
| 11 | Mature Age Entry | **From 25** on the first day of the academic year, with **5 years** of relevant work experience (UNAM's rule; was 23 until 2026-11-23), set on the pathway |
| 12 | Postgraduate eligibility | **Automatic check** of the prior qualification's NQF level and average against the programme's minimums; anything unusual (foreign, NQF or average missing) is "Needs review" |

Still open:

| # | Decision | Recommendation |
|---|---|---|
| 5 | Points scale and requirements | Load the university's own published scale; do not copy UNAM's or NUST's |
| 6 | Results verification | Reviewer compares with the uploaded statement; ask DNEA whether a results file or service is available to universities (not found publicly) |
| 8 | Who decides | Admissions officers and the registrar (as now); faculty officers comment |
| 9 | SMS notifications | Optional, later; email first |
| 10 | Retention of unsuccessful applications | Ask the university's legal/records office |

## 5. Phases

1. **Applicant portal**: account, intake, pathway, three ranked choices, secondary school from the school list,
   results with points and eligibility flags, document upload (certified copies), submit, status checklist.
2. **Fee and verification**: DPO card payment, EFT reference with bank-statement matching, waivers, per-document
   verification (including the certification stamp) and re-upload, completeness in the staff queue.
3. **Offers** (built): see section 7.
4. **More pathways** (built): see section 6.
5. **Integrations**: DNEA results (if offered), NQA, SMS; the Ministry's school register as a refreshable feed.

Before phase 2 the university needs a **DPO merchant account** (API tokens, NAD settlement terms). Before phase 1
goes live it needs the **school register** from the Ministry's EMIS unit and DNEA, and its own **points scale**.

## 6. Pathways (built)

Each university decides its own admission rules; EduCore reads them from settings and never fixes them in code.
Six entry pathways (names as in docs/architecture/terminology.md) are installed once, as a starting point (`educore.admissions.pathways.ensure_defaults`), and are then
the university's to change, add to or close:

| Pathway | Level | Judged on | Eligibility | Asks for |
|---|---|---|---|---|
| School leaver | Undergraduate | School results | Points and subject requirements (international: Needs review) | School, NSSC results; foreign school certificate and NQA evaluation if international |
| Mature Age Entry | Undergraduate | Work experience | Minimum age (25) and years of work (5) are rules; otherwise Needs review (the MAE examination) | Jobs; CV, proof of employment, motivation letter |
| Recognition of Prior Learning | Undergraduate | Work experience | Needs review: learning assessed against the programme | RPL portfolio, CV |
| Credit transfer | Undergraduate | Studies elsewhere | Needs review: the faculty decides credits (admission with advanced standing) | School results and studies after school; academic record, course outlines |
| Re-admission | Undergraduate | Studies here | Needs review: standing, exclusion, fees; the earlier student record is found | Previous student number |
| Postgraduate | Postgraduate | Prior qualification | Programme's minimum NQF level and average | Qualifications, 2 referees; degree certificate, academic record, CV, motivation letter |

The Registrar sets all of it in the Vue app's **Admission setup** screen (`/admission-setup`,
`educore.api.v1.admission_setup`): rules, offers, fees, pathways, documents, each programme's entry requirements
and the points scale. Saving the university's own scale clears the placeholder flag. What the university sets, and
where it is stored:

| Rule | Where |
|---|---|
| Home country (others are international: other documents and fee), number of choices, fees, certification age, file size, points scale | Admission Settings |
| Whether approval waits for verified documents, and for the fee | Admission Settings |
| Each pathway: level, evidence, minimum age, referees, documents (for everyone, home or international applicants; required or optional), open or closed, order | Admission Pathway |
| Identity documents for everyone, home or international applicants | Admission Document Type ("Pathway only": asked for only by the pathways that list it) |
| Level of study, minimum points and subjects, minimum prior NQF level and average | The programme (Entry Requirements) |

Choices must be at the pathway's level; changing to a pathway at the other level removes the programmes chosen (the
applicant is told before saving).

## 7. Offers and notifications (built)

Approving an online application makes an offer (`educore.admissions.offers`). Staff may add conditions, which appear
in the offer letter. The applicant accepts or declines in the portal by the deadline; declining moves the
application to **Declined**, and an unanswered offer becomes **Lapsed** the day after its deadline (daily job). Both
release the place: intake capacity counts Approved and Admitted only. Only the registrar can reconsider a declined
or lapsed application. Admissions can extend a deadline. Paper applications are answered in person: no deadline,
no portal response.

| Rule | Setting (Admission Settings) | Default |
|---|---|---|
| Days to accept an offer | `offer_response_days` | 14 |
| Reminder before the deadline | `offer_reminder_days` (0: none) | 3 |
| Enrol online applicants only once they accept | `enrolment_needs_acceptance` | on |
| Email applicants | `notify_applicants` | on |

Emails (`educore.admissions.notify`), queued with the application as reference: submission received, a rejected
document (with the reason), offer made, reminder, offer accepted, offer declined, offer lapsed, unsuccessful. A site
with no outgoing email account notes each unsent email on the application's timeline instead of failing.

Access fix with this phase: an application belongs to its first choice's campus; later choices at other campuses no
longer hide it from that campus's officers (Applicant Choice.campus ignores User Permissions).

## Sources

- UNAM: [2027 undergraduate programmes](https://www.unam.edu.na/wp-content/uploads/2026/07/2027-All-Programmes.pdf),
  [admission requirements](https://www.unam.edu.na/requirements/),
  [international students](https://unam.edu.na/apply-to-unam/international-students),
  [2025 applications notice](https://www.unam.edu.na/wp-content/uploads/2024/06/2025-Applications-Now-Open-4B.pdf),
  [online applications manual 2025](https://unam.edu.na/wp-content/uploads/2025/01/Online-Applications-Manual-Final-2025.pdf)
- NUST: [Guide to Prospective Students 2027](https://www.nust.na/sites/default/files/docs-forms/Guide-to-Prospective-Students-2027.pdf),
  [Guide 2026](https://www.nust.na/sites/default/files/2026-Final-Guide-to-Prospective-Students.pdf),
  [2027 undergraduate application form](https://www.nust.na/sites/default/files/docs-forms/2027_eUndergraduate_Application_Form.pdf),
  [2025 application information](https://www.nust.na/sites/default/files/2024-09/Application-Admission_Information_2025.pdf)
- ITS Integrator / iEnabler: [Adapt IT education](https://adaptit.com/education),
  [ITWeb: iEnabler at ORBIT FET College](https://www.itweb.co.za/article/its-ienabler-streamlines-student-registrations-at-orbit-fet-college/XnWJad7bYJwvbjO1),
  [ITWeb: UJ online registration](https://www.itweb.co.za/article/uj-registered-over-5-000-students-on-one-day/Kjlyr7wL8P4Mk6am)
- Other: [DNEA, Ministry of Education](https://moe.gov.na/index.php/dep/dep-sfe/directorate-of-national-examinations-and-assessment-dnea),
  [IUM online application guide](https://ium.edu.na/Files/Online%20Application%20Guide.pdf)
- Schools: [ITS "Maintain Secondary School Information" (CPUT manual)](https://alecto.cput.ac.za/manuals/documents/sschl-1.html),
  [List of schools in Namibia](https://en.wikipedia.org/wiki/List_of_schools_in_Namibia)
- DPO: [DPO receives payment facilitator licence in Namibia (New Era)](https://neweralive.na/posts/dpo-receives-payment-facilitator-licence-in-namibia),
  [DPO Group in Namibia (The Namibian)](https://www.namibian.com.na/dpo-group-offers-innovative-payment-solutions/)

Fees, dates and minimums change each cycle and some published documents disagree (for example N$ 150 vs N$ 240
at NUST); treat the figures above as examples, not policy.
