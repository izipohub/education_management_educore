"""Student fee payments matched from the bank statement, by student number (as application fees are matched by
application number, educore.admissions.fees).

Students pay by EFT into the university's bank account with their student number as the reference. Finance imports
the bank statement into ERPNext as usual (Bank Transactions); match_bank_transactions(), run hourly and on demand,
finds a student number in each deposit's description or reference and records the payment: an ERPNext Payment Entry
from the student's Customer, set against their oldest unpaid invoices first (any remainder stays as an advance, which
registration counts towards the deposit), and reconciles the bank line against it. A deposit with no student number
in it is left for Finance to assign to a student (assign()).

The booking runs as a system action: it is the consequence of the bank statement, not of anyone's accounting rights.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate

#: a student number in free text, e.g. "EDU-STU-2026-00003" (Education's naming series)
STUDENT_NUMBER = re.compile(r"\b[A-Z][A-Z0-9]*-STU-\d{4}-\d{3,}\b", re.IGNORECASE)


def student_numbers_in(*texts) -> list[str]:
	found = []
	for text in texts:
		for match in STUDENT_NUMBER.findall(text or ""):
			number = match.upper()
			if number not in found:
				found.append(number)
	return found


def _university_bank_accounts() -> list[str]:
	return frappe.get_all("Bank Account", filters={"is_company_account": 1, "disabled": 0}, pluck="name")


def unallocated_deposits(limit: int = 500) -> list:
	"""Deposits on the university's bank accounts not yet reconciled with anything"""
	accounts = _university_bank_accounts()
	if not accounts:
		return []
	return frappe.get_all(
		"Bank Transaction",
		filters={"docstatus": 1, "bank_account": ("in", accounts), "deposit": (">", 0), "unallocated_amount": (">", 0)},
		fields=["name", "date", "deposit", "unallocated_amount", "description", "reference_number", "bank_account"],
		order_by="date asc, name asc",
		limit=limit,
	)


def match_bank_transactions() -> int:
	"""Scheduled hourly: record the payments of students whose number appears on an unallocated deposit"""
	matched = 0
	for deposit in unallocated_deposits():
		from educore.finance.sponsors import sponsor_numbers_in

		if sponsor_numbers_in(deposit.description, deposit.reference_number):
			continue  # a sponsor's payment, though it may list its students (educore.finance.sponsors)
		numbers = [n for n in student_numbers_in(deposit.description, deposit.reference_number) if frappe.db.exists("Student", n)]
		# one student per deposit: a line naming two students is left for Finance to split
		if len(numbers) == 1 and record_payment(numbers[0], deposit.name):
			matched += 1
	return matched


def record_payment(student: str, bank_transaction: str) -> str | None:
	from educore.finance.student_fees import _as_system

	with _as_system():
		return _record_payment(student, bank_transaction)


def _record_payment(student: str, bank_transaction: str) -> str | None:
	customer = frappe.db.get_value("Student", student, "customer")
	if not customer:
		return None
	return book_receipt(customer, bank_transaction, _("Student fees, {0}").format(student))


def book_receipt(customer: str, bank_transaction: str, what: str) -> str | None:
	"""A deposit on the bank statement as a Payment Entry from this customer (a student or a sponsor), set against
	their oldest unpaid invoices first, the bank line reconciled against it. Runs as the caller's user: callers
	switch to the system first (student_fees._as_system)."""
	from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import _reconcile_vouchers
	from erpnext.accounts.party import get_party_account

	from educore.finance.student_fees import ensure_fiscal_year

	txn = frappe.get_doc("Bank Transaction", bank_transaction)
	amount = flt(txn.unallocated_amount)
	if amount <= 0:
		return None
	bank_gl, company = frappe.db.get_value("Bank Account", txn.bank_account, ["account", "company"])
	ensure_fiscal_year(txn.date, company)

	entry = frappe.new_doc("Payment Entry")
	entry.update(
		{
			"payment_type": "Receive",
			"company": company,
			"posting_date": getdate(txn.date),
			"party_type": "Customer",
			"party": customer,
			"paid_from": get_party_account("Customer", customer, company),
			"paid_to": bank_gl,
			"paid_amount": amount,
			"received_amount": amount,
			# one currency (N$): the student's account, the bank and the company
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"reference_no": (txn.reference_number or txn.name)[:140],
			"reference_date": getdate(txn.date),
			"remarks": _("{0}: from the bank statement ({1})").format(what, txn.name),
		}
	)
	# the oldest unpaid invoices first; what is left stays as an advance (the deposit towards a new year)
	left = amount
	for invoice in frappe.get_all(
		"Sales Invoice",
		filters={"customer": customer, "docstatus": 1, "outstanding_amount": (">", 0), "company": company},
		fields=["name", "outstanding_amount", "grand_total", "due_date"],
		order_by="posting_date asc, name asc",
	):
		if left <= 0:
			break
		allocated = min(left, flt(invoice.outstanding_amount))
		entry.append(
			"references",
			{
				"reference_doctype": "Sales Invoice",
				"reference_name": invoice.name,
				"total_amount": invoice.grand_total,
				"outstanding_amount": invoice.outstanding_amount,
				"allocated_amount": allocated,
				"due_date": invoice.due_date,
			},
		)
		left -= allocated
	entry.insert(ignore_permissions=True)
	entry.submit()
	_reconcile_vouchers(txn.name, [{"payment_doctype": "Payment Entry", "payment_name": entry.name, "amount": amount}])
	return entry.name


@frappe.whitelist(methods=["POST"])
def match_now() -> int:
	"""For Finance: match the bank statement without waiting for the hour"""
	frappe.only_for(("Bursar", "Finance Officer", "Student Fees Officer", "Accounts Manager", "System Manager"))
	return match_bank_transactions()
