"""Fee waivers: part of a student's fees for a year that the university does not charge.

Finance (a Student Fees Officer, Finance Officer or the Bursar) requests a waiver for a student's year with the
reason: a percent of the year's fees, an amount, or the late registration fee. The Bursar approves or rejects it,
never their own request. Once approved and the year's invoice exists (the registration is approved,
educore.finance.student_fees), a credit note against that invoice takes the waived part off, line by line, so the
student owes only the rest; before that, it is applied when the year is invoiced, and the registration deposit is
worked out on what the student will owe.

A waiver never takes off more than the student is still charged on those lines (after sponsors and earlier
waivers). Withdrawing an approved waiver cancels its credit note: the student owes it again.
"""

import frappe
from frappe import _
from frappe.utils import flt, nowdate

PERCENT, AMOUNT, LATE = "Percent of fees", "Amount", "Late registration fee"
REQUESTED, APPROVED, REJECTED, WITHDRAWN = "Requested", "Approved", "Rejected", "Withdrawn"
LATE_FEE_ITEM = "Late Registration Fee"
#: who decides on waivers
APPROVER_ROLES = ("Bursar", "System Manager")


def validate_waiver(doc, method=None):
	doc.reason = (doc.reason or "").strip()
	if not doc.reason:
		frappe.throw(_("Give the reason for the waiver"))
	if doc.waive == PERCENT and not 0 < flt(doc.value) <= 100:
		frappe.throw(_("The percent must be more than 0 and at most 100"))
	if doc.waive == AMOUNT and flt(doc.value) <= 0:
		frappe.throw(_("Enter the amount to waive"))
	if doc.waive == LATE:
		doc.value = 0
	if doc.status in (REQUESTED, APPROVED) and doc.waive == LATE and frappe.db.exists(
		"Fee Waiver",
		{
			"student": doc.student,
			"academic_year": doc.academic_year,
			"waive": LATE,
			"status": ("in", (REQUESTED, APPROVED)),
			"name": ("!=", doc.name or ""),
		},
	):
		frappe.throw(_("The late registration fee of {0} in {1} is waived already").format(doc.student_name or doc.student, doc.academic_year))
	if not doc.requested_by:
		doc.requested_by = frappe.session.user
		doc.requested_on = nowdate()


