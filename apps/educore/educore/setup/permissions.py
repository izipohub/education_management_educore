"""Read access EduCore's roles need on upstream DocTypes, added after install and every migrate.

Added as Custom DocPerms (Frappe's Role Permission Manager mechanism), so upstream DocTypes stay unmodified.
What each user then sees is still narrowed by their User Permissions (campus, faculty, department).
"""

import frappe
from frappe.permissions import add_permission, update_permission_property

#: (DocType, role): read only
READ_ACCESS = (
	# every staff member can see the university's structure: faculties, schools, departments, divisions
	("Department", "University Staff"),
	# and its programmes and courses
	("Program", "University Staff"),
	("Course", "University Staff"),
	# academic leaders see the students and enrolments of their faculty / department / campus
	("Student", "Dean"),
	("Student", "Head of Department"),
	("Student", "Campus Director"),
	("Student", "Executive Management"),
	("Program Enrollment", "Dean"),
	("Program Enrollment", "Head of Department"),
	("Program Enrollment", "Campus Director"),
	("Program Enrollment", "Executive Management"),
	# student support and sponsored students: the Students screen, read only (educore.api.v1.student_records)
	("Student", "Student Affairs Officer"),
	("Student", "Financial Aid Officer"),
	("Student", "Accommodation Officer"),
	("Program Enrollment", "Student Affairs Officer"),
	("Program Enrollment", "Financial Aid Officer"),
	("Program Enrollment", "Accommodation Officer"),
)

#: (DocType, role): upstream grants write, a university does not. Education lets Instructor (every
#: Lecturer) edit programmes and courses; the catalogue belongs to faculties and the registry.
READ_ONLY = (
	("Program", "Instructor"),
	("Course", "Instructor"),
)


#: (DocType, role): read the records the user created themselves, nothing else and no writing. Applicants read
#: their own application (Frappe's workflow checks read access before a Submit); every change goes through
#: educore.api.v1.apply, which takes only the fields it lists.
OWN_RECORDS_READ = (("Student Applicant", "Applicant"),)


def _ensure_row(doctype, role):
	if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role, "permlevel": 0}):
		add_permission(doctype, role, 0)


def sync():
	for doctype, role in READ_ACCESS:
		_ensure_row(doctype, role)
		update_permission_property(doctype, role, 0, "read", 1, validate=False)
		update_permission_property(doctype, role, 0, "report", 1, validate=False)
	for doctype, role in READ_ONLY:
		_ensure_row(doctype, role)
		update_permission_property(doctype, role, 0, "read", 1, validate=False)
		for right in ("write", "create", "delete", "submit", "cancel", "amend"):
			update_permission_property(doctype, role, 0, right, 0, validate=False)
	for doctype, role in OWN_RECORDS_READ:
		_ensure_row(doctype, role)
		update_permission_property(doctype, role, 0, "read", 1, validate=False)
		update_permission_property(doctype, role, 0, "if_owner", 1, validate=False)
		for right in ("write", "create", "delete", "submit", "cancel", "amend", "report", "export", "print", "email", "share"):
			update_permission_property(doctype, role, 0, right, 0, validate=False)
