"""The application fee (docs/architecture/online-applications.md 3.4).

- The amount depends on the applicant: Namibian or international (Admission Settings).
- Applicants pay by EFT with their application number as the reference. Finance imports the bank statement into
  ERPNext as usual (Bank Transactions on the fee bank account); match_bank_transactions(), run hourly and on
  demand, finds application numbers in each deposit's description and reference, books the fee (Journal Entry:
  bank debit, Application Fees credit, on the campus cost center of the first choice), reconciles the statement
  line against it with ERPNext's own reconciliation, and marks the fee paid. A deposit below the fee, or for an
  application already settled, is left for Finance with a note on the application.
- Admissions may waive the fee, with a reason.
- Card payments (DPO) come once the university's merchant account exists; card_payments_enabled stays off.

The booking runs as a system action: it is the consequence of the bank statement, not of anyone's accounting rights.
"""

import re

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime

from educore.admissions import application as rules
from educore.admissions import pathways

#: An application number in free text, e.g. "EDU-APP-2026-00016" (Education's naming series)
REFERENCE = re.compile(r"\b[A-Z][A-Z0-9]*-APP-\d{4}-\d{3,}\b", re.IGNORECASE)


def is_international(doc) -> bool:
	return pathways.is_international(doc)


def fee_for(doc) -> float:
	settings = rules.settings()
	return flt(settings.fee_international if is_international(doc) else settings.fee_namibian)


def set_fee(doc):
	"""An online application's fee, while unpaid (home or international, Admission Settings)"""
	if doc.get("educore_applicant_user") and (doc.get("educore_fee_status") or "Unpaid") == "Unpaid":
		doc.educore_fee_status = "Unpaid"
		doc.educore_fee_amount = fee_for(doc)


def settled(doc) -> bool:
	return doc.get("educore_fee_status") in ("Paid", "Waived")


# --- matching the bank statement -----------------------------------------------------------------------


def references_in(*texts) -> list[str]:
	found = []
	for text in texts:
		for match in REFERENCE.findall(text or ""):
			reference = match.upper()
			if reference not in found:
				found.append(reference)
	return found


def match_bank_transactions() -> int:
	"""Scheduled hourly: settle applications whose number appears on an unallocated deposit"""
	settings = rules.settings()
	if not (settings.fee_bank_account and settings.fee_income_account):
		return 0
	matched = 0
	deposits = frappe.get_all(
		"Bank Transaction",
		filters={
			"docstatus": 1,
			"bank_account": settings.fee_bank_account,
			"deposit": (">", 0),
			"unallocated_amount": (">", 0),
		},
		fields=["name", "date", "deposit", "unallocated_amount", "description", "reference_number"],
		order_by="date asc, name asc",
	)
	for deposit in deposits:
		for reference in references_in(deposit.description, deposit.reference_number):
			if frappe.db.exists("Student Applicant", {"name": reference, "educore_applicant_user": ("is", "set")}):
				if record_payment(reference, deposit.name):
					matched += 1
	# no commit here: a scheduled job and a web request each commit when they finish (and a test rolls back)
	return matched


def record_payment(applicant: str, bank_transaction: str) -> bool:
	from educore.finance.student_fees import _as_system

	with _as_system():
		return _record_payment(applicant, bank_transaction)


def _note(applicant: str, text: str):
	frappe.db.set_value("Student Applicant", applicant, "educore_fee_note", text, update_modified=False)


def _record_payment(applicant: str, bank_transaction: str) -> bool:
	from erpnext.accounts.doctype.bank_reconciliation_tool.bank_reconciliation_tool import _reconcile_vouchers

	from educore.finance.student_fees import ensure_fiscal_year

	doc = frappe.get_doc("Student Applicant", applicant)
	txn = frappe.get_doc("Bank Transaction", bank_transaction)
	if settled(doc):
		if doc.educore_fee_bank_transaction != txn.name:
			_note(applicant, _("A further deposit ({0}) carries this application's number: refund or reallocate it.").format(txn.name))
		return False
	fee = flt(doc.educore_fee_amount) or fee_for(doc)
	if flt(txn.unallocated_amount) < fee:
		_note(
			applicant,
			_("Bank line {0} has N$ {1}, less than the fee of N$ {2}: check it with Finance.").format(
				txn.name, flt(txn.unallocated_amount), fee
			),
		)
		return False

	settings = rules.settings()
	bank_gl, company = frappe.db.get_value("Bank Account", settings.fee_bank_account, ["account", "company"])
	cost_center = (
		frappe.db.get_value("Campus", doc.campus, "cost_center")
		if doc.get("campus")
		else frappe.get_cached_value("Company", company, "cost_center")
	)
	ensure_fiscal_year(txn.date, company)
	entry = frappe.get_doc(
		{
			"doctype": "Journal Entry",
			"voucher_type": "Bank Entry",
			"company": company,
			"posting_date": txn.date,
			"cheque_no": (txn.reference_number or txn.name)[:140],
			"cheque_date": txn.date,
			"user_remark": _("Application fee {0}").format(applicant),
			"accounts": [
				{"account": bank_gl, "debit_in_account_currency": fee, "cost_center": cost_center},
				{"account": settings.fee_income_account, "credit_in_account_currency": fee, "cost_center": cost_center},
			],
		}
	)
	entry.insert(ignore_permissions=True)
	entry.submit()
	_reconcile_vouchers(txn.name, [{"payment_doctype": "Journal Entry", "payment_name": entry.name, "amount": fee}])

	values = {
		"educore_fee_status": "Paid",
		"educore_fee_amount": fee,
		"educore_fee_paid_on": getdate(txn.date),
		"educore_fee_voucher": entry.name,
		"educore_fee_bank_transaction": txn.name,
		"educore_fee_note": None,
	}
	if flt(txn.unallocated_amount) > fee:
		values["educore_fee_note"] = _("N$ {0} more than the fee was paid on {1}: refund or reallocate it.").format(
			flt(txn.unallocated_amount) - fee, txn.name
		)
	frappe.db.set_value("Student Applicant", applicant, values)
	doc.add_comment("Info", _("Application fee received: {0}, reconciled with {1}").format(entry.name, txn.name))
	return True


@frappe.whitelist(methods=["POST"])
def match_now() -> int:
	"""For Finance and the Registrar: match the bank statement without waiting for the hour"""
	frappe.only_for(("Accounts User", "Accounts Manager", "Registrar", "System Manager"))
	return match_bank_transactions()


# --- waivers -------------------------------------------------------------------------------------------


def waive(applicant: str, reason: str):
	doc = frappe.get_doc("Student Applicant", applicant)
	if settled(doc):
		frappe.throw(_("The fee is already {0}").format(doc.educore_fee_status.lower()))
	if not (reason or "").strip():
		frappe.throw(_("Give the reason for waiving the fee"))
	frappe.db.set_value(
		"Student Applicant",
		applicant,
		{
			"educore_fee_status": "Waived",
			"educore_fee_note": _("Waived by {0} on {1}: {2}").format(
				frappe.session.user, now_datetime().strftime("%d-%m-%Y"), reason.strip()
			),
		},
	)
	doc.add_comment("Info", _("Application fee waived: {0}").format(reason.strip()))
