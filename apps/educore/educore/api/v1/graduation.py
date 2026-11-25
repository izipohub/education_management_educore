"""Graduation: which students meet their programme's requirements, and recording the completions the Senate
approves (educore.academics.graduation).

- The examinations officer and the faculty offices read the list (their own campus or faculty) to prepare it
  for the Senate.
- The Registrar confirms completion with the Senate meeting's reference; the academic record then reads final.
"""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from educore.academics import graduation

CONFIRM_ROLES = ("Registrar", "System Manager")
READ_ROLES = (*CONFIRM_ROLES, "Registry Officer", "Examinations Officer", "Faculty Officer", "Dean", "Head of Department", "Campus Director", "Executive Management")


def _has(roles) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _require(roles):
	if not _has(roles):
		frappe.throw(_("Graduation is for the Registrar's and examinations offices"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def candidates(program: str | None = None, campus: str | None = None) -> dict:
	"""Every student this user may see, with their progress towards completing their programme"""
	_require(READ_ROLES)
	filters = {"enabled": 1}
	if campus:
		filters["campus"] = campus
	names = frappe.get_list("Student", filters=filters, pluck="name", order_by="student_name asc", limit=0)
	rows = [graduation.progress(n) for n in names]
	if program:
		rows = [r for r in rows if r["program"] == program]
	return {
		"rows": rows,
		"programmes": sorted({r["program"] for r in rows if r["program"]}),
		"campuses": frappe.get_list("Campus", pluck="name", order_by="name asc", limit=0),
		"can_confirm": _has(CONFIRM_ROLES),
	}


@frappe.whitelist(methods=["POST"])
def confirm(students: list[str] | str, reference: str, completed_on: str | None = None) -> dict:
	"""Record the completions the Senate approved: every student must be eligible and not held back"""
	_require(CONFIRM_ROLES)
	students = frappe.parse_json(students) if isinstance(students, str) else students
	reference = (reference or "").strip()
	if not reference:
		frappe.throw(_("Name the Senate meeting that approved the awards"))
	if not students:
		frappe.throw(_("Choose the students"))
	completed_on = str(getdate(completed_on or nowdate()))
	if getdate(completed_on) > getdate(nowdate()):
		frappe.throw(_("The date of completion cannot be in the future"))
	for student in students:
		frappe.get_doc("Student", student).check_permission("read")
		graduation.confirm(student, reference, completed_on)
	return {"confirmed": len(students)}
