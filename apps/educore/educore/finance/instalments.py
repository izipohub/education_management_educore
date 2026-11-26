"""Instalment plans: when a year's fees are due.

The Bursar sets each academic year's instalments (Instalment Plan: a due date and a share of the fees each, adding up
to 100%). Every invoice of the year's fees made from then on carries them as its ERPNext payment schedule, so
ERPNext's own ageing and reports follow them; an instalment already past on the invoice date falls due on that day.
Without a plan, the year's fees are due in full a month after the invoice (educore.finance.student_fees).

What a student has paid (and what sponsors took over, by credit note) settles the earliest instalments first: what is
overdue is what the instalments due by today still lack.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def validate_plan(doc, method=None):
	if not doc.instalments:
		frappe.throw(_("Add the instalments"))
	dates = [getdate(r.due_date) for r in doc.instalments]
	if len(set(dates)) != len(dates):
		frappe.throw(_("Two instalments fall due on the same day"))
	if any(flt(r.share) <= 0 for r in doc.instalments):
		frappe.throw(_("Each instalment is a share of the fees above 0%"))
	if abs(sum(flt(r.share) for r in doc.instalments) - 100) > 0.01:
		frappe.throw(_("The instalments add up to {0}%, not 100%").format(round(sum(flt(r.share) for r in doc.instalments), 2)))
	year = frappe.db.get_value("Academic Year", doc.academic_year, ["year_start_date", "year_end_date"], as_dict=True)
	if year and year.year_start_date and year.year_end_date:
		end = getdate(year.year_end_date)
		if any(d > end for d in dates):
			frappe.throw(_("An instalment falls due after the {0} academic year ends").format(doc.academic_year))
	doc.instalments = sorted(doc.instalments, key=lambda r: getdate(r.due_date))
	for i, row in enumerate(doc.instalments, start=1):
		row.idx = i


def plan_for(academic_year: str | None):
	return frappe.get_doc("Instalment Plan", academic_year) if academic_year and frappe.db.exists("Instalment Plan", academic_year) else None


def apply(invoice, academic_year: str) -> bool:
	"""The year's instalments as the (inserted, draft) invoice's payment schedule; True when there is a plan"""
	plan = plan_for(academic_year)
	if not plan:
		return False
	posting = getdate(invoice.posting_date)
	shares: dict = {}
	for row in plan.instalments:
		day = max(getdate(row.due_date), posting)
		shares[day] = shares.get(day, 0) + flt(row.share)
	total = flt(invoice.rounded_total or invoice.grand_total)
	invoice.payment_terms_template = None
	invoice.set("payment_schedule", [])
	left = total
	days = sorted(shares)
	for i, day in enumerate(days):
		amount = flt(left if i == len(days) - 1 else total * shares[day] / 100, 2)
		left = flt(left - amount, 2)
		invoice.append(
			"payment_schedule",
			{
				"due_date": day,
				"invoice_portion": shares[day],
				"payment_amount": amount,
				"outstanding": amount,
				"description": _("Instalment {0} of {1}").format(i + 1, len(days)),
			},
		)
	invoice.due_date = days[-1]
	return True


def due(student: str) -> dict:
	"""The student's instalments still to pay, what is overdue, and the next one"""
	today = getdate(nowdate())
	rows = []
	for invoice in frappe.get_all(
		"Sales Invoice",
		filters={"student": student, "docstatus": 1, "is_return": 0, "outstanding_amount": (">", 0)},
		fields=["name", "grand_total", "rounded_total", "outstanding_amount", "due_date"],
		order_by="posting_date asc, name asc",
	):
		schedule = frappe.get_all(
			"Payment Schedule",
			filters={"parent": invoice.name, "parenttype": "Sales Invoice"},
			fields=["due_date", "payment_amount"],
			order_by="due_date asc, idx asc",
		) or [frappe._dict(due_date=invoice.due_date, payment_amount=invoice.rounded_total or invoice.grand_total)]
		settled = flt((invoice.rounded_total or invoice.grand_total) - invoice.outstanding_amount)
		for row in schedule:
			taken = min(settled, flt(row.payment_amount))
			settled -= taken
			left = flt(flt(row.payment_amount) - taken, 2)
			if left > 0:
				rows.append({"invoice": invoice.name, "due_date": str(row.due_date), "amount": flt(row.payment_amount), "left": left})
	overdue = flt(sum(r["left"] for r in rows if getdate(r["due_date"]) < today), 2)
	upcoming = [r for r in rows if getdate(r["due_date"]) >= today]
	return {
		"instalments": rows,
		"overdue": overdue,
		"next_due": upcoming[0]["due_date"] if upcoming else None,
		"next_amount": upcoming[0]["left"] if upcoming else 0.0,
	}
