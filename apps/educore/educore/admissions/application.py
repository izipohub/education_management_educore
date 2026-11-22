"""Online applications: points, eligibility per choice, and what a complete application needs.

The application is Education's Student Applicant (docs/architecture/online-applications.md). These rules run
from its validate hook (educore.academics.students.validate_applicant):

- Points: each result's points come from the university's scale (Admission Settings); the application's points
  are the best results in the configured number of subjects, one result per subject.
- Eligibility per choice: the programme's minimum points and subject requirements. A requirement names a subject
  (or a group such as English, which English Second Language counts as) and a minimum grade at a level; a result
  worth at least as many points meets it, so a higher level or a better grade does too. The result is a flag for
  staff, never a decision.
- Eligibility depends on the pathway's evidence (educore.admissions.pathways): school results as above; a prior
  qualification against the programme's minimum NQF level and average (postgraduate); the minimum age and then
  a person's judgement (mature age entry); studies elsewhere or here, decided by admissions and the faculty.
- Submitting (Draft → Applied) needs the declaration, a pathway and at least one choice at its level, the evidence
  the pathway is judged on, its referees, every required document, and certified copies certified recently
  enough, in an open intake.

What a university decides (Admission Settings, Admission Pathway, the programme's entry requirements) is read
from there, never fixed here.
"""

import frappe
from frappe import _
from frappe.utils import add_months, flt, getdate, now_datetime, nowdate

from educore.admissions import pathways

MEETS, FAILS, REVIEW = "Meets requirements", "Does not meet requirements", "Needs review"


def settings():
	return frappe.get_cached_doc("Admission Settings")


def max_choices() -> int:
	return settings().max_choices or 3


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
	"""(eligibility, why) for one choice, on the evidence the application's pathway is judged on"""
	program = frappe.get_cached_doc("Program", frappe.db.get_value("Programme Offering", offering, "program"))
	evidence = pathways.evidence(doc)
	if evidence == pathways.PRIOR_QUALIFICATION:
		return _assess_prior(doc, program)
	if evidence == pathways.WORK_EXPERIENCE:
		return _assess_mature(doc)
	if evidence == pathways.STUDIES_HERE:
		return _assess_returning(doc)
	if pathways.is_international(doc):
		return REVIEW, _("Foreign school qualifications are assessed by admissions.")
	eligibility, note = _assess_school(doc, program)
	if evidence == pathways.STUDIES_ELSEWHERE:
		if eligibility == FAILS:
			return REVIEW, _("School results: {0}. Studies since then may count; admissions decides.").format(note)
		return REVIEW, _("The faculty decides credit for previous studies.") + (f" {note}." if eligibility == MEETS else "")
	return eligibility, note


def _assess_school(doc, program) -> tuple[str, str]:
	results = [r for r in doc.get("educore_results") or [] if r.points is not None]
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


def _pct(value) -> str:
	return f"{flt(value, 1):g}"


def _best_prior(doc):
	rows = [r for r in doc.get("educore_prior_qualifications") or [] if r.year_completed]
	return max(rows, key=lambda r: (r.nqf_level or 0, flt(r.average)), default=None)


def _assess_prior(doc, program) -> tuple[str, str]:
	"""Postgraduate: the best completed qualification against the programme's minimum NQF level and average"""
	best = _best_prior(doc)
	if not best:
		return REVIEW, _("No completed qualification entered yet.")
	home = settings().home_country or "Namibia"
	if best.country and best.country != home:
		return REVIEW, _("{0} is from {1}: admissions checks it against the NQA evaluation.").format(best.qualification, best.country)
	if not best.nqf_level:
		return REVIEW, _("The NQF level of {0} is not given.").format(best.qualification)
	problems = []
	if program.get("educore_min_prior_nqf") and best.nqf_level < program.educore_min_prior_nqf:
		problems.append(_("NQF level {0}, {1} needed").format(best.nqf_level, program.educore_min_prior_nqf))
	minimum = flt(program.get("educore_min_prior_average"))
	if minimum:
		if not best.average:
			return REVIEW, _("The average of {0} is not given.").format(best.qualification)
		if flt(best.average) < minimum:
			problems.append(_("average {0}%, {1}% needed").format(_pct(best.average), _pct(minimum)))
	if problems:
		note = "; ".join(problems)
		return FAILS, note[:1].upper() + note[1:]
	return MEETS, _("{0}, NQF {1}").format(best.qualification, best.nqf_level) + (
		_(", {0}% average").format(_pct(best.average)) if best.average else ""
	)


def _assess_mature(doc) -> tuple[str, str]:
	"""Mature age entry: the pathway's minimum age is a rule; the experience is a person's judgement"""
	pathway = pathways.of(doc)
	age = pathways.age_on_intake(doc)
	if pathway and pathway.min_age and age is not None and age < pathway.min_age:
		return FAILS, _("{0} years old on 1 January; mature age entry is from {1}").format(age, pathway.min_age)
	return REVIEW, _("{0} years of work: admissions decides, perhaps after a test or interview.").format(
		pathways.work_years(doc)
	)


def _assess_returning(doc) -> tuple[str, str]:
	"""Resumption: who they were here; whether they may come back (standing, exclusion, fees) is decided by staff"""
	number = (doc.get("educore_previous_student_number") or "").strip()
	if not number:
		return REVIEW, _("No previous student number given.")
	student = frappe.db.get_value("Student", number, ["name", "student_name"], as_dict=True)
	if not student:
		return REVIEW, _("Student number {0} is not on record: admissions checks it.").format(number)
	program = frappe.db.get_value(
		"Program Enrollment", {"student": student.name, "docstatus": 1}, "program", order_by="enrollment_date desc"
	)
	return REVIEW, _("Studied here as {0}{1}: admissions checks their standing.").format(
		student.student_name, _(", last in {0}").format(program) if program else ""
	)


