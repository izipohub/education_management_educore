"""Lecturer workload: what each lecturer teaches in a semester, against the university's rule.

For a lecturer, an academic year and a semester:

- modules: the classes they are allocated to (Student Group Instructor) whose course runs that semester, a
  full-year course counting in both semesters (educore.api.v1.teaching_allocation._semester_of);
- students: the active students of those classes, each counted once;
- contact hours a week: the hours of those classes' Timetable Slots in the semester. A class taught by two lecturers
  counts in full for each, since both are in the room; the co-lecturers are named;
- invigilation hours: the papers they invigilate in that semester's examination sessions, in all.

The rule is the university's (Teaching Workload Settings, set by the Registrar): contact hours a week at least and at
most. A lecturer above the most is Over, below the least Light, else Within; one with no modules in the semester
None. Read on the Academic staff screen
(educore.api.v1.academic_staff).
"""

import frappe
from frappe.utils import flt, get_time

from educore.academics import lecturers as lecturer_records

SETTINGS = "Teaching Workload Settings"
#: the rule until the university sets its own, written once if the site has never had a value
DEFAULTS = {"min_hours": 6, "max_hours": 16}
OVER, WITHIN, LIGHT, NONE = "Over", "Within", "Light", "None"


def ensure_defaults():
	"""From every migrate: the defaults for anything never set"""
	stored = set(frappe.db.sql_list("select field from `tabSingles` where doctype = %s", SETTINGS))
	for field, value in DEFAULTS.items():
		if field not in stored:
			frappe.db.set_single_value(SETTINGS, field, value)


def rule() -> dict:
	return {field: flt(frappe.db.get_single_value(SETTINGS, field)) for field in DEFAULTS}


def status(hours: float, limits: dict) -> str:
	if hours > limits["max_hours"]:
		return OVER
	if hours < limits["min_hours"]:
		return LIGHT
	return WITHIN


def _hours(start, end) -> float:
	start, end = get_time(start), get_time(end)
	return round((end.hour * 60 + end.minute - start.hour * 60 - start.minute) / 60, 2)


def _classes(academic_year: str, semester: str, instructors: list[str]) -> list[dict]:
	"""The classes of these lecturers running in the semester: (instructor, class, course, campus)"""
	from educore.api.v1.teaching_allocation import _semester_of

	if not instructors:
		return []
	rows = frappe.db.sql(
		"""select i.instructor, g.name as `group`, g.course, g.campus, c.course_name, c.educore_course_code as code
		from `tabStudent Group Instructor` i join `tabStudent Group` g on g.name = i.parent
		left join `tabCourse` c on c.name = g.course
		where g.academic_year = %s and g.disabled = 0 and g.group_based_on = 'Course' and i.instructor in %s""",
		(academic_year, instructors),
		as_dict=True,
	)
	runs: dict[str, str] = {}
	out = []
	for r in rows:
		if r.course not in runs:
			runs[r.course] = _semester_of(r.course)
		if runs[r.course] in (semester, "Year"):
			out.append(r)
	return out


def for_lecturers(academic_year: str, semester: str, instructors: list[str]) -> dict[str, dict]:
	"""Each lecturer's workload in the semester: modules (with hours a week and co-lecturers), students, contact
	hours a week, invigilation hours and status"""
	limits = rule()
	classes = _classes(academic_year, semester, instructors)
	groups = list({c.group for c in classes})

	hours: dict[str, float] = {}
	for s in frappe.get_all(
		"Timetable Slot",
		filters={"student_group": ("in", groups or [""]), "semester": semester},
		fields=["student_group", "start_time", "end_time"],
		limit=0,
	):
		hours[s.student_group] = hours.get(s.student_group, 0) + _hours(s.start_time, s.end_time)

	students: dict[str, set[str]] = {}
	for s in frappe.get_all("Student Group Student", filters={"parent": ("in", groups or [""]), "active": 1}, fields=["parent", "student"], limit=0):
		students.setdefault(s.parent, set()).add(s.student)

	teachers: dict[str, list[tuple[str, str]]] = {}
	for t in frappe.get_all(
		"Student Group Instructor", filters={"parent": ("in", groups or [""])}, fields=["parent", "instructor", "instructor_name"], order_by="idx asc", limit=0
	):
		teachers.setdefault(t.parent, []).append((t.instructor, t.instructor_name))

	invigilation = _invigilation(academic_year, semester, instructors)

	out = {
		i: {"modules": [], "students": 0, "hours": 0.0, "invigilation": invigilation.get(i, 0.0), "campuses": []} for i in instructors
	}
	seen: dict[str, set[str]] = {i: set() for i in instructors}
	for c in sorted(classes, key=lambda c: (c.code or c.course, c.campus or "")):
		w = out[c.instructor]
		w["modules"].append(
			{
				"group": c.group,
				"course": c.course,
				"course_name": c.course_name,
				"code": c.code,
				"campus": c.campus,
				"students": len(students.get(c.group, ())),
				"hours": round(hours.get(c.group, 0), 2),
				"with": [name for i, name in teachers.get(c.group, []) if i != c.instructor],
			}
		)
		w["hours"] += hours.get(c.group, 0)
		seen[c.instructor] |= students.get(c.group, set())
		if c.campus and c.campus not in w["campuses"]:
			w["campuses"].append(c.campus)
	for i, w in out.items():
		w["hours"] = round(w["hours"], 2)
		w["students"] = len(seen[i])
		w["status"] = status(w["hours"], limits) if w["modules"] else NONE
	return out


def _invigilation(academic_year: str, semester: str, instructors: list[str]) -> dict[str, float]:
	"""Hours each lecturer invigilates in the semester's examination sessions (invigilators are logins)"""
	users = {u: i for i in instructors if (u := lecturer_records.user_of(i))}
	if not users:
		return {}
	rows = frappe.db.sql(
		"""select inv.user, p.start_time, p.end_time
		from `tabExamination Invigilator` inv
		join `tabExamination Paper` p on p.name = inv.parent and inv.parenttype = 'Examination Paper'
		join `tabExamination Session` s on s.name = p.session
		where s.academic_year = %s and s.semester = %s and inv.user in %s""",
		(academic_year, semester, list(users)),
		as_dict=True,
	)
	out: dict[str, float] = {}
	for r in rows:
		i = users[r.user]
		out[i] = round(out.get(i, 0) + _hours(r.start_time, r.end_time), 2)
	return out
