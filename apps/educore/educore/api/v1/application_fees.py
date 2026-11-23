"""Application fees, for Finance: what is outstanding, paid or waived, and waiving one with a reason.

Fees are paid by EFT (matched from the bank statement, educore.admissions.fees) or at a campus cashier for a
paper form; waiving is Finance's decision (fees.WAIVE_ROLES), through educore.api.v1.admissions.waive_fee.
"""

import frappe
from frappe import _

from educore.admissions.fees import WAIVE_ROLES

STATUSES = ("Unpaid", "Paid", "Waived")


@frappe.whitelist(methods=["GET"])
def fees(status: str = "Unpaid", search: str | None = None) -> dict:
	if not set(frappe.get_roles()) & set(WAIVE_ROLES):
		frappe.throw(_("Application fees are for Finance"), frappe.PermissionError)
	if status not in STATUSES:
		frappe.throw(_("Unknown status {0}").format(status))
	base = {"application_status": ("not in", ("Draft",)), "educore_fee_amount": (">", 0)}
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [["title", "like", like], ["name", "like", like]]
	rows = frappe.get_all(
		"Student Applicant",
		filters={**base, "educore_fee_status": status},
		or_filters=or_filters,
		fields=[
			"name", "title as applicant", "campus", "academic_year", "application_date",
			"educore_applicant_user as online", "educore_fee_amount as amount", "educore_fee_paid_on as paid_on",
			"educore_fee_note as note", "educore_international as international",
		],
		order_by="application_date asc, name asc",
		limit=500,
	)
	for row in rows:
		row["online"] = bool(row.online)
	return {
		"rows": rows,
		"counts": {s: frappe.db.count("Student Applicant", {**base, "educore_fee_status": s}) for s in STATUSES},
	}
