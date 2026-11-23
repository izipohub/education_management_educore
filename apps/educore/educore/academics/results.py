"""Course results: from the marks on a class's mark sheet to the final mark, grade and result, and from published
results to the student's academic standing.

The rules are the university's (Examination Settings, set by the Registrar): the continuous assessment (CA) weight,
the CA a student needs to be admitted to the examination, the pass mark, the band below it that allows a
supplementary examination, the grading scale (Education's Grading Scale), and the share of a year's credits failed
that puts a student on probation.

A mark sheet moves Draft (the lecturer enters marks) → Submitted → Moderated (the department) → Approved (the
examination board) → Published (students see it; standing is set). See educore.api.v1.examinations.
"""

import frappe
from frappe import _
from frappe.utils import flt

#: Examination Settings: the defaults, written once if the site has never had a value
DEFAULTS = {"ca_weight": 50, "exam_admission_ca": 40, "pass_mark": 50, "supplementary_from": 45, "probation_share": 50}
#: the university's grading scale until it loads its own (grade, lowest final mark)
DEFAULT_SCALE = ("EduCore Standard", (("A+", 80), ("A", 70), ("B", 60), ("C", 50), ("D", 40), ("E", 0)))

PASS, SUPPLEMENTARY, FAIL, NOT_ADMITTED, ABSENT = "Pass", "Supplementary", "Fail", "Not admitted", "Absent"
#: results that do not earn the course's credits
NOT_PASSED = (SUPPLEMENTARY, FAIL, NOT_ADMITTED, ABSENT)
#: academic standing this module sets; others (On hold, Excluded) are set by hand and left alone
AUTOMATIC_STANDING = ("Good standing", "Probation")


def ensure_defaults():
	"""From every migrate: the defaults for anything never set, and a grading scale to start from"""
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = 'Examination Settings'"))
	for field, value in DEFAULTS.items():
		if field not in stored:
			frappe.db.set_single_value("Examination Settings", field, value)
	name, intervals = DEFAULT_SCALE
	if not frappe.db.exists("Grading Scale", name):
		scale = frappe.get_doc(
			{
				"doctype": "Grading Scale",
				"grading_scale_name": name,
				"description": _("A starting scale; load the university's own"),
				"intervals": [{"grade_code": g, "threshold": t} for g, t in intervals],
			}
		).insert(ignore_permissions=True)
		scale.submit()
	if not frappe.db.get_single_value("Examination Settings", "grading_scale"):
		frappe.db.set_single_value("Examination Settings", "grading_scale", name)


def settings():
	return frappe.get_cached_doc("Examination Settings")


def grade_bands() -> list[tuple[str, float]]:
	"""(grade, lowest final mark), highest first"""
	scale = settings().grading_scale
	if not scale:
		return []
	rows = frappe.get_all("Grading Scale Interval", filters={"parent": scale}, fields=["grade_code", "threshold"])
	return sorted(((r.grade_code, flt(r.threshold)) for r in rows), key=lambda r: -r[1])


def grade_for(final: float, bands: list[tuple[str, float]]) -> str | None:
	return next((grade for grade, lowest in bands if final >= lowest), None)


def work_out(entry, rules=None, bands=None):
	"""An entry's final mark, grade and result from its marks (nothing while marks are missing)"""
	rules = rules or settings()
	bands = bands if bands is not None else grade_bands()
	entry.final_mark = entry.grade = entry.result = None
	if entry.ca_mark is None or entry.ca_mark == "":
		return
	ca = flt(entry.ca_mark)
	if ca < flt(rules.exam_admission_ca):
		entry.result = NOT_ADMITTED
		return
	if entry.absent:
		entry.result = ABSENT
		return
	if entry.exam_mark is None or entry.exam_mark == "":
		return
	weight = flt(rules.ca_weight) / 100
	final = round(ca * weight + flt(entry.exam_mark) * (1 - weight))
	entry.final_mark = final
	entry.grade = grade_for(final, bands)
	if final >= flt(rules.pass_mark):
		entry.result = PASS
	elif final >= flt(rules.supplementary_from):
		entry.result = SUPPLEMENTARY
	else:
		entry.result = FAIL


def check_marks(entry):
	for label, mark in ((_("Continuous assessment"), entry.ca_mark), (_("Examination"), entry.exam_mark)):
		if mark not in (None, "") and not 0 <= flt(mark) <= 100:
			frappe.throw(_("{0}: {1} must be between 0 and 100").format(entry.student_name or entry.student, label))


def work_out_sheet(doc):
	rules, bands = settings(), grade_bands()
	for entry in doc.entries:
		check_marks(entry)
		work_out(entry, rules, bands)


def summary(doc) -> dict:
	"""How the class did: results counted, average final mark, pass rate"""
	counts = {r: 0 for r in (PASS, SUPPLEMENTARY, FAIL, NOT_ADMITTED, ABSENT)}
	finals = []
	for e in doc.entries:
		if e.result:
			counts[e.result] += 1
		if e.final_mark is not None:
			finals.append(flt(e.final_mark))
	decided = sum(counts.values())
	return {
		"counts": counts,
		"average": round(sum(finals) / len(finals), 1) if finals else None,
		"pass_rate": round(100 * counts[PASS] / decided) if decided else None,
		"complete": decided == len(doc.entries) and bool(doc.entries),
	}


# --- standing -----------------------------------------------------------------------------------------


def update_standing(students: list[str], academic_year: str):
	"""From a year's published results: probation when the share of credits failed reaches the university's line,
	good standing otherwise. A standing set by hand (On hold, Excluded) is left alone."""
	from educore.registration.rules import credits

	share = flt(settings().probation_share) or 50
	for student in set(students):
		if frappe.db.get_value("Student", student, "educore_academic_standing") not in (*AUTOMATIC_STANDING, None, ""):
			continue
		rows = frappe.db.sql(
			"""select ms.course, e.result from `tabMark Sheet Entry` e
			join `tabMark Sheet` ms on ms.name = e.parent
			where ms.status = 'Published' and ms.academic_year = %s and e.student = %s""",
			(academic_year, student),
			as_dict=True,
		)
		total = sum(credits(r.course) for r in rows)
		failed = sum(credits(r.course) for r in rows if r.result in NOT_PASSED)
		if not total:
			continue
		probation = 100 * failed / total >= share
		frappe.db.set_value(
			"Student",
			student,
			{
				"educore_academic_standing": "Probation" if probation else "Good standing",
				"educore_standing_note": _("From the {0} results: {1} of {2} credits not passed").format(academic_year, failed, total)
				if failed
				else None,
			},
		)
