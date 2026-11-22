"""Demo teaching for EduCore Demo University (development only): lecturers as HR Employees and Education
Instructors, and a course group (Student Group) per course and campus for 2026 with its students and lecturers.

Called from demo_students.create, after the students are enrolled. Re-running adds whatever is missing.
Real lecturers come from HR (Employee, linked to their login) and the faculty assigns them to course groups.
"""

import frappe

from educore.access.demo_users import DOMAIN

YEAR = "2026"


def _lecturers() -> dict[tuple[str, str], list[str]]:
	"""(unit code, campus code) → lecturer logins, from the scoped test users' naming"""
	from educore.access.test_users import plan

	teaching = {}
	for spec in plan():
		if "Lecturer" not in spec["positions"]:
			continue
		units = [frappe.db.get_value("Department", u, "educore_unit_code") for u in spec["units"]]
		campuses = [frappe.db.get_value("Campus", c, "campus_code") for c in spec["campuses"]]
		for unit in units:
			for campus in campuses:
				teaching.setdefault((unit, campus), []).append(spec["email"])
	return teaching


def _instructor(email: str) -> str | None:
	if not frappe.db.exists("User", email):
		return None
	employee = frappe.db.get_value("Employee", {"user_id": email})
	user = frappe.get_doc("User", email)
	if not employee:
		from educore.access.test_users import plan

		spec = next(s for s in plan() if s["email"] == email)
		campus = spec["campuses"][0] if spec["campuses"] else None
		employee = (
			frappe.get_doc(
				{
					"doctype": "Employee",
					"first_name": user.first_name,
					"last_name": user.last_name,
					"company": frappe.db.get_value("Campus", campus, "company"),
					"gender": "Female",
					"date_of_birth": "1985-06-15",
					"date_of_joining": "2020-01-15",
					"status": "Active",
					"user_id": email,
					"department": spec["units"][0] if spec["units"] else None,
					"branch": frappe.db.get_value("Campus", campus, "branch") if campus else None,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	instructor = frappe.db.get_value("Instructor", {"employee": employee})
	if not instructor:
		instructor = (
			frappe.get_doc(
				{
					"doctype": "Instructor",
					"instructor_name": user.full_name,
					"employee": employee,
					"department": frappe.db.get_value("Employee", employee, "department"),
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	return instructor


def create_course_groups() -> int:
	teaching = _lecturers()
	created = 0
	# students taking each course on each campus this year
	rows = frappe.db.sql(
		"""
		select ce.course, pe.campus, ce.student, ce.student_name
		from `tabCourse Enrollment` ce
		join `tabProgram Enrollment` pe on pe.name = ce.program_enrollment
		where pe.docstatus = 1 and pe.academic_year = %s
		order by ce.course, pe.campus, ce.student_name
		""",
		YEAR,
		as_dict=True,
	)
	groups: dict[tuple[str, str], list] = {}
	for row in rows:
		groups.setdefault((row.course, row.campus), []).append(row)

	for (course, campus), students in groups.items():
		code, unit = frappe.db.get_value("Course", course, ["educore_course_code", "department"])
		unit_code = frappe.db.get_value("Department", unit, "educore_unit_code")
		campus_code = frappe.db.get_value("Campus", campus, "campus_code")
		name = f"{code} {campus_code} {YEAR}"
		if frappe.db.exists("Student Group", name):
			continue
		instructors = [i for i in (_instructor(e) for e in teaching.get((unit_code, campus_code), [])) if i]
		frappe.get_doc(
			{
				"doctype": "Student Group",
				"student_group_name": name,
				"group_based_on": "Course",
				"course": course,
				"academic_year": YEAR,
				"campus": campus,
				"students": [{"student": s.student, "student_name": s.student_name, "active": 1} for s in students],
				"instructors": [{"instructor": i} for i in dict.fromkeys(instructors)],
			}
		).insert(ignore_permissions=True)
		created += 1
	return created


def lecturer_email(login: str) -> str:
	return f"{login}@{DOMAIN}"
