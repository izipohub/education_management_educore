"""Teaching allocation, for the academic side: the classes of each course on each campus for a year and semester,
their class lists from approved registrations, and the lecturers teaching them.

A class is Education's Student Group (group_based_on Course) with EduCore's campus, named "<course code> <campus
code> <year>"; its term is the course's semester from the curriculum (none for a full-year course). The head of
department or the dean allocates lecturers (Education Instructors, who are HR Employees); class lists are built
from the students whose registration for the year is approved (Course Enrollments of submitted Program
Enrollments). Lecturers see their classes in My teaching (educore.api.v1.teaching).

Courses are read through frappe.get_list, so each person sees their own department's or faculty's courses only.
"""

import frappe
from frappe import _

from educore.academics.calendar import term

#: who allocates lecturers and updates class lists
EDIT_ROLES = ("Head of Department", "Dean", "System Manager")
#: who reads the allocation
#: Examinations Officer (who teaches a class whose marks are late), Quality Assurance, Executive Management: read only
READ_ROLES = (
	*EDIT_ROLES, "Faculty Officer", "Timetable Officer", "Registrar", "Campus Director",
	"Examinations Officer", "Quality Assurance Officer", "Executive Management",
)


def can_edit() -> bool:
	return bool(set(frappe.get_roles()) & set(EDIT_ROLES))


def _require(roles):
	if not set(frappe.get_roles()) & set(roles):
		frappe.throw(_("Teaching allocation is the faculty's"), frappe.PermissionError)


def _courses() -> dict[str, dict]:
	"""The courses this user may see (department and faculty scope), with code, credits and department"""
	return {
		c.name: c
		for c in frappe.get_list(
			"Course",
			fields=["name", "course_name", "educore_course_code as code", "educore_credits as credits", "department"],
			limit=0,
		)
	}


def _campuses() -> set[str]:
	from educore.access.scope import campuses

	return campuses()


def _semester_of(course: str) -> str:
	"""When a course runs, from the curriculum of the programmes that have it (the first one listing it)"""
	period = frappe.db.get_value("Program Course", {"course": course, "parenttype": "Program"}, "educore_semester")
	return period or "Year"


def _registered(academic_year: str, courses: list[str]) -> dict[tuple[str, str], list[dict]]:
	"""(course, campus) → the students whose registration for the year is approved"""
	if not courses:
		return {}
	rows = frappe.db.sql(
		"""
		select ce.course, pe.campus, ce.student, ce.student_name
		from `tabCourse Enrollment` ce
		join `tabProgram Enrollment` pe on pe.name = ce.program_enrollment
		where pe.docstatus = 1 and pe.academic_year = %(year)s and ce.course in %(courses)s
		order by ce.student_name
		""",
		{"year": academic_year, "courses": tuple(courses)},
		as_dict=True,
	)
	out: dict[tuple[str, str], list[dict]] = {}
	for row in rows:
		out.setdefault((row.course, row.campus), []).append(row)
	return out


def _group_name(course: dict, campus: str, academic_year: str) -> str:
	campus_code = frappe.get_cached_value("Campus", campus, "campus_code") or campus
	return f"{course.get('code') or course['name']} {campus_code} {academic_year}"


def _years() -> list[str]:
	years = set(frappe.get_all("Program Enrollment", filters={"docstatus": 1}, pluck="academic_year", distinct=True))
	years |= set(frappe.get_all("Student Group", filters={"group_based_on": "Course"}, pluck="academic_year", distinct=True))
	return sorted((y for y in years if y), reverse=True)


@frappe.whitelist(methods=["GET"])
def classes(academic_year: str | None = None) -> dict:
	"""Every course taught this year on each campus: its class (if made), students registered, lecturers"""
	_require(READ_ROLES)
	years = _years()
	academic_year = academic_year or (years[0] if years else None)
	courses = _courses()
	registered = _registered(academic_year, list(courses)) if academic_year else {}
	groups = frappe.get_all(
		"Student Group",
		filters={"group_based_on": "Course", "academic_year": academic_year, "course": ("in", list(courses) or [""]), "disabled": 0},
		fields=["name", "course", "campus"],
	)
	by_key = {(g.course, g.campus): g.name for g in groups}
	campuses = _campuses()

	rows = []
	for key in sorted({k for k in set(registered) | set(by_key) if not k[1] or k[1] in campuses}, key=lambda k: ((courses[k[0]].get("code") or k[0]), k[1] or "")):
		course, campus = key
		info = courses[course]
		group = by_key.get(key)
		in_class = frappe.db.count("Student Group Student", {"parent": group, "active": 1}) if group else 0
		lecturers = (
			frappe.get_all("Student Group Instructor", filters={"parent": group}, pluck="instructor_name") if group else []
		)
		count = len(registered.get(key, []))
		rows.append(
			{
				"key": f"{course}|{campus}",
				"group": group,
				"course": course,
				"course_name": info.course_name,
				"code": info.code,
				"credits": info.credits,
				"department": (info.department or "").rsplit(" - ", 1)[0],
				"campus": campus,
				"semester": _semester_of(course),
				"registered": count,
				"in_class": in_class,
				"lecturers": lecturers,
				"state": "no-class" if not group else ("to-update" if in_class != count else ("no-lecturer" if not lecturers else "ready")),
			}
		)
	return {
		"academic_year": academic_year,
		"academic_years": years,
		"campuses": sorted({r["campus"] for r in rows if r["campus"]}),
		"rows": rows,
		"can_edit": can_edit(),
	}


