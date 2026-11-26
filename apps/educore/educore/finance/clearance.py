"""Financial holds and clearance.

- Finance places a hold on a student with the reason (a returned payment, a sponsor that withdrew, an unpaid fine) and
  lifts it with a note; holds are kept as a history (Student Hold).
- A student is financially cleared when they owe no more than the university allows at clearance (Registration
  Settings, clearance_max_owing) and no hold is active.
- What a hold or a lack of clearance stops: registration (any active hold); recording the completion of the programme
  and printing the award certificate, when the university requires clearance for graduation (graduation_needs_clearance).
"""

import frappe
from frappe import _
from frappe.utils import flt, fmt_money, nowdate

ACTIVE, LIFTED = "Active", "Lifted"


def _nad(amount: float) -> str:
	return f"N$ {fmt_money(amount, precision=2)}"


def owing(student: str) -> float:
	"""What the student owes on their invoices (a credit is not counted against a debt)"""
	return flt(
		frappe.db.sql(
			"select sum(outstanding_amount) from `tabSales Invoice` where docstatus = 1 and student = %s and outstanding_amount > 0",
			student,
		)[0][0],
		2,
	)


def active_holds(student: str) -> list[dict]:
	return frappe.get_all(
		"Student Hold",
		filters={"student": student, "status": ACTIVE},
		fields=["name", "reason", "placed_by", "placed_on"],
		order_by="placed_on asc, creation asc",
	)


def status(student: str, leave_out: str | None = None) -> dict:
	"""Cleared or not, and why not, in plain words; leave_out: an invoice not counted (a transcript's own fee, which
	stops the transcript by itself)"""
	settings = frappe.get_cached_doc("Registration Settings")
	owed = owing(student)
	if leave_out:
		owed = flt(owed - max(0.0, flt(frappe.db.get_value("Sales Invoice", leave_out, "outstanding_amount"))), 2)
	holds = active_holds(student)
	reasons = [_("Hold: {0}").format(h.reason) for h in holds]
	if owed > flt(settings.clearance_max_owing):
		reasons.insert(0, _("Fees owing: {0}").format(_nad(owed)))
	return {"cleared": not reasons, "owing": owed, "holds": [{**h, "placed_on": str(h.placed_on)} for h in holds], "reasons": reasons}


def graduation_needs_clearance() -> bool:
	return bool(frappe.db.get_single_value("Registration Settings", "graduation_needs_clearance"))


def require_for_graduation(student: str, student_name: str | None = None):
	if not graduation_needs_clearance():
		return
	state = status(student)
	if not state["cleared"]:
		frappe.throw(
			_("{0} is not financially cleared: {1}").format(
				student_name or frappe.db.get_value("Student", student, "student_name"), "; ".join(state["reasons"])
			)
		)


def place(student: str, reason: str) -> str:
	reason = (reason or "").strip()
	if not reason:
		frappe.throw(_("Give the reason for the hold"))
	doc = frappe.get_doc(
		{"doctype": "Student Hold", "student": student, "reason": reason, "status": ACTIVE, "placed_by": frappe.session.user, "placed_on": nowdate()}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def lift(name: str, note: str) -> None:
	note = (note or "").strip()
	if not note:
		frappe.throw(_("Say why the hold is lifted"))
	doc = frappe.get_doc("Student Hold", name)
	if doc.status != ACTIVE:
		frappe.throw(_("This hold is lifted already"))
	doc.update({"status": LIFTED, "lifted_by": frappe.session.user, "lifted_on": nowdate(), "lift_note": note})
	doc.save(ignore_permissions=True)
