"""Course changes after registration: a student whose registration for the year is approved asks to add or drop
courses until the year's course change date (Registration Period.changes_until); the faculty officer approves or
declines.

The same rules as registration hold for the courses after the change (on the programme, not passed already,
prerequisites passed, the year's required courses kept, within the credit limit). Approving updates the
registration's courses and Course Enrollments, so the class lists show as out of date on the Teaching screen until
the department updates them. The year's fees do not depend on the courses, so no invoice changes.
"""

import frappe
from frappe import _
from frappe.utils import getdate, now_datetime, nowdate

from educore.api.v1.registration import REVIEW_ROLES, _student
from educore.registration import rules

SUBMITTED, APPROVED, DECLINED = "Submitted", "Approved", "Declined"
ADD, DROP = "Add", "Drop"


def _window(period) -> dict:
	until = period.get("changes_until") if period else None
	return {
		"changes_until": str(until) if until else None,
		"open": bool(until) and getdate(nowdate()) <= getdate(until),
	}


def _approved_registration(student: str, academic_year: str):
	name = frappe.db.get_value("Program Enrollment", {"student": student, "academic_year": academic_year, "docstatus": 1})
	return frappe.get_doc("Program Enrollment", name) if name else None


def _serialise(doc) -> dict:
	return {
		"name": doc.name,
		"student": doc.student,
		"student_name": doc.student_name,
		"program": doc.program,
		"campus": doc.campus,
		"academic_year": doc.academic_year,
		"status": doc.status,
		"submitted_on": str(doc.submitted_on) if doc.submitted_on else None,
		"reviewed_on": str(doc.reviewed_on) if doc.reviewed_on else None,
		"reason": doc.reason,
		"review_note": doc.review_note,
		"items": [
			{"action": i.action, "course": i.course, "course_name": i.course_name, "credits": rules.credits(i.course)} for i in doc.items
		],
	}


def _after(registration, adds: list[str], drops: list[str]) -> list[str]:
	current = [row.course for row in registration.courses]
	return [c for c in current if c not in drops] + [c for c in adds if c not in current]


def _check(registration, adds: list[str], drops: list[str]):
	"""The courses after the change, under the registration rules"""
	current = {row.course for row in registration.courses}
	if not adds and not drops:
		frappe.throw(_("Choose a course to add or drop"))
	for course in adds:
		if course in current:
			frappe.throw(_("{0} is registered already").format(course))
	for course in drops:
		if course not in current:
			frappe.throw(_("{0} is not one of the registered courses").format(course))
	year = registration.get("educore_year_of_study") or 1
	after = _after(registration, adds, drops)
	if not after:
		frappe.throw(_("At least one course must stay registered; to stop studying, contact the Registry"))
	rules.check_courses(registration.program, year, after, registration.student)


# --- the student ---------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def mine() -> dict:
	"""The student's approved registration for the year, whether course changes are open, and their requests"""
	student = _student()
	period = rules.current_period()
	out = {"academic_year": period.academic_year if period else None, **_window(period), "registration": None, "changes": []}
	if not period:
		return out
	registration = _approved_registration(student, period.academic_year)
	if not registration:
		return out
	year = registration.get("educore_year_of_study") or 1
	states = rules.course_states(student, registration.program, year)
	current = {row.course for row in registration.courses}
	courses = []
	for c in rules.curriculum(registration.program):
		state = states.get(c["course"], {"state": rules.OPEN, "missing": []})
		courses.append(
			{
				**c,
				"registered": c["course"] in current,
				"state": state["state"],
				"missing": state["missing"],
			}
		)
	out["registration"] = {"name": registration.name, "program": registration.program, "year_of_study": year, "courses": courses}
	out["max_credits"] = rules.settings().max_credits or 0
	out["changes"] = [
		_serialise(frappe.get_doc("Course Change", n))
		for n in frappe.get_all("Course Change", filters={"student": student, "academic_year": period.academic_year}, pluck="name", order_by="creation desc")
	]
	return out