def request(student: str, academic_year: str, waive: str, value: float, reason: str) -> str:
	doc = frappe.get_doc(
		{"doctype": "Fee Waiver", "student": student, "academic_year": academic_year, "waive": waive, "value": flt(value), "reason": reason}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _decide(name: str) -> "frappe.model.document.Document":
	if not set(frappe.get_roles()) & set(APPROVER_ROLES):
		frappe.throw(_("Only the Bursar decides on fee waivers"), frappe.PermissionError)
	doc = frappe.get_doc("Fee Waiver", name)
	if doc.status != REQUESTED:
		frappe.throw(_("This waiver is {0} already").format(doc.status.lower()))
	if doc.requested_by == frappe.session.user:
		frappe.throw(_("Someone else decides on a waiver you requested"), frappe.PermissionError)
	return doc


def approve(name: str, note: str | None = None) -> str | None:
	"""Approve the waiver; the credit note when the year is invoiced already"""
	doc = _decide(name)
	doc.db_set({"status": APPROVED, "decided_by": frappe.session.user, "decided_on": nowdate(), "decision_note": (note or "").strip()})
	return apply(name)


def reject(name: str, note: str):
	if not (note or "").strip():
		frappe.throw(_("Say why the waiver is rejected"))
	doc = _decide(name)
	doc.db_set({"status": REJECTED, "decided_by": frappe.session.user, "decided_on": nowdate(), "decision_note": note.strip()})


def withdraw(name: str, note: str):
	"""Take back a waiver: a request no longer wanted, or an approved one (its credit note is cancelled)"""
	from educore.finance.student_fees import _as_system

	if not (note or "").strip():
		frappe.throw(_("Say why the waiver is withdrawn"))
	doc = frappe.get_doc("Fee Waiver", name)
	if doc.status not in (REQUESTED, APPROVED):
		frappe.throw(_("This waiver is {0} already").format(doc.status.lower()))
	if doc.status == APPROVED and not set(frappe.get_roles()) & set(APPROVER_ROLES):
		frappe.throw(_("Only the Bursar withdraws an approved waiver"), frappe.PermissionError)
	if doc.credit_note and frappe.db.get_value("Sales Invoice", doc.credit_note, "docstatus") == 1:
		with _as_system():
			frappe.get_doc("Sales Invoice", doc.credit_note).cancel()
	doc.db_set({"status": WITHDRAWN, "decided_by": frappe.session.user, "decided_on": nowdate(), "decision_note": note.strip()})


# --- applying ------------------------------------------------------------------------------------------


def apply_for(student: str, academic_year: str) -> list[str]:
	"""Every approved waiver of the student's year not applied yet, once its invoice exists (oldest first)"""
	return [
		n
		for n in frappe.get_all(
			"Fee Waiver",
			filters={"student": student, "academic_year": academic_year, "status": APPROVED, "credit_note": ("is", "not set")},
			pluck="name",
			order_by="creation asc",
		)
		if apply(n)
	]


def apply(name: str) -> str | None:
	"""The waiver's credit note against the student's invoice for the year (None while there is no invoice)"""
	from educore.finance.student_fees import _as_system

	with _as_system():
		return _apply(name)


def _lines(invoice, waive: str) -> list:
	if waive == LATE:
		return [i for i in invoice.items if i.item_code == LATE_FEE_ITEM and flt(i.amount) > 0]
	return [i for i in invoice.items if i.item_code != LATE_FEE_ITEM and flt(i.amount) > 0]


def _apply(name: str) -> str | None:
	from educore.finance.sponsors import year_invoice
	from educore.finance.student_fees import credit_note, credited, split

	doc = frappe.get_doc("Fee Waiver", name)
	if doc.status != APPROVED or doc.credit_note:
		return doc.credit_note
	invoice_name = year_invoice(doc.student, doc.academic_year)
	if not invoice_name:
		return None  # applied when the year's registration is approved and invoiced
	invoice = frappe.get_doc("Sales Invoice", invoice_name)
	lines = _lines(invoice, doc.waive)
	base = flt(sum(flt(i.amount) for i in lines), 2)
	off = credited(invoice.name)
	left = flt(base - sum(off.get(i.item_code, 0) for i in lines), 2)
	wanted = base * flt(doc.value) / 100 if doc.waive == PERCENT else flt(doc.value) if doc.waive == AMOUNT else base
	amount = flt(max(0.0, min(wanted, left)), 2)
	if amount <= 0:
		doc.db_set("amount", 0)
		frappe.msgprint(_("Nothing is left to waive on {0}'s fees for {1}").format(doc.student_name, doc.academic_year), alert=True)
		return None
	what = _("Fees waived, {0}").format(doc.academic_year) if doc.waive != LATE else _("Late registration fee waived, {0}").format(doc.academic_year)
	note = credit_note(invoice, split(lines, amount, base), what, educore_fee_waiver=doc.name)
	doc.db_set({"amount": amount, "credit_note": note})
	return note


def estimate(student: str, academic_year: str, year_fees: float) -> float:
	"""The approved waivers of a year's fees before it is invoiced (the registration deposit is on the rest)"""
	total = 0.0
	for w in frappe.get_all(
		"Fee Waiver",
		filters={"student": student, "academic_year": academic_year, "status": APPROVED, "waive": ("!=", LATE)},
		fields=["waive", "value", "amount", "credit_note"],
	):
		if w.credit_note:
			total += flt(w.amount)
		else:
			total += flt(year_fees) * flt(w.value) / 100 if w.waive == PERCENT else flt(w.value)
	return flt(min(total, flt(year_fees)), 2)
