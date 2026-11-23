"""The curriculum, laid out by the academic side (faculty officer, head of department, dean) and read by the
Registrar's office: which courses each programme has, in which year of study, and when they
run (Semester 1, Semester 2 or the full year).

The curriculum is Education's own Program Course table, with EduCore's year of study and semester on each row
(educore.setup.custom_fields); registration reads it (educore.registration.rules.curriculum), and the proof of
registration shows each course's semester. Programmes are read through frappe.get_list, so a faculty officer or
head of department sees their faculty's programmes only; saving is recorded as the signed-in user.
"""

import frappe
from frappe import _
from frappe.utils import cint

from educore.registration import rules

#: who reads the curriculum: the faculties, and the Registrar's office, which publishes it (yearbook, proof of
#: registration)
CURRICULUM_ROLES = ("Registrar", "Faculty Officer", "Head of Department", "Dean", "System Manager")
#: who lays it out: the academic side, each in their own faculty (the Registrar reads it, does not change it)
EDIT_ROLES = ("Faculty Officer", "Head of Department", "Dean", "System Manager")
SEMESTERS = ("Semester 1", "Semester 2", "Year")


def _require_role():
	if not set(frappe.get_roles()) & set(CURRICULUM_ROLES):
		frappe.throw(_("The curriculum is set by the faculty and the Registrar"), frappe.PermissionError)


def can_edit() -> bool:
	return bool(set(frappe.get_roles()) & set(EDIT_ROLES))


def _faculty(department: str | None) -> str:
	return (department or "").rsplit(" - ", 1)[0]


@frappe.whitelist(methods=["GET"])
def programmes() -> list[dict]:
	"""The programmes this user may see, with how much of each is laid out"""
	_require_role()
	rows = frappe.get_list(
		"Program",
		filters={"educore_programme_code": ("is", "set")},
		fields=["name", "educore_programme_code as code", "educore_qualification_type as qualification", "educore_nqf_level as nqf_level",
			"educore_duration_years as duration", "department", "educore_study_level as level"],
		order_by="program_name asc",
		limit=0,
	)
	for row in rows:
		courses = rules.curriculum(row.name)
		row["faculty"] = _faculty(row.pop("department"))
		row["courses"] = len(courses)
		row["credits"] = sum(c["credits"] for c in courses)
		row["years_laid_out"] = len({c["year"] for c in courses})
		row["duration"] = cint(row.duration) or None
	return rows


@frappe.whitelist(methods=["GET"])
def programme(name: str) -> dict:
	"""One programme's curriculum, and the courses that can be added to it"""
	_require_role()
	doc = frappe.get_doc("Program", name)
	doc.check_permission("read")  # faculty scope
	nqf = lambda course: frappe.get_cached_value("Course", course, "educore_nqf_level")  # noqa: E731
	return {
		"name": doc.name,
		"code": doc.get("educore_programme_code"),
		"qualification": doc.get("educore_qualification_type"),
		"nqf_level": doc.get("educore_nqf_level"),
		"duration": cint(doc.get("educore_duration_years")) or None,
		"faculty": _faculty(doc.department),
		"level": doc.get("educore_study_level"),
		"courses": [{**c, "nqf_level": nqf(c["course"])} for c in rules.curriculum(name)],
		"catalogue": frappe.get_all(
			"Course",
			fields=["name as course", "educore_course_code as code", "educore_credits as credits", "educore_nqf_level as nqf_level"],
			order_by="educore_course_code asc, name asc",
			limit=0,
		),
		"semesters": list(SEMESTERS),
		"can_edit": can_edit(),
	}


@frappe.whitelist(methods=["POST"])
def save(name: str, courses: list | str) -> dict:
	"""The programme's courses, each with its year of study, semester and whether it is required"""
	if not can_edit():
		frappe.throw(_("The curriculum is laid out by the faculty"), frappe.PermissionError)
	courses = frappe.parse_json(courses)
	doc = frappe.get_doc("Program", name)
	doc.check_permission("read")  # faculty scope: only a programme this user may see
	duration = cint(doc.get("educore_duration_years")) or 10
	seen = set()
	doc.courses = []
	for row in courses:
		course = row.get("course")
		if not course or not frappe.db.exists("Course", course):
			frappe.throw(_("Choose each course from the course list"))
		if course in seen:
			frappe.throw(_("{0} is listed twice").format(course))
		seen.add(course)
		year = cint(row.get("year"))
		if not 1 <= year <= duration:
			frappe.throw(_("{0}: the year of study must be between 1 and {1}").format(course, duration))
		semester = row.get("semester") or "Year"
		if semester not in SEMESTERS:
			frappe.throw(_("{0}: choose Semester 1, Semester 2 or Year").format(course))
		doc.append(
			"courses",
			{
				"course": course,
				"course_name": frappe.db.get_value("Course", course, "course_name") or course,
				"educore_year": year,
				"educore_semester": semester,
				"required": 1 if row.get("required") else 0,
			},
		)
	doc.flags.ignore_permissions = True  # the role and the faculty scope are checked above
	doc.save()
	frappe.clear_document_cache("Program", name)
	return programme(name)