def assess(doc):
	doc.educore_points = score(doc)
	doc.educore_work_years = pathways.work_years(doc)
	for choice in doc.get("educore_choices") or []:
		choice.eligibility, choice.eligibility_note = assess_choice(doc, choice.programme_offering)


# --- drafts --------------------------------------------------------------------------------------------


def tidy_draft(doc):
	"""Ranks 1..n, at most three different active offerings; the first choice is the offering under decision"""
	choices = [c for c in doc.get("educore_choices") or [] if c.programme_offering]
	if len(choices) > max_choices():
		frappe.throw(_("Choose at most {0} programmes").format(max_choices()))
	offerings = [c.programme_offering for c in choices]
	if len(set(offerings)) != len(offerings):
		frappe.throw(_("Each programme offering can be chosen once"))
	choices.sort(key=lambda c: c.rank or 99)
	for rank, choice in enumerate(choices, start=1):
		choice.rank = rank
		if not frappe.db.get_value("Programme Offering", choice.programme_offering, "is_active"):
			frappe.throw(_("{0} is not taking applications").format(choice.programme_offering))
		pathways.check_programme_level(doc, frappe.db.get_value("Programme Offering", choice.programme_offering, "program"))
	doc.educore_choices = choices
	if choices:
		doc.educore_programme_offering = choices[0].programme_offering

	seen = set()
	for row in doc.get("educore_results") or []:
		if (row.subject, row.level) in seen:
			frappe.throw(_("{0} at {1} is entered twice").format(row.subject, row.level))
		seen.add((row.subject, row.level))


# --- submitting ----------------------------------------------------------------------------------------


def document_plan(doc) -> dict[str, bool]:
	"""The documents this applicant is asked for, {document: required}, required first: identity documents by
	their status (home or international), the pathway's documents, then the optional ones"""
	international = pathways.is_international(doc)
	active = frappe.get_all("Admission Document Type", filters={"active": 1}, fields=["name", "required_for"])
	asked: dict[str, bool] = {}
	for d in active:
		if d.required_for in ("All applicants", "International applicants" if international else "Namibian applicants"):
			asked[d.name] = True
	pathway = pathways.of(doc)
	is_active = {d.name for d in active}
	for row in pathway.documents if pathway else []:
		if row.document_type not in is_active:
			continue
		if row.applies_to == "Everyone" or row.applies_to == ("International applicants" if international else "Home applicants"):
			asked[row.document_type] = asked.get(row.document_type, False) or bool(row.required)
	for d in active:
		if d.required_for == "Optional":
			asked.setdefault(d.name, False)
	return dict(sorted(asked.items(), key=lambda item: (not item[1], item[0])))


def required_documents(doc) -> list[str]:
	return [name for name, required in document_plan(doc).items() if required]


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
	pathway = pathways.of(doc)
	if not pathway:
		gaps.append(_("Your pathway"))
	if not doc.get("educore_choices"):
		gaps.append(_("At least one programme choice"))
	gaps.extend(_evidence_gaps(doc, pathway))

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


def _evidence_gaps(doc, pathway) -> list[str]:
	evidence = pathway.evidence if pathway else pathways.SCHOOL_RESULTS
	gaps = []
	if evidence in (pathways.SCHOOL_RESULTS, pathways.STUDIES_ELSEWHERE) and not pathways.is_international(doc):
		if not doc.get("educore_secondary_school"):
			gaps.append(_("Your secondary school"))
		if not doc.get("educore_results"):
			gaps.append(_("Your school results"))
	if evidence in (pathways.STUDIES_ELSEWHERE, pathways.PRIOR_QUALIFICATION) and not doc.get("educore_prior_qualifications"):
		gaps.append(_("Your studies after school"))
	if evidence == pathways.PRIOR_QUALIFICATION and doc.get("educore_prior_qualifications") and not _best_prior(doc):
		gaps.append(_("A completed qualification (with the year completed)"))
	if evidence == pathways.WORK_EXPERIENCE and not doc.get("educore_employment"):
		gaps.append(_("Your work experience"))
	if evidence == pathways.STUDIES_HERE and not (doc.get("educore_previous_student_number") or "").strip():
		gaps.append(_("Your previous student number"))
	if pathway and pathway.min_age:
		age = pathways.age_on_intake(doc)
		if age is not None and age < pathway.min_age:
			gaps.append(
				_("{0} is for applicants aged {1} or older on 1 January: choose another pathway").format(
					pathway.name, pathway.min_age
				)
			)
	needed = pathway.referees_required if pathway else 0
	if needed and len(doc.get("educore_referees") or []) < needed:
		gaps.append(_("{0} referees").format(needed))
	return gaps


def decision_blockers(doc) -> list[str]:
	"""What stops staff approving an online application: unverified required documents, an unsettled fee"""
	from educore.admissions.fees import settled

	if not doc.get("educore_applicant_user"):
		return []  # a paper application captured by staff was checked in person
	blockers = []
	rules = settings()
	uploaded = {d.document_type: d for d in doc.get("educore_documents") or []}
	for document in required_documents(doc) if rules.approval_needs_verified_documents else []:
		row = uploaded.get(document)
		if not row or row.status != "Verified":
			blockers.append(_("{0} is not verified").format(document))
	if rules.approval_needs_fee and not settled(doc):
		blockers.append(_("The application fee is not paid or waived"))
	return blockers


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
