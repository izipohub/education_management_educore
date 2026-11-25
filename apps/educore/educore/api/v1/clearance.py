"""Financial clearance, for Finance: students on hold, owing, or cleared; placing and lifting holds
(educore.finance.clearance). Campus finance staff see their campus's students."""

import frappe
from frappe import _
from frappe.utils import flt

from educore.finance import clearance

#: who places and lifts holds
CLEARANCE_ROLES = ("Bursar", "Finance Officer", "Student Fees Officer", "System Manager")


def _require():
	if not set(frappe.get_roles()) & set(CLEARANCE_ROLES):
		frappe.throw(_("Financial clearance is Finance's"), frappe.PermissionError)


def _students() -> list:
	from educore.access.scope import campuses

	return frappe.get_all(
		"Student",
		filters={"enabled": 1, "campus": ("in", list(campuses()) or [""])},
		fields=["name", "student_name", "campus"],
		order_by="student_name asc",
	)


def _in_scope(student: str):
	from educore.access.scope import campuses

	if frappe.db.get_value("Student", student, "campus") not in campuses():
		frappe.throw(_("{0} is not a student of your campus").format(student), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def students() -> dict:
	"""Every student with what they owe, their active holds and whether they are cleared"""
	_require()
	holds: dict[str, int] = {}
	for h in frappe.get_all("Student Hold", filters={"status": clearance.ACTIVE}, pluck="student"):
		holds[h] = holds.get(h, 0) + 1
	limit = flt(frappe.db.get_single_value("Registration Settings", "clearance_max_owing"))
	rows = []
	for s in _students():
		owed = clearance.owing(s.name)
		rows.append({**s, "owing": owed, "holds": holds.get(s.name, 0), "cleared": owed <= limit and not holds.get(s.name)})
	return {"rows": rows, "max_owing": limit}


@frappe.whitelist(methods=["GET"])
def student(name: str) -> dict:
	"""One student's clearance: what they owe, their invoices, who sponsors them, every hold"""
	_require()
	_in_scope(name)
	doc = frappe.db.get_value("Student", name, ["name", "student_name", "campus", "student_email_id"], as_dict=True)
	return {
		**doc,
		**clearance.status(name),
		"invoices": [
			{**i, "posting_date": str(i.posting_date), "due_date": str(i.due_date)}
			for i in frappe.get_all(
				"Sales Invoice",
				filters={"student": name, "docstatus": 1},
				fields=["name", "posting_date", "due_date", "grand_total", "outstanding_amount", "remarks", "is_return"],
				order_by="posting_date desc",
			)
		],
		"history": [
			{**h, "placed_on": str(h.placed_on), "lifted_on": str(h.lifted_on) if h.lifted_on else None}
			for h in frappe.get_all(
				"Student Hold",
				filters={"student": name},
				fields=["name", "reason", "status", "placed_by", "placed_on", "lifted_by", "lifted_on", "lift_note"],
				order_by="creation desc",
			)
		],
		"sponsors": frappe.get_all(
			"Sponsorship",
			filters={"student": name, "status": ("!=", "Withdrawn")},
			fields=["sponsor_name", "academic_year", "amount", "status"],
			order_by="academic_year desc",
		),
	}


@frappe.whitelist(methods=["POST"])
def place_hold(student_id: str, reason: str) -> dict:
	_require()
	_in_scope(student_id)
	clearance.place(student_id, reason)
	return student(student_id)


@frappe.whitelist(methods=["POST"])
def lift_hold(hold: str, note: str) -> dict:
	_require()
	student_id = frappe.db.get_value("Student Hold", hold, "student")
	if not student_id:
		frappe.throw(_("Unknown hold {0}").format(hold))
	_in_scope(student_id)
	clearance.lift(hold, note)
	return student(student_id)