@frappe.whitelist(methods=["POST"])
def request(add: list | str | None = None, drop: list | str | None = None, reason: str | None = None) -> dict:
	"""Ask the faculty to add or drop courses"""
	student = _student()
	adds = list(dict.fromkeys(frappe.parse_json(add) if isinstance(add, str) else (add or [])))
	drops = list(dict.fromkeys(frappe.parse_json(drop) if isinstance(drop, str) else (drop or [])))
	period = rules.current_period()
	if not period or not _window(period)["open"]:
		frappe.throw(_("Course changes are closed"))
	registration = _approved_registration(student, period.academic_year)
	if not registration:
		frappe.throw(_("Course changes are for students whose registration is approved"))
	if frappe.db.exists("Course Change", {"student": student, "academic_year": period.academic_year, "status": SUBMITTED}):
		frappe.throw(_("Your earlier request is still with the faculty"))
	_check(registration, adds, drops)
	names = {c["course"]: c["course_name"] for c in rules.curriculum(registration.program)}
	doc = frappe.get_doc(
		{
			"doctype": "Course Change",
			"student": student,
			"program_enrollment": registration.name,
			"academic_year": registration.academic_year,
			"program": registration.program,
			"campus": registration.get("campus"),
			"status": SUBMITTED,
			"submitted_on": now_datetime(),
			"reason": (reason or "").strip() or None,
			"items": [{"action": ADD, "course": c, "course_name": names.get(c, c)} for c in adds]
			+ [{"action": DROP, "course": c, "course_name": names.get(c, c)} for c in drops],
		}
	).insert(ignore_permissions=True)
	if not rules.settings().approval_needed:
		_apply(doc)
	return mine()


# --- the faculty officer -------------------------------------------------------------------------------


def _require_reviewer():
	if not set(frappe.get_roles()) & set(REVIEW_ROLES):
		frappe.throw(_("Only faculty officers and the Registrar approve course changes"), frappe.PermissionError)


def _in_scope(names: list[str]) -> set[str]:
	"""The registrations among these that the user may see (campus and faculty User Permissions)"""
	if not names:
		return set()
	return set(frappe.get_list("Program Enrollment", filters={"name": ("in", names)}, pluck="name", limit=0))


def _reviewable(name: str):
	_require_reviewer()
	doc = frappe.get_doc("Course Change", name)
	if doc.program_enrollment not in _in_scope([doc.program_enrollment]):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	if doc.status != SUBMITTED:
		frappe.throw(_("This request is not waiting for a decision"))
	return doc


@frappe.whitelist(methods=["GET"])
def queue(status: str = SUBMITTED) -> dict:
	_require_reviewer()
	if status not in (SUBMITTED, APPROVED, DECLINED):
		frappe.throw(_("Unknown status {0}").format(status))
	period = rules.current_period()
	year = period.academic_year if period else None
	rows = frappe.get_all("Course Change", filters={"academic_year": year}, fields=["name", "program_enrollment", "status"], order_by="submitted_on asc")
	mine = _in_scope([r.program_enrollment for r in rows])
	rows = [r for r in rows if r.program_enrollment in mine]
	return {
		"academic_year": year,
		**_window(period),
		"rows": [_serialise(frappe.get_doc("Course Change", r.name)) for r in rows if r.status == status],
		"counts": {s: sum(1 for r in rows if r.status == s) for s in (SUBMITTED, APPROVED, DECLINED)},
	}


def _apply(doc):
	"""The registration's courses and Course Enrollments after the change; checked again, as the student's results
	or the curriculum may have moved since the request"""
	registration = frappe.get_doc("Program Enrollment", doc.program_enrollment)
	adds = [i.course for i in doc.items if i.action == ADD]
	drops = [i.course for i in doc.items if i.action == DROP]
	_check(registration, adds, drops)
	for course in drops:
		for row in registration.courses:
			if row.course == course:
				frappe.db.delete("Program Enrollment Course", {"name": row.name})
		for name in frappe.get_all("Course Enrollment", filters={"program_enrollment": registration.name, "course": course}, pluck="name"):
			frappe.delete_doc("Course Enrollment", name, force=True, ignore_permissions=True)
	idx = max((row.idx for row in registration.courses), default=0)
	names = {i.course: i.course_name for i in doc.items}
	student = frappe.get_doc("Student", registration.student)
	for course in adds:
		idx += 1
		frappe.get_doc(
			{
				"doctype": "Program Enrollment Course",
				"parent": registration.name,
				"parenttype": "Program Enrollment",
				"parentfield": "courses",
				"idx": idx,
				"course": course,
				"course_name": names.get(course),
			}
		).db_insert()
		student.enroll_in_course(course, registration.name)
	doc.status = APPROVED
	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()
	doc.save(ignore_permissions=True)
	registration.add_comment(
		"Info",
		_("Courses changed ({0}): {1}").format(doc.name, ", ".join(f"{i.action.lower()} {i.course_name}" for i in doc.items)),
	)


@frappe.whitelist(methods=["POST"])
def approve(name: str) -> dict:
	_apply(_reviewable(name))
	return queue()


@frappe.whitelist(methods=["POST"])
def decline(name: str, note: str) -> dict:
	doc = _reviewable(name)
	if not (note or "").strip():
		frappe.throw(_("Tell the student why"))
	doc.status = DECLINED
	doc.review_note = note.strip()
	doc.reviewed_by = frappe.session.user
	doc.reviewed_on = now_datetime()
	doc.save(ignore_permissions=True)
	return queue()
