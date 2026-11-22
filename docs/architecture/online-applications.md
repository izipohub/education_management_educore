# Online applications — proposal

Status (2026-11-22): **phases 1 and 2 built** (EFT fee matching and document verification; DPO cards wait for the merchant account) (applicant portal: `educore.api.v1.apply`, `educore/admissions`, the Vue
pages `/apply`, `/apply/register`, `/application`). Phases 2–5 are proposals. Decisions still open are marked
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
| 4 | Number of choices per application | **3, ranked** |

Still open:

| # | Decision | Recommendation |
|---|---|---|
| 5 | Points scale and requirements | Load the university's own published scale; do not copy UNAM's or NUST's |
| 6 | Results verification | Reviewer compares with the uploaded statement; ask DNEA whether a results file or service is available to universities (not found publicly) |
| 7 | Pathways online in phase 1 | School leaver, international; then mature age, advanced standing, postgraduate |
| 8 | Who decides | Admissions officers and the registrar (as now); faculty officers comment |
| 9 | SMS notifications | Optional, later; email first |
| 10 | Retention of unsuccessful applications | Ask the university's legal/records office |

## 5. Phases

1. **Applicant portal**: account, intake, pathway, three ranked choices, secondary school from the school list,
   results with points and eligibility flags, document upload (certified copies), submit, status checklist.
2. **Fee and verification**: DPO card payment, EFT reference with bank-statement matching, waivers, per-document
   verification (including the certification stamp) and re-upload, completeness in the staff queue.
3. **Offers**: offer letters, accept/decline, deadline release of places, notifications.
4. **More pathways**: mature age, advanced standing / RPL, postgraduate, resumption.
5. **Integrations**: DNEA results (if offered), NQA, SMS; the Ministry's school register as a refreshable feed.

Before phase 2 the university needs a **DPO merchant account** (API tokens, NAD settlement terms). Before phase 1
goes live it needs the **school register** from the Ministry's EMIS unit and DNEA, and its own **points scale**.

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
