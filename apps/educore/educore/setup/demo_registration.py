"""Re-registration for 2027 in the demo (development only).

- The curriculum: each programme course gets its year of study and semester from its code (CMP2511: year 2,
  semester 1; MBA courses are year 1).
- The 2027 registration period: open now, closing 31 January 2027, late registration to 14 February (N$ 500).
- Returning students, as a university would have them:
  * student1.whk (Ndapewa Amukoto) paid 2026 and her deposit: she can register (left for you to try);
  * student1.osh (Martha Shilongo) paid 2026 and her deposit and has submitted: waiting for the Faculty of Science
    and Technology's officer at Oshakati (faculty-officer.fst.osh);
  * student2.osh (Tangeni Iiyambo) is on hold by the faculty;
  * the others still owe 2026 fees, which blocks them.

Called from demo_students.create; re-running adds only what is missing.
"""

import frappe
from frappe.utils import flt

from educore.access.demo_users import DOMAIN

PERIOD = {"academic_year": "2027", "opens_on": "2026-11-01", "closes_on": "2027-01-31", "late_until": "2027-02-14", "late_fee": 500, "changes_until": "2027-02-28"}
#: login: (pays the rest of 2026, pays the deposit, registers)
STUDENTS = {"student1.whk": (False, True, False), "student1.osh": (True, True, True)}
ON_HOLD = {"student2.osh": "Outstanding practical teaching portfolio for 2026. See the Faculty Officer."}


def _year_and_semester(code: str | None) -> tuple[int, str]:
	if not code or len(code) < 7 or not code[3].isdigit():
		return 1, "Year"
	year = int(code[3])
	if code.startswith("MBA"):
		year = 1
	semester = {"1": "Semester 1", "2": "Semester 2"}.get(code[5], "Year")
	return year, semester


def set_curriculum():
	for program in frappe.get_all("Program", filters={"educore_programme_code": ("is", "set")}, pluck="name"):
		doc = frappe.get_doc("Program", program)
		changed = False
		for row in doc.courses:
			if row.get("educore_year"):
				continue
			row.educore_year, row.educore_semester = _year_and_semester(frappe.db.get_value("Course", row.course, "educore_course_code"))
			changed = True
		if changed:
			doc.save(ignore_permissions=True)


def _bank():
	from educore.finance.student_fees import CENTRAL_BANK

	company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company")
	return company, f"{CENTRAL_BANK} - {frappe.get_cached_value('Company', company, 'abbr')}"


def _pay_balance(student: str):
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	_company, bank = _bank()
	for invoice in frappe.get_all("Sales Invoice", filters={"student": student, "docstatus": 1, "outstanding_amount": (">", 0)}, pluck="name"):
		payment = get_payment_entry("Sales Invoice", invoice, bank_account=bank)
		payment.reference_no = f"EFT-DEMO-{invoice}"
		payment.reference_date = payment.posting_date = "2026-10-15"
		payment.insert(ignore_permissions=True)
		payment.submit()


def _pay_deposit(student: str, offering: str):
	"""An advance payment, not yet set against an invoice: the registration deposit"""
	from educore.registration import rules

	if rules.paid_in_advance(student) >= rules.deposit_required(offering, PERIOD["academic_year"], student):
		return
	company, bank = _bank()
	customer = frappe.db.get_value("Student", student, "customer")
	amount = rules.deposit_required(offering, PERIOD["academic_year"], student)
	payment = frappe.get_doc(
		{
			"doctype": "Payment Entry",
			"payment_type": "Receive",
			"company": company,
			"posting_date": "2026-11-10",
			"party_type": "Customer",
			"party": customer,
			"paid_to": bank,
			"paid_amount": amount,
			"received_amount": amount,
			"reference_no": f"EFT-DEMO-DEPOSIT-{student}",
			"reference_date": "2026-11-10",
			"remarks": "Registration deposit 2027",
		}
	)
	payment.setup_party_account_field()
	payment.set_missing_values()
	payment.insert(ignore_permissions=True)
	payment.submit()


def create():
	from educore.api.v1 import registration

	set_curriculum()
	if not frappe.db.exists("Registration Period", PERIOD["academic_year"]):
		frappe.get_doc({"doctype": "Registration Period", **PERIOD}).insert(ignore_permissions=True)
	elif not frappe.db.get_value("Registration Period", PERIOD["academic_year"], "changes_until"):
		frappe.db.set_value("Registration Period", PERIOD["academic_year"], "changes_until", PERIOD["changes_until"])

	for login, note in ON_HOLD.items():
		student = frappe.db.get_value("Student", {"user": f"{login}@{DOMAIN}"})
		if student and frappe.db.get_value("Student", student, "educore_academic_standing") != "On hold":
			frappe.db.set_value("Student", student, {"educore_academic_standing": "On hold", "educore_standing_note": note})

	for login, (pay_balance, pay_deposit, register) in STUDENTS.items():
		user = f"{login}@{DOMAIN}"
		student = frappe.db.get_value("Student", {"user": user})
		if not student:
			continue
		offering = frappe.db.get_value("Program Enrollment", {"student": student, "docstatus": 1}, "educore_programme_offering")
		if pay_balance:
			_pay_balance(student)
		if pay_deposit:
			_pay_deposit(student, offering)
		if register and not frappe.db.exists("Program Enrollment", {"student": student, "academic_year": PERIOD["academic_year"], "docstatus": ("<", 2)}):
			frappe.set_user(user)
			try:
				state = registration.status()
				year = state["year_of_study"]
				# the year's courses still open to the student (not passed already, prerequisites passed), and the
				# courses failed earlier, which must be repeated
				courses = [
					c["course"]
					for c in state["courses"]
					if (c["year"] == year and c.get("state") not in ("passed", "blocked")) or c.get("state") == "repeat"
				]
				registration.save(courses)
				registration.submit()
			finally:
				frappe.set_user("Administrator")
	return flt(len(STUDENTS))
