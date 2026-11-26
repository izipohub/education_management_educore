"""EduCore Demo University's student fees (development only): a fee structure for every offering in 2026 and
2027, invoices for enrolments made before fees existed, and a few payments.

create_fee_structures() runs from create_demo_university; invoice_and_pay() from demo_students.create.
"""

import frappe
from frappe.utils import flt

from educore.finance.student_fees import CENTRAL_BANK, fee_structure_for, invoice_enrollment

#: annual tuition (NAD), full-time, by programme code (else by qualification)
TUITION = {"BNS": 32_000, "BEDP": 30_000, "MBA": 45_000}
TUITION_BY_QUALIFICATION = {"Bachelor's Degree": 28_000, "Honours Degree": 30_000, "Diploma": 22_000}
MODE_FACTOR = {"Full-time": 1.0, "Part-time": 0.6, "Distance": 0.5, "Blended": 0.8}
OTHER_FEES = {"Registration Fee": 1_500, "Examination Fee": 1_200, "Technology Levy": 800}
#: each year's fees on the year before
INCREASE = {"2026": 1.0, "2027": 1.06}

#: student login: share of the invoice paid
PAYMENTS = {"student1.whk": 1.0, "student1.kmp": 0.5, "student2.kmp": 1.0}


def _round(amount):
	return round(amount / 50) * 50


def create_fee_structures(years=("2026", "2027")) -> int:
	create_instalment_plans()
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


#: academic year: (due date, share of the year's fees), as many universities split the year
INSTALMENTS = {"2027": (("2027-02-15", 40), ("2027-05-14", 30), ("2027-08-16", 30))}


def create_instalment_plans() -> int:
	made = 0
	for year, rows in INSTALMENTS.items():
		if frappe.db.exists("Instalment Plan", year) or not frappe.db.exists("Academic Year", year):
			continue
		frappe.get_doc(
			{"doctype": "Instalment Plan", "academic_year": year, "instalments": [{"due_date": d, "share": s} for d, s in rows]}
		).insert(ignore_permissions=True)
		made += 1
	return made


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


#: demo sponsors: name, type, contact, students (login, cover, value, the sponsor's reference), paid by EFT; as the
#: students' applications say who pays their fees
SPONSORS = (
	(
		"Namibia Students Financial Assistance Fund", "Government fund", "Student Funding Office",
		(("student1.osh", "Full fees", 0, "NSFAF-2026-11873"),), 15_000,
	),
)


def create_sponsors() -> dict:
	"""Sponsors paying demo students' 2026 fees, and a sponsor payment by EFT matched by its number"""
	from frappe.utils import add_days, nowdate

	from educore.finance import sponsors

	made = paid = 0
	for name, kind, contact, students, payment in SPONSORS:
		sponsor = frappe.db.get_value("Sponsor", {"sponsor_name": name})
		if not sponsor:
			sponsor = frappe.get_doc(
				{"doctype": "Sponsor", "sponsor_name": name, "sponsor_type": kind, "contact_person": contact, "payment_days": 60}
			).insert(ignore_permissions=True).name
			made += 1
		# students who choose NSFAF on their application are named on its page (educore.admissions.funding)
		if kind == "Government fund" and frappe.db.exists("Funding Route", "NSFAF") and not frappe.db.get_value("Funding Route", "NSFAF", "sponsor"):
			route = frappe.get_doc("Funding Route", "NSFAF")
			route.sponsor = sponsor
			route.save(ignore_permissions=True)
		for login, cover, value, reference in students:
			student = frappe.db.get_value("Student", {"user": f"{login}@educore.localhost"})
			if not student or frappe.db.exists("Sponsorship", {"sponsor": sponsor, "student": student, "academic_year": "2026"}):
				continue
			doc = frappe.get_doc(
				{
					"doctype": "Sponsorship",
					"sponsor": sponsor,
					"student": student,
					"academic_year": "2026",
					"cover_type": cover,
					"cover_value": value,
					"sponsor_reference": reference,
				}
			).insert(ignore_permissions=True)
			sponsors.apply(doc.name)
		bank_account = frappe.db.get_single_value("Admission Settings", "fee_bank_account")
		customer = frappe.db.get_value("Sponsor", sponsor, "customer")
		already = frappe.db.exists("Payment Entry", {"party": customer, "docstatus": 1}) if customer else True
		if payment and bank_account and not already:
			line = frappe.get_doc(
				{
					"doctype": "Bank Transaction",
					"date": add_days(nowdate(), -3),
					"bank_account": bank_account,
					"company": frappe.db.get_value("Bank Account", bank_account, "company"),
					"deposit": payment,
					"currency": "NAD",
					"description": f"NSFAF TUITION PAYMENT {sponsor} BATCH 2026/03",
					"reference_number": "NSFAF-PMT-2026-03",
				}
			).insert(ignore_permissions=True)
			line.submit()
			if sponsors.record_payment(sponsor, line.name):
				paid += 1
	return {"sponsors": made, "sponsor_payments": paid}


#: login: a hold Finance placed (educore.finance.clearance)
HOLDS = {"student2.osh": "Payment arrangement for the 2026 fees not kept"}


def create_holds() -> int:
	from frappe.utils import add_days, nowdate

	made = 0
	for login, reason in HOLDS.items():
		student = frappe.db.get_value("Student", {"user": f"{login}@educore.localhost"})
		if not student or frappe.db.exists("Student Hold", {"student": student}):
			continue
		frappe.get_doc(
			{
				"doctype": "Student Hold",
				"student": student,
				"reason": reason,
				"status": "Active",
				"placed_by": "student-fees-officer.osh@educore.localhost",
				"placed_on": add_days(nowdate(), -12),
			}
		).insert(ignore_permissions=True)
		made += 1
	return made


#: login: a fee waiver requested by the campus's Student Fees Officer, waiting for the Bursar (educore.finance.waivers)
WAIVERS = {"student1.kmp": ("2026", "Percent of fees", 25, "Death of the parent who paid the fees; the family asks for help")}


def create_waivers() -> int:
	from frappe.utils import add_days, nowdate

	made = 0
	for login, (year, waive, value, reason) in WAIVERS.items():
		student, campus = frappe.db.get_value("Student", {"user": f"{login}@educore.localhost"}, ["name", "campus"]) or (None, None)
		if not student or frappe.db.exists("Fee Waiver", {"student": student}):
			continue
		officer = f"student-fees-officer.{login.split('.')[-1]}@educore.localhost"
		frappe.get_doc(
			{
				"doctype": "Fee Waiver",
				"student": student,
				"academic_year": year,
				"waive": waive,
				"value": value,
				"reason": reason,
				"requested_by": officer if frappe.db.exists("User", officer) else "Administrator",
				"requested_on": add_days(nowdate(), -3),
			}
		).insert(ignore_permissions=True)
		made += 1
	return made