@frappe.whitelist(methods=["POST"])
def update_class_lists(academic_year: str) -> dict:
	"""Make or bring up to date the class of every course this user may see, from approved registrations"""
	_require(EDIT_ROLES)
	courses = _courses()
	registered = _registered(academic_year, list(courses))
	made = updated = 0
	for (course, campus), students in registered.items():
		if not campus:
			continue
		name = frappe.db.get_value(
			"Student Group", {"group_based_on": "Course", "course": course, "campus": campus, "academic_year": academic_year}
		)
		semester = _semester_of(course)
		academic_term = term(int(academic_year), semester) if semester != "Year" and str(academic_year).isdigit() else None
		if not name:
			frappe.get_doc(
				{
					"doctype": "Student Group",
					"student_group_name": _group_name(courses[course], campus, academic_year),
					"group_based_on": "Course",
					"course": course,
					"academic_year": academic_year,
					"academic_term": academic_term,
					"campus": campus,
					"students": [{"student": s.student, "student_name": s.student_name, "active": 1} for s in students],
				}
			).insert(ignore_permissions=True)
			made += 1
			continue
		group = frappe.get_doc("Student Group", name)
		current = {s.student for s in group.students if s.active}
		wanted = {s.student for s in students}
		if current == wanted and group.academic_term == academic_term:
			continue
		# students who left the course stay on the list, inactive; new ones are added
		for row in group.students:
			row.active = 1 if row.student in wanted else 0
		listed = {s.student for s in group.students}
		for s in students:
			if s.student not in listed:
				group.append("students", {"student": s.student, "student_name": s.student_name, "active": 1})
		group.academic_term = academic_term
		group.flags.ignore_permissions = True
		group.save()
		updated += 1
	return {"made": made, "updated": updated, **classes(academic_year)}


@frappe.whitelist(methods=["GET"])
def class_detail(group: str) -> dict:
	"""One class: its students and lecturers, and the lecturers who could be allocated"""
	_require(READ_ROLES)
	doc = frappe.get_doc("Student Group", group)
	if doc.get("campus") and doc.campus not in _campuses():
		frappe.throw(_("This class is on another campus"), frappe.PermissionError)
	if doc.course not in _courses():
		frappe.throw(_("This class is not in your department or faculty"), frappe.PermissionError)
	course = frappe.db.get_value("Course", doc.course, ["educore_course_code", "educore_credits", "department"], as_dict=True)
	students = []
	for s in doc.students:
		if not s.active:
			continue
		enrolment = frappe.db.get_value(
			"Program Enrollment",
			{"student": s.student, "academic_year": doc.academic_year, "docstatus": 1},
			["educore_programme_offering", "educore_year_of_study"],
			as_dict=True,
		) or {}
		students.append({"student": s.student, "student_name": s.student_name, "offering": enrolment.get("educore_programme_offering"), "year_of_study": enrolment.get("educore_year_of_study")})
	instructors = frappe.get_all("Instructor", filters={"status": ("!=", "Left")}, fields=["name", "instructor_name", "department"], order_by="instructor_name asc")
	return {
		"name": doc.name,
		"course": doc.course,
		"code": course.educore_course_code if course else None,
		"credits": course.educore_credits if course else None,
		"department": ((course.department if course else "") or "").rsplit(" - ", 1)[0],
		"campus": doc.get("campus"),
		"academic_year": doc.academic_year,
		"semester": _semester_of(doc.course),
		"students": sorted(students, key=lambda s: s["student_name"] or ""),
		"lecturers": [{"instructor": i.instructor, "instructor_name": i.instructor_name} for i in doc.instructors],
		# the course's own department first: most allocations are from it
		"instructors": sorted(
			({**i, "department": (i.department or "").rsplit(" - ", 1)[0]} for i in instructors),
			key=lambda i: (i["department"] != ((course.department if course else "") or "").rsplit(" - ", 1)[0], i["instructor_name"]),
		),
		"can_edit": can_edit(),
		# the class's course in Moodle, once ICT connects it (educore.learning.moodle)
		"moodle": {
			"connected": bool(frappe.db.get_single_value("Learning Platform Settings", "moodle_enabled")),
			"course_id": doc.get("educore_moodle_course_id"),
			"synced_on": str(doc.educore_moodle_synced_on) if doc.get("educore_moodle_synced_on") else None,
			"error": doc.get("educore_moodle_error"),
		},
	}


@frappe.whitelist(methods=["POST"])
def set_lecturers(group: str, instructors: list | str) -> dict:
	"""The lecturers who teach this class"""
	_require(EDIT_ROLES)
	instructors = frappe.parse_json(instructors) or []
	doc = frappe.get_doc("Student Group", group)
	if doc.course not in _courses():
		frappe.throw(_("This class is not in your department or faculty"), frappe.PermissionError)
	for name in instructors:
		if not frappe.db.exists("Instructor", name):
			frappe.throw(_("{0} is not a lecturer on record").format(name))
	doc.instructors = []
	for name in dict.fromkeys(instructors):
		doc.append("instructors", {"instructor": name})
	doc.flags.ignore_permissions = True
	doc.save()
	return class_detail(group)
