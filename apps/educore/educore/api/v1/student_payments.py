"""Student payments, for Finance: fees received from the bank statement, and deposits waiting to be assigned to a
student (educore.finance.student_payments)."""

import frappe
from frappe import _
from frappe.utils import flt

from educore.admissions.fees import references_in
from educore.finance import student_payments

#: the Cashier receipts payments: matching the bank statement and assigning deposits
FINANCE_ROLES = ("Bursar", "Finance Officer", "Student Fees Officer", "Cashier", "System Manager")


def _require_role():
	if not set(frappe.get_roles()) & set(FINANCE_ROLES):
		frappe.throw(_("Student payments are Finance's"), frappe.PermissionError)


def _student_by_customer() -> dict[str, dict]:
	return {
		s.customer: s
		for s in frappe.get_all("Student", filters={"customer": ("is", "set")}, fields=["name", "student_name", "customer", "campus"])
	}


def _waiting() -> list[dict]:
	"""Deposits no payment could be matched to: no student or application number found, or one that is not known"""
	rows = []
	for d in student_payments.unallocated_deposits():
		if any(frappe.db.exists("Student Applicant", r) for r in references_in(d.description, d.reference_number)):
			continue  # an application fee: matched by educore.admissions.fees
		numbers = student_payments.student_numbers_in(d.description, d.reference_number)
		rows.append({**d, "amount": flt(d.unallocated_amount), "numbers_found": numbers})
	return rows


@frappe.whitelist(methods=["GET"])
def payments(view: str = "received", search: str | None = None) -> dict:
	_require_role()
	students = _student_by_customer()
	waiting = _waiting()
	if view == "waiting":
		rows = waiting
		if search:
			q = search.strip().lower()
			rows = [r for r in rows if q in f"{r.description} {r.reference_number}".lower()]
	else:
		received = frappe.get_all(
			"Payment Entry",
			filters={"docstatus": 1, "payment_type": "Receive", "party_type": "Customer", "party": ("in", list(students) or [""])},
			fields=["name", "posting_date", "party", "paid_amount", "unallocated_amount", "reference_no"],
			order_by="posting_date desc, name desc",
			limit=500,
		)
		rows = []
		for p in received:
			s = students.get(p.party) or {}
			row = {**p, "student": s.get("name"), "student_name": s.get("student_name"), "campus": s.get("campus")}
			if search and search.strip().lower() not in f"{row['student']} {row['student_name']} {p.reference_no}".lower():
				continue
			rows.append(row)
	return {"rows": rows, "counts": {"waiting": len(waiting)}}


@frappe.whitelist(methods=["POST"])
def assign(bank_transaction: str, student: str | None = None, sponsor: str | None = None) -> dict:
	"""A deposit without a usable student or sponsor number, recorded as that student's or sponsor's payment"""
	from educore.finance import sponsors

	_require_role()
	if not flt(frappe.db.get_value("Bank Transaction", bank_transaction, "unallocated_amount")):
		frappe.throw(_("{0} is already matched").format(bank_transaction))
	if sponsor:
		if not frappe.db.exists("Sponsor", sponsor):
			frappe.throw(_("Choose a sponsor"))
		return {"payment_entry": sponsors.record_payment(sponsor, bank_transaction)}
	if not student or not frappe.db.exists("Student", student):
		frappe.throw(_("Choose a student"))
	entry = student_payments.record_payment(student, bank_transaction)
	if not entry:
		frappe.throw(_("{0} has no customer account to receive the payment").format(student))
	return {"payment_entry": entry}


@frappe.whitelist(methods=["GET"])
def find_sponsors(search: str) -> list[dict]:
	"""Sponsors by name or number, to assign a deposit to"""
	_require_role()
	like = f"%{(search or '').strip()}%"
	return frappe.get_all(
		"Sponsor",
		or_filters=[["sponsor_name", "like", like], ["name", "like", like]],
		fields=["name", "sponsor_name"],
		order_by="sponsor_name asc",
		limit=20,
	)


@frappe.whitelist(methods=["POST"])
def match_now() -> dict:
	from educore.finance import sponsors

	_require_role()
	return {"matched": student_payments.match_bank_transactions() + sponsors.match_bank_transactions()}


@frappe.whitelist(methods=["GET"])
def find_students(search: str) -> list[dict]:
	"""Students by name or number, to assign a deposit to"""
	_require_role()
	like = f"%{(search or '').strip()}%"
	return frappe.get_all(
		"Student",
		or_filters=[["student_name", "like", like], ["name", "like", like], ["educore_national_id", "like", like]],
		fields=["name", "student_name", "campus"],
		order_by="student_name asc",
		limit=20,
	)
