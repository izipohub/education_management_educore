"""Lecturers: every login holding the Lecturer position has an Education Instructor record, made automatically.

Classes, marks and Moodle all work through the Instructor (Student Group Instructor), so a lecturer without one
sees nothing in My teaching and cannot be allocated to a class. The Instructor is made as soon as a login holds
the Lecturer position, linked to that login (educore_user), with its department and campuses taken from the
login's User Permissions (the teaching department, the campuses). The HR staff record (Employee) is HR's: it needs
personal details EduCore does not invent, so HR adds it and it is linked to the Instructor when its login matches.

A login that loses the position, or is disabled, is marked Left (kept for the classes it taught); gaining the
position again makes it Active. The head of department or the dean completes the rest on the Academic staff
screen (educore.api.v1.academic_staff).
"""

import frappe

from educore.setup.custom_fields import ACADEMIC_UNIT_TYPES

LECTURER = "Lecturer"
#: units a lecturer belongs to: the department that teaches (a faculty holds departments; a school also teaches)
TEACHING_UNIT_TYPES = ("Academic Department", "School")


def instructors_of(user: str) -> list[str]:
	"""The Instructor records of this login: linked directly, or through its HR staff record"""
	employees = frappe.get_all("Employee", filters={"user_id": user, "status": "Active"}, pluck="name")
	names = set(frappe.get_all("Instructor", filters={"educore_user": user, "status": ("!=", "Left")}, pluck="name"))
	if employees:
		names |= set(frappe.get_all("Instructor", filters={"employee": ("in", employees), "status": ("!=", "Left")}, pluck="name"))
	return sorted(names)


def user_of(instructor: str) -> str | None:
	"""The login of a lecturer: its own, else its HR staff record's"""
	user, employee = frappe.db.get_value("Instructor", instructor, ["educore_user", "employee"]) or (None, None)
	if not user and employee:
		user = frappe.db.get_value("Employee", employee, "user_id")
	return user


def _permitted(user: str, doctype: str) -> list[str]:
	return frappe.get_all("User Permission", filters={"user": user, "allow": doctype}, pluck="for_value", order_by="creation asc")


def teaching_department(user: str) -> str | None:
	"""The login's teaching department, from its User Permissions on Department"""
	for unit in _permitted(user, "Department"):
		if frappe.db.get_value("Department", unit, "educore_unit_type") in TEACHING_UNIT_TYPES:
			return unit
	return None


def campuses(user: str) -> list[str]:
	return _permitted(user, "Campus")


def _record_for(user: str) -> str | None:
	"""The login's Instructor, Left ones included"""
	found = frappe.db.get_value("Instructor", {"educore_user": user})
	if found:
		return found
	employee = frappe.db.get_value("Employee", {"user_id": user})
	return frappe.db.get_value("Instructor", {"employee": employee}) if employee else None


def _is_lecturer(user: str) -> bool:
	# from the database, not frappe.get_roles: its cache is stale while the User is being saved
	return bool(frappe.db.get_value("User", user, "enabled")) and bool(
		frappe.db.exists("Has Role", {"parent": user, "parenttype": "User", "role": LECTURER})
	)


def sync_user(user: str) -> str | None:
	"""Make, complete, retire or reinstate the login's Instructor, as its position and access stand"""
	if not user or user in ("Administrator", "Guest") or not frappe.db.exists("User", user):
		return None
	name = _record_for(user)
	lecturer = _is_lecturer(user)
	if not name and not lecturer:
		return None
	doc = frappe.get_doc("Instructor", name) if name else frappe.new_doc("Instructor")
	before = doc.as_dict() if name else None

	if not doc.educore_user:
		doc.educore_user = user
	if not doc.instructor_name:
		doc.instructor_name = frappe.db.get_value("User", user, "full_name") or user
	if not doc.employee:
		employee = frappe.db.get_value("Employee", {"user_id": user})
		if employee and not frappe.db.exists("Instructor", {"employee": employee, "name": ("!=", doc.name or "")}):
			doc.employee = employee
	if not doc.department:
		doc.department = teaching_department(user) or (
			frappe.db.get_value("Employee", doc.employee, "department") if doc.employee else None
		)
	have = {row.campus for row in doc.get("educore_campuses") or []}
	for campus in campuses(user):
		if campus not in have:
			doc.append("educore_campuses", {"campus": campus})
	doc.status = "Active" if lecturer else "Left"

	doc.flags.ignore_permissions = True
	if not name:
		# Education names instructors by full name: two lecturers may share one
		taken = frappe.db.exists("Instructor", doc.instructor_name)
		doc.insert(set_name=f"{doc.instructor_name} ({user})" if taken else None)
		return doc.name
	if _changed(before, doc):
		doc.save()
	return doc.name


def _changed(before: dict, doc) -> bool:
	if any(before.get(f) != doc.get(f) for f in ("educore_user", "instructor_name", "employee", "department", "status")):
		return True
	return len(before.get("educore_campuses") or []) != len(doc.get("educore_campuses") or [])


def sync_all() -> int:
	"""Every lecturer login and every linked Instructor (after migrate): nothing is left half set up"""
	users = set(
		frappe.get_all("Has Role", filters={"role": LECTURER, "parenttype": "User"}, pluck="parent", distinct=True)
	)
	users |= {u for u in frappe.get_all("Instructor", filters={"educore_user": ("is", "set")}, pluck="educore_user")}
	users -= {"Administrator", "Guest"}
	for user in sorted(users):
		sync_user(user)
	return len(users)


# --- doc events ----------------------------------------------------------------------------------------


def on_user_update(doc, method=None):
	"""A login gained or lost the Lecturer position, or was disabled"""
	sync_user(doc.name)


def on_user_permission_change(doc, method=None):
	"""Access added to a lecturer's login: its department and campuses"""
	if doc.allow in ("Department", "Campus") and _record_for(doc.user):
		sync_user(doc.user)


def on_employee_update(doc, method=None):
	"""HR added the staff record of a lecturer's login: link it"""
	if doc.user_id and (_record_for(doc.user_id) or _is_lecturer(doc.user_id)):
		sync_user(doc.user_id)


def is_academic_unit(department: str | None) -> bool:
	return bool(department) and frappe.db.get_value("Department", department, "educore_unit_type") in ACADEMIC_UNIT_TYPES
