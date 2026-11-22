"""Students and guardians see only their own (their wards') records.

Education restricts Student this way (education.education.doctype.student.student), but not the records
that point to a student: a student with read access to Program Enrollment or Sales Invoice saw every
record their campus User Permission allowed. These hooks apply the same rule to those DocTypes.

Who is restricted is decided per DocType: a user holding Student or Guardian and no other role that can
read *this* DocType. (Education's own test looks at read access to Student, which would wrongly restrict
staff such as the Bursar, who read invoices but not student records.) Everyone else is unaffected.
"""

import frappe
from frappe.permissions import get_valid_perms

PORTAL_ROLES = ("Student", "Guardian")


def _restricted(user: str, doctype: str) -> bool:
	if user == "Administrator" or not set(frappe.get_roles(user)) & set(PORTAL_ROLES):
		return False
	return not any(perm.read and perm.role not in PORTAL_ROLES for perm in get_valid_perms(doctype, user))


def _own_students(user: str) -> list[str]:
	from education.education.api import get_guardians_for_user

	students = frappe.get_all("Student", filters={"user": user}, pluck="name")
	guardians = get_guardians_for_user(user)
	if guardians:
		students += frappe.get_all(
			"Student Guardian",
			filters={"parenttype": "Student", "guardian": ("in", guardians)},
			pluck="parent",
		)
	return students


def query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if not _restricted(user, doctype):
		return ""
	students = _own_students(user)
	if not students:
		return "1=0"
	names = ", ".join(frappe.db.escape(s) for s in students)
	return f"`tab{doctype}`.`student` in ({names})"


def has_permission(doc, ptype=None, user=None, debug=False):
	user = user or frappe.session.user
	if not _restricted(user, doc.doctype):
		return True
	return doc.get("student") in _own_students(user)
