"""EduCore Demo University's student fees (development only): a fee structure for every offering in 2026 and
2027, invoices for enrolments made before fees existed, and a few payments.

create_fee_structures() runs from create_demo_university; invoice_and_pay() from demo_students.create.
"""

import frappe
from frappe.utils import flt

from educore.finance.student_fees import CENTRAL_BANK, fee_structure_for, invoice_enrollment

#: annual tuition (NAD), full-time, by programme code (else by qualification)
TUITION = {"BNS": 32_000, "BEDP": 30_000}
TUITION_BY_QUALIFICATION = {"Bachelor's Degree": 28_000, "Honours Degree": 30_000, "Diploma": 22_000}
MODE_FACTOR = {"Full-time": 1.0, "Part-time": 0.6, "Distance": 0.5, "Blended": 0.8}
OTHER_FEES = {"Registration Fee": 1_500, "Examination Fee": 1_200, "Technology Levy": 800}
#: each year's fees on the year before
INCREASE = {"2026": 1.0, "2027": 1.06}

#: student login: share of the invoice paid
PAYMENTS = {"student1.whk": 1.0, "student1.kmp": 0.5}


def _round(amount):
	return round(amount / 50) * 50


def create_fee_structures(years=("2026", "2027")) -> int:
	created = 0
	for offering in frappe.get_all("Programme Offering", fields=["name", "program", "mode_of_study"]):
		code, qualification = frappe.db.get_value(
			"Program", offering.program, ["educore_programme_code", "educore_qualification_type"]
		)
		tuition = TUITION.get(code) or TUITION_BY_QUALIFICATION[qualification]
		for year in years:
			if fee_structure_for(offering.name, year):
				continue
			factor = INCREASE[year]
			components = [
				{"fees_category": "Tuition Fee", "amount": _round(tuition * MODE_FACTOR[offering.mode_of_study] * factor)},
				*({"fees_category": category, "amount": _round(amount * factor)} for category, amount in OTHER_FEES.items()),
			]
			structure = frappe.get_doc(
				{
					"doctype": "Fee Structure",
					"educore_programme_offering": offering.name,
					"academic_year": year,
					"components": components,
				}
			)
			structure.insert(ignore_permissions=True)
			structure.submit()
			created += 1
	return created


def invoice_and_pay() -> dict:
	invoiced = 0
	for enrollment in frappe.get_all("Program Enrollment", filters={"docstatus": 1}, pluck="name"):
		if invoice_enrollment(frappe.get_doc("Program Enrollment", enrollment)):
			invoiced += 1

	paid = 0
	company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company")
	bank = f"{CENTRAL_BANK} - {frappe.get_cached_value('Company', company, 'abbr')}"
	for login, share in PAYMENTS.items():
		student = frappe.db.get_value("Student", {"user": f"{login}@educore.localhost"})
		invoice = frappe.db.get_value("Sales Invoice", {"student": student, "docstatus": 1}, ["name", "outstanding_amount", "grand_total"], as_dict=True)
		if not invoice or flt(invoice.outstanding_amount) < flt(invoice.grand_total):
			continue  # already paid (in part): leave it
		from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

		payment = get_payment_entry("Sales Invoice", invoice.name, bank_account=bank)
		amount = flt(invoice.grand_total * share, 2)
		payment.paid_amount = payment.received_amount = amount
		payment.references[0].allocated_amount = amount
		payment.reference_no = f"EFT-DEMO-{invoice.name}"
		payment.reference_date = "2026-02-20"
		payment.posting_date = "2026-02-20"
		payment.insert(ignore_permissions=True)
		payment.submit()
		paid += 1
	return {"invoiced": invoiced, "paid": paid}
