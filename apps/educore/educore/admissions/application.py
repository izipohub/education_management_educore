"""Online applications: points, eligibility per choice, and what a complete application needs.

The application is Education's Student Applicant (docs/architecture/online-applications.md). These rules run
from its validate hook (educore.academics.students.validate_applicant):

- Points: each result's points come from the university's scale (Admission Settings); the application's points
  are the best results in the configured number of subjects, one result per subject.
- Eligibility per choice: the programme's minimum points and subject requirements. A requirement names a subject
  (or a group such as English, which English Second Language counts as) and a minimum grade at a level; a result
  worth at least as many points meets it, so a higher level or a better grade does too. The result is a flag for
  staff, never a decision.
- Submitting (Draft → Applied) needs the declaration, at least one choice, the school and results for a school
  leaver, every required document, and certified copies certified recently enough, in an open intake.
"""

import frappe
from frappe import _
from frappe.utils import add_months, getdate, now_datetime, nowdate

MAX_CHOICES = 3
MEETS, FAILS, REVIEW = "Meets requirements", "Does not meet requirements", "Needs review"


def settings():
	return frappe.get_cached_doc("Admission Settings")


def _key(level: str, grade: str) -> tuple[str, str]:
	return (level or "").strip().upper(), (grade or "").strip().upper()


def scale() -> dict[tuple[str, str], int]:
	return {_key(row.level, row.grade): row.points for row in settings().points_scale}


def grade_points(level: str, grade: str) -> int | None:
	return scale().get(_key(level, grade))


# --- points --------------------------------------------------------------------------------------------


def score(doc) -> int:
	"""Sets each result's points and returns the application's points (best results, one per subject)"""
	best_per_subject: dict[str, int] = {}
	for row in doc.get("educore_results") or []:
		row.points = grade_points(row.level, row.grade)
		if row.points is not None:
			best_per_subject[row.subject] = max(best_per_subject.get(row.subject, 0), row.points)
	counted = sorted(best_per_subject.values(), reverse=True)[: settings().best_subjects or 5]
	return sum(counted)


# --- eligibility ---------------------------------------------------------------------------------------


def _counts_as(subject: str) -> set[str]:
	names = {subject}
	group = frappe.get_cached_value("School Subject", subject, "counts_as")
	if group:
		names.add(group)
	return names


def assess_choice(doc, offering: str) -> tuple[str, str]:
	"""(eligibility, why) for one choice"""
	program = frappe.get_cached_doc("Program", frappe.db.get_value("Programme Offering", offering, "program"))
	results = [r for r in doc.get("educore_results") or [] if r.points is not None]
	if doc.get("educore_pathway") == "International":
		return REVIEW, _("Foreign qualifications are assessed by admissions.")
	if not results:
		return REVIEW, _("No school results entered yet.")

	problems = []
	if program.get("educore_min_points") and (doc.educore_points or 0) < program.educore_min_points:
		problems.append(_("{0} points, {1} needed").format(doc.educore_points or 0, program.educore_min_points))

	for req in program.get("educore_subject_requirements") or []:
		needed = grade_points(req.level, req.grade)
		if needed is None:
			return REVIEW, _("The requirement {0} {1} {2} is not on the points scale.").format(req.subject, req.level, req.grade)
		best = max((r.points for r in results if req.subject in _counts_as(r.subject)), default=None)
		if best is None:
			problems.append(_("no result in {0}").format(req.subject))
		elif best < needed:
			problems.append(_("{0} below {1} {2}").format(req.subject, req.level, req.grade))

	if problems:
		note = "; ".join(problems)
		# first letter only: str.capitalize() would lowercase "NSSCO C"
		return FAILS, note[:1].upper() + note[1:]
	return MEETS, _("{0} points").format(doc.educore_points or 0)


def assess(doc):
	doc.educore_points = score(doc)
	for choice in doc.get("educore_choices") or []:
		choice.eligibility, choice.eligibility_note = assess_choice(doc, choice.programme_offering)


# --- drafts --------------------------------------------------------------------------------------------


