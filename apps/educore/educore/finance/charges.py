"""One-off charges to a student: a service fee, a disciplinary fine. Invoiced at once to the student's fee account,
posted to their campus, and paid like any fee (by EFT with the student number); an unpaid one is cancelled when what
it was for falls away (a fee already paid is Finance's to refund)."""

import frappe
from frappe.utils import flt, nowdate


def invoice(student: str, campus: str | None, item: str, description: str, amount: float, remarks: str) -> str:
	from education.education.doctype.fee_schedule.fee_schedule import get_customer_from_student

	from educore.finance.student_fees import _as_system, ensure_fee_setup, ensure_fiscal_year

	with _as_system():
		company = (frappe.db.get_value("Campus", campus, "company") if campus else None) or frappe.defaults.get_global_default("company")
		if not frappe.db.exists("Item", item):
			ensure_fee_setup(company)
		cost_center = (frappe.db.get_value("Campus", campus, "cost_center") if campus else None) or frappe.get_cached_value("Company", company, "cost_center")
		ensure_fiscal_year(nowdate(), company)
		doc = frappe.new_doc("Sales Invoice")
		doc.update(
			{
				"customer": get_customer_from_student(student),
				"student": student,
				"company": company,
				"set_posting_time": 1,
				"posting_date": nowdate(),
				"due_date": nowdate(),
				"cost_center": cost_center,
				"campus": campus,
				"remarks": remarks,
			}
		)
		doc.append(
			"items",
			{
				"item_code": item,
				"item_name": item,
				"description": description,
				"qty": 1,
				"rate": flt(amount, 2),
				"cost_center": cost_center,
				"income_account": frappe.db.get_value("Fee Category Default", {"parent": item, "company": company}, "income_account"),
			},
		)
		doc.insert(ignore_permissions=True)
		doc.submit()
		return doc.name


def unpaid(name: str | None) -> bool:
	return bool(name) and flt(frappe.db.get_value("Sales Invoice", name, "outstanding_amount")) > 0


def cancel_if_unpaid(name: str | None):
	"""Cancel the invoice if nothing of it is paid yet"""
	from educore.finance.student_fees import _as_system

	if not name:
		return
	total, outstanding, docstatus = frappe.db.get_value("Sales Invoice", name, ["grand_total", "outstanding_amount", "docstatus"])
	if docstatus == 1 and flt(outstanding) >= flt(total):
		with _as_system():
			frappe.get_doc("Sales Invoice", name).cancel()
