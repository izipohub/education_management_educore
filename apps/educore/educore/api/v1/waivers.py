"""Fee waivers, for Finance: requests waiting for the Bursar, and those decided (educore.finance.waivers).
Campus finance staff see and request waivers for their campus's students; the Bursar decides."""

import frappe
from frappe import _
from frappe.utils import flt, get_fullname

from educore.api.v1.clearance import _in_scope
from educore.finance import waivers

#: who requests fee waivers (the Bursar also decides: waivers.APPROVER_ROLES)
WAIVER_ROLES = ("Bursar", "Finance Officer", "Student Fees Officer", "System Manager")
KINDS = (waivers.PERCENT, waivers.AMOUNT, waivers.LATE)
FIELDS = [
	"name", "student", "student_name", "campus", "academic_year", "waive", "value", "reason", "status", "amount",
	"credit_note", "requested_by", "requested_on", "decided_by", "decided_on", "decision_note",
]


def _require():
	if not set(frappe.get_roles()) & set(WAIVER_ROLES):
		frappe.throw(_("Fee waivers are Finance's"), frappe.PermissionError)


def _row(w) -> dict:
	return {
		**w,
		"requested_on": str(w.requested_on) if w.requested_on else None,
		"decided_on": str(w.decided_on) if w.decided_on else None,
		"can_decide": w.status == waivers.REQUESTED and _can_decide() and w.requested_by != frappe.session.user,
		"can_withdraw": w.status == waivers.APPROVED and _can_decide(),
		"requested_by_name": get_fullname(w.requested_by) if w.requested_by else None,
		"decided_by_name": get_fullname(w.decided_by) if w.decided_by else None,
	}


def _can_decide() -> bool:
	return bool(set(frappe.get_roles()) & set(waivers.APPROVER_ROLES))


def of_student(student: str) -> list[dict]:
	return [_row(w) for w in frappe.get_all("Fee Waiver", filters={"student": student}, fields=FIELDS, order_by="creation desc")]


def years_of(student: str) -> list[str]:
	"""The years a waiver can be for: the latest the student is registered for first, then the rest (and years open
	for registration), newest first"""
	enrolled = set(frappe.get_all("Program Enrollment", filters={"student": student, "docstatus": 1}, pluck="academic_year"))
	years = sorted((y for y in enrolled | set(frappe.get_all("Registration Period", pluck="academic_year")) if y), reverse=True)
	current = max(enrolled) if enrolled else None
	return [current, *(y for y in years if y != current)] if current else years


@frappe.whitelist(methods=["GET"])
def waivers_list() -> dict:
	"""Every waiver of the user's campuses, newest first"""
	from educore.access.scope import campuses

	_require()
	rows = frappe.get_all(
		"Fee Waiver", filters={"campus": ("in", list(campuses()) or [""])}, fields=FIELDS, order_by="creation desc", limit=0
	)
	return {"rows": [_row(w) for w in rows], "can_decide": _can_decide(), "kinds": KINDS}


@frappe.whitelist(methods=["POST"])
def request(student_id: str, academic_year: str, waive: str, value: float | None = None, reason: str = "") -> dict:
	_require()
	_in_scope(student_id)
	if waive not in KINDS:
		frappe.throw(_("Choose what to waive"))
	if academic_year not in years_of(student_id):
		frappe.throw(_("{0} is not a year of this student's studies").format(academic_year))
	name = waivers.request(student_id, academic_year, waive, flt(value), reason)
	return _row(frappe.db.get_value("Fee Waiver", name, FIELDS, as_dict=True))


def _scoped(name: str) -> str:
	student = frappe.db.get_value("Fee Waiver", name, "student")
	if not student:
		frappe.throw(_("Unknown fee waiver {0}").format(name))
	_in_scope(student)
	return student


@frappe.whitelist(methods=["POST"])
def approve(name: str, note: str | None = None) -> dict:
	_require()
	_scoped(name)
	waivers.approve(name, note)
	return _row(frappe.db.get_value("Fee Waiver", name, FIELDS, as_dict=True))


@frappe.whitelist(methods=["POST"])
def reject(name: str, note: str) -> dict:
	_require()
	_scoped(name)
	waivers.reject(name, note)
	return _row(frappe.db.get_value("Fee Waiver", name, FIELDS, as_dict=True))


@frappe.whitelist(methods=["POST"])
def withdraw(name: str, note: str) -> dict:
	_require()
	_scoped(name)
	waivers.withdraw(name, note)
	return _row(frappe.db.get_value("Fee Waiver", name, FIELDS, as_dict=True))