def tidy_draft(doc):
	"""Ranks 1..n, at most three different active offerings; the first choice is the offering under decision"""
	choices = [c for c in doc.get("educore_choices") or [] if c.programme_offering]
	if len(choices) > MAX_CHOICES:
		frappe.throw(_("Choose at most {0} programmes").format(MAX_CHOICES))
	offerings = [c.programme_offering for c in choices]
	if len(set(offerings)) != len(offerings):
		frappe.throw(_("Each programme offering can be chosen once"))
	choices.sort(key=lambda c: c.rank or 99)
	for rank, choice in enumerate(choices, start=1):
		choice.rank = rank
		if not frappe.db.get_value("Programme Offering", choice.programme_offering, "is_active"):
			frappe.throw(_("{0} is not taking applications").format(choice.programme_offering))
	doc.educore_choices = choices
	if choices:
		doc.educore_programme_offering = choices[0].programme_offering

	seen = set()
	for row in doc.get("educore_results") or []:
		if (row.subject, row.level) in seen:
			frappe.throw(_("{0} at {1} is entered twice").format(row.subject, row.level))
		seen.add((row.subject, row.level))


# --- submitting ----------------------------------------------------------------------------------------


def required_documents(doc) -> list[str]:
	international = doc.get("educore_pathway") == "International" or (
		doc.nationality and doc.nationality.strip().lower() not in ("namibian", "namibia")
	)
	wanted = {"All applicants", "International applicants" if international else "Namibian applicants"}
	return frappe.get_all(
		"Admission Document Type", filters={"active": 1, "required_for": ("in", list(wanted))}, pluck="name"
	)


def missing(doc) -> list[str]:
	"""What still stops this application from being submitted, in plain words (empty: ready)"""
	gaps = []
	for field, label in (
		("first_name", _("first name")),
		("last_name", _("last name")),
		("date_of_birth", _("date of birth")),
		("gender", _("gender")),
		("nationality", _("nationality")),
		("student_email_id", _("email")),
		("student_admission", _("intake")),
	):
		if not doc.get(field):
			gaps.append(_("Your {0}").format(label))
	if not doc.get("educore_choices"):
		gaps.append(_("At least one programme choice"))
	if doc.get("educore_pathway") != "International":
		if not doc.get("educore_secondary_school"):
			gaps.append(_("Your secondary school"))
		if not doc.get("educore_results"):
			gaps.append(_("Your school results"))

	uploaded = {d.document_type: d for d in doc.get("educore_documents") or []}
	max_age = settings().certification_max_age_months or 0
	for document in required_documents(doc):
		row = uploaded.get(document)
		if not row:
			gaps.append(_("Document: {0}").format(document))
			continue
		if frappe.get_cached_value("Admission Document Type", document, "must_be_certified"):
			if not row.certified_on:
				gaps.append(_("The certification date of: {0}").format(document))
			elif getdate(row.certified_on) > getdate(nowdate()):
				gaps.append(_("A certification date in the future: {0}").format(document))
			elif max_age and getdate(row.certified_on) < getdate(add_months(nowdate(), -max_age)):
				gaps.append(
					_("A certified copy of {0} from the last {1} months").format(document, max_age)
				)
	return gaps


def intake_open(intake: str) -> bool:
	admission = frappe.get_cached_doc("Student Admission", intake)
	today = getdate(nowdate())
	if not (admission.published and admission.enable_admission_application):
		return False
	if admission.admission_start_date and today < getdate(admission.admission_start_date):
		return False
	return not (admission.admission_end_date and today > getdate(admission.admission_end_date))


def check_submission(doc):
	gaps = missing(doc)
	if gaps:
		frappe.throw(_("The application is not complete yet:") + "<br>" + "<br>".join(f"• {g}" for g in gaps))
	if not intake_open(doc.student_admission):
		frappe.throw(_("Applications for {0} are closed").format(doc.student_admission))
	if not doc.get("educore_declaration"):
		frappe.throw(_("Accept the declaration to submit the application"))
	doc.educore_submitted_on = now_datetime()
	doc.application_date = nowdate()
