# Terminology

EduCore uses the words Namibian universities use, so registry, admissions and finance staff recognise their own
processes. Where UNAM and NUST differ, EduCore follows the more common term and lets the university rename labels
later. Checked against their published guides on 2026-11-23 (sources below).

| EduCore says | Meaning | Not |
|---|---|---|
| **Entry pathway** | A way into the university: School leaver, Mature Age Entry, Recognition of Prior Learning, Credit transfer, Re-admission, Postgraduate (UNAM: "alternative entry pathways") | Route, admission type |
| **Mature Age Entry (MAE)** | Admission without the school requirements: at least 25 on the first day of the academic year, five years of relevant work experience (UNAM 2027), and the MAE examination | Mature age |
| **Recognition of Prior Learning (RPL)** | Admission (or credit) for learning gained through work and life, assessed against the programme | |
| **Credit transfer** | Credits from another accredited institution towards the programme; "admission with advanced standing" (NUST) | Transfer |
| **Re-admission** | A former student returning after an interruption | Resumption |
| **Admission points**, **Admission Point Scale** | Points from school-leaving results (best subjects), against a programme's minimum (NUST) | Score |
| **Programme**, **programme offering** | A qualification; its offering at one campus in one mode of study | Course (a course is a module within a programme) |
| **Intake** | The applications for one academic year | |
| **Offer**, **accept**, **decline**, **lapsed** | The admission decision and the applicant's response | |
| **First-year registration** | Registering an admitted applicant as a student: student number, login, the year's fees | Enrolment (used in Frappe's data model, not on screen) |
| **Registration** (returning students) | Each year's registration for the year's courses; approved by the faculty officer | Re-enrolment |
| **Registration deposit** | The minimum payment before registering (UNAM: "minimum deposit at academic registration") | |
| **Academic standing**: Good standing, Probation, On hold, Excluded | Whether a student may continue | |
| **Local** and **international** applicants | Citizens and permanent residents of the home country, and everyone else (fees, documents) | Home |
| **NQA evaluation** | The Namibia Qualifications Authority's evaluation of a foreign qualification | |

## Known gaps

- Fees and documents distinguish **Namibian, SADC and non-SADC** applicants at UNAM (different deposits), and NUST
  does not require an NQA evaluation of SADC school results. EduCore has local and international only: add SADC as
  a third group.
- The Mature Age Entry examination is not recorded yet (sitting, result, pass mark: UNAM 50% average for degrees,
  40% for diplomas, no paper below 40%).

## Sources

- UNAM, [2027 Undergraduate Programmes: General Admission Requirements](https://www.unam.edu.na/wp-content/uploads/2026/07/2027-All-Programmes.pdf)
- UNAM, [2026 Undergraduate Programmes Booklet](https://www.unam.edu.na/wp-content/uploads/2025/11/2026_Undergraduate_Programmes_Booklet.pdf)
- UNAM, [2026 Fees Prospectus](https://www.unam.edu.na/wp-content/uploads/2026/01/2026-Fees-Prospectus.pdf)
- NUST, [Guide to Prospective Students 2027](https://www.nust.na/sites/default/files/docs-forms/Guide_to_Prospective_Students_2027.pdf)
- NUST, [Admissions](https://www.nust.na/admissions)
