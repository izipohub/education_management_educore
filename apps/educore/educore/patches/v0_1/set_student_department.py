"""Student.department (new): the faculty/department of each student's latest submitted enrolment"""

import frappe


def execute():
	# custom fields are synced after migrate, after patches: create the new field first
	from educore.setup import custom_fields

	custom_fields.sync()

	enrollments = frappe.get_all(
		"Program Enrollment",
		filters={"docstatus": 1, "department": ("is", "set")},
		fields=["student", "department"],
		order_by="enrollment_date asc, creation asc",
	)
	latest = {e.student: e.department for e in enrollments}
	for student, department in latest.items():
		frappe.db.set_value("Student", student, "department", department, update_modified=False)
