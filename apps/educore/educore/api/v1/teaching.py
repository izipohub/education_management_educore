"""A lecturer's teaching: the course groups they teach and the students in them.

Who the lecturer is comes only from the signed-in session: User → HR Employee (user_id) → Education
Instructor (employee) → the Student Groups that list that instructor. No function takes a lecturer as a
parameter, so no request reaches another lecturer's classes.
"""

import frappe
from frappe import _


def _instructors() -> list[str]:
	employees = frappe.get_all("Employee", filters={"user_id": frappe.session.user, "status": "Active"}, pluck="name")
	if not employees:
		return []
	return frappe.get_all("Instructor", filters={"employee": ("in", employees), "status": ("!=", "Left")}, pluck="name")


@frappe.whitelist(methods=["GET"])
def my_classes(academic_year: str | None = None) -> dict:
	if "Instructor" not in frappe.get_roles() and "Lecturer" not in frappe.get_roles():
		frappe.throw(_("This page is for lecturers."), frappe.PermissionError)
	instructors = _instructors()
	if not instructors:
		# a lecturer login not yet linked to an HR Employee and Instructor record
		return {"linked": False, "academic_year": academic_year, "academic_years": [], "classes": []}

	group_names = frappe.get_all(
		"Student Group Instructor", filters={"instructor": ("in", instructors), "parenttype": "Student Group"}, pluck="parent"
	)
	years = sorted(
		set(frappe.get_all("Student Group", filters={"name": ("in", group_names or [""])}, pluck="academic_year")), reverse=True
	)
	academic_year = academic_year or (years[0] if years else None)
	groups = frappe.get_all(
		"Student Group",
		filters={"name": ("in", group_names or [""]), "academic_year": academic_year, "disabled": 0},
		fields=["name", "course", "campus", "academic_year", "academic_term"],
		order_by="name asc",
	)

	classes = []
	for group in groups:
		code, credits, nqf = frappe.db.get_value(
			"Course", group.course, ["educore_course_code", "educore_credits", "educore_nqf_level"]
		) or (None, None, None)
		students = frappe.get_all(
			"Student Group Student",
			filters={"parent": group.name, "parenttype": "Student Group", "active": 1},
			fields=["student", "student_name"],
			order_by="student_name asc",
		)
		for student in students:
			enrollment = frappe.db.get_value(
				"Program Enrollment",
				{"student": student.student, "academic_year": group.academic_year, "docstatus": 1},
				["program", "educore_programme_offering", "educore_mode_of_study"],
				as_dict=True,
			)
			student["programme"] = enrollment.program if enrollment else None
			student["offering"] = enrollment.educore_programme_offering if enrollment else None
			student["mode_of_study"] = enrollment.educore_mode_of_study if enrollment else None
		co_lecturers = frappe.get_all(
			"Student Group Instructor",
			filters={"parent": group.name, "instructor": ("not in", instructors)},
			pluck="instructor_name",
		)
		classes.append(
			{
				**group,
				"code": code,
				"credits": credits,
				"nqf_level": nqf,
				"students": students,
				"co_lecturers": co_lecturers,
			}
		)
	return {"linked": True, "academic_year": academic_year, "academic_years": years, "classes": classes}
