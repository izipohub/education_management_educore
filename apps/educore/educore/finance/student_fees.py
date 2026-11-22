"""Student fees: per-offering fee structures, invoices on enrolment, campus cost centers (AGENT.md 5.1.2, 5.5).

ERPNext stays the system of record for the money: invoices are Sales Invoices to the student's Customer
(created by Education for every Student), payments are Payment Entries into the university's central bank
account. EduCore adds:

- ensure_fee_setup(): the accounts, item group and fee categories a university needs (run by the university
  setup; safe to re-run).
- Fee Structure per programme offering and year: a part-time or distance offering, or another campus, has
  its own fees and its own campus cost center.
- invoice_enrollment(): submitting a Program Enrollment invoices the offering's fee structure, posted to the
  campus cost center. (Education's own Fee Schedule invoicing clears the cost center on every line, which
  would put all campus income on Central Administration.)
- Payments take the campus and cost center of the invoices they settle, so collections are reported per
  campus although the money goes into one central account.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate

#: category, income account, description
FEE_CATEGORIES = (
	("Tuition Fee", "Tuition Fees", "Tuition for the academic year"),
	("Registration Fee", "Other Student Fees", "Annual registration"),
	("Examination Fee", "Other Student Fees", "Examinations for the academic year"),
	("Technology Levy", "Other Student Fees", "Computer labs, network and learning platforms"),
)
STUDENT_DEBTORS = "Student Debtors"
CENTRAL_BANK = "Central Bank Account"
#: days after the enrolment date that an enrolment invoice is due
PAYMENT_DAYS = 30


def _abbr(company):
	return frappe.get_cached_value("Company", company, "abbr")


def _account(company, name, parent, account_type):
	full = f"{name} - {_abbr(company)}"
	if not frappe.db.exists("Account", full):
		frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": name,
				"parent_account": f"{parent} - {_abbr(company)}",
				"company": company,
				"account_type": account_type,
				"is_group": 0,
			}
		).insert(ignore_permissions=True)
	return full


def ensure_fee_setup(company: str):
	"""Accounts, the Student customer group's receivable account, and the fee categories"""
	debtors = _account(company, STUDENT_DEBTORS, "Accounts Receivable", "Receivable")
	income = {
		"Tuition Fees": _account(company, "Tuition Fees", "Direct Income", "Income Account"),
		"Other Student Fees": _account(company, "Other Student Fees", "Direct Income", "Income Account"),
	}
	_account(company, CENTRAL_BANK, "Bank Accounts", "Bank")

	group = frappe.get_doc("Customer Group", "Student")
	if not any(row.company == company for row in group.accounts):
		group.append("accounts", {"company": company, "account": debtors})
		group.save(ignore_permissions=True)

	if not frappe.db.exists("Item Group", "Fee Component"):
		frappe.get_doc(
			{"doctype": "Item Group", "item_group_name": "Fee Component", "parent_item_group": "All Item Groups"}
		).insert(ignore_permissions=True)

	for category, income_account, description in FEE_CATEGORIES:
		if frappe.db.exists("Fee Category", category):
			continue
		frappe.get_doc(
			{
				"doctype": "Fee Category",
				"category_name": category,
				"description": description,
				"item_defaults": [{"company": company, "income_account": income[income_account]}],
			}
		).insert(ignore_permissions=True)


# --- Fee Structure -------------------------------------------------------------------------------------


def validate_fee_structure(doc, method=None):
	offering = doc.get("educore_programme_offering")
	if not offering:
		frappe.throw(_("Choose the programme offering these fees are for"))
	offering = frappe.get_cached_doc("Programme Offering", offering)
	doc.program = offering.program
	doc.campus = offering.campus
	doc.cost_center = frappe.db.get_value("Campus", offering.campus, "cost_center")
	if not doc.company:
		doc.company = frappe.db.get_value("Campus", offering.campus, "company")
	# student receivables are kept apart from other debtors; ERPNext pre-fills the company's general
	# receivable account, so that one is replaced too (any other account chosen on purpose is kept)
	company_default = frappe.get_cached_value("Company", doc.company, "default_receivable_account")
	if not doc.receivable_account or doc.receivable_account == company_default:
		doc.receivable_account = f"{STUDENT_DEBTORS} - {_abbr(doc.company)}"
	if doc.academic_term:
		frappe.throw(_("EduCore bills a year's fees on enrolment: leave Academic Term empty"))


def before_submit_fee_structure(doc, method=None):
	existing = frappe.db.exists(
		"Fee Structure",
		{
			"educore_programme_offering": doc.educore_programme_offering,
			"academic_year": doc.academic_year,
			"docstatus": 1,
			"name": ("!=", doc.name),
		},
	)
	if existing:
		frappe.throw(
			_("{0} already has fees for {1}: {2}. Cancel it first.").format(
				doc.educore_programme_offering, doc.academic_year, existing
			)
		)


def fee_structure_for(offering: str, academic_year: str) -> str | None:
	return frappe.db.get_value(
		"Fee Structure",
		{"educore_programme_offering": offering, "academic_year": academic_year, "docstatus": 1},
	)


# --- Fiscal year ---------------------------------------------------------------------------------------


def ensure_fiscal_year(date, company: str):
	"""The fiscal year a posting date falls in, creating it when it is the year after the latest one.

	Universities enrol for next year before ERPNext's scheduler creates its fiscal year (it does so only
	days before the current one ends); without this, submitting an enrolment would fail on its invoice.
	Follows ERPNext's own auto_create_fiscal_year: the next year starts the day after the latest ends.
	"""
	from erpnext.accounts.utils import get_fiscal_years
	from frappe.utils import add_years, cstr

	date = getdate(date)
	if get_fiscal_years(date, company=company, boolean=True):
		return
	latest = frappe.get_all(
		"Fiscal Year", filters={"is_short_year": 0}, fields=["name", "year_end_date"], order_by="year_end_date desc", limit=1
	)
	if not latest:
		return
	start = add_days(latest[0].year_end_date, 1)
	end = add_days(add_years(start, 1), -1)
	if not start <= date <= end:
		return  # only ever the next year; anything further is a setup decision for finance
	year = cstr(start.year) if start.year == end.year else f"{start.year}-{end.year}"
	previous = frappe.get_doc("Fiscal Year", latest[0].name)
	frappe.get_doc(
		{
			"doctype": "Fiscal Year",
			"year": year,
			"year_start_date": start,
			"year_end_date": end,
			"companies": [{"company": row.company} for row in previous.companies],
		}
	).insert(ignore_permissions=True)


# --- Invoicing -----------------------------------------------------------------------------------------


def invoice_enrollment(enrollment) -> str | None:
	"""The enrolment's Sales Invoice, from its offering's fee structure for the year (submitted)"""
	existing = frappe.db.get_value(
		"Sales Invoice", {"educore_program_enrollment": enrollment.name, "docstatus": ("<", 2)}
	)
	if existing:
		return existing
	structure_name = fee_structure_for(enrollment.educore_programme_offering, enrollment.academic_year)
	if not structure_name:
		frappe.msgprint(
			_("No fees for {0} in {1}: the enrolment is not invoiced. Invoice it once the fee structure is submitted.").format(
				enrollment.educore_programme_offering, enrollment.academic_year
			),
			alert=True,
		)
		return None

	from education.education.doctype.fee_schedule.fee_schedule import get_customer_from_student

	structure = frappe.get_doc("Fee Structure", structure_name)
	posting_date = getdate(enrollment.enrollment_date)
	ensure_fiscal_year(posting_date, structure.company)
	invoice = frappe.new_doc("Sales Invoice")
	invoice.update(
		{
			"customer": get_customer_from_student(enrollment.student),
			"student": enrollment.student,
			"company": structure.company,
			"set_posting_time": 1,
			"posting_date": posting_date,
			"due_date": add_days(posting_date, PAYMENT_DAYS),
			"debit_to": structure.receivable_account,
			"cost_center": structure.cost_center,
			"campus": enrollment.campus,
			"educore_program_enrollment": enrollment.name,
			"educore_fee_structure": structure.name,
			"remarks": _("Fees {0}, {1}").format(enrollment.academic_year, enrollment.educore_programme_offering),
		}
	)
	for component in structure.components:
		invoice.append(
			"items",
			{
				"item_code": component.item or component.fees_category,
				"item_name": component.fees_category,
				"description": component.description or component.fees_category,
				"qty": 1,
				"rate": component.total,
				"cost_center": structure.cost_center,
				"income_account": frappe.db.get_value(
					"Fee Category Default",
					{"parent": component.fees_category, "company": structure.company},
					"income_account",
				),
			},
		)
	invoice.insert(ignore_permissions=True)
	invoice.submit()
	return invoice.name


# --- Payments ------------------------------------------------------------------------------------------


def validate_payment(doc, method=None):
	"""A receipt from a student takes the campus and cost center of the first invoice it settles"""
	if doc.payment_type != "Receive" or doc.party_type != "Customer":
		return
	invoices = [r.reference_name for r in doc.references if r.reference_doctype == "Sales Invoice"]
	if not invoices:
		return
	campus, cost_center = frappe.db.get_value("Sales Invoice", invoices[0], ["campus", "cost_center"])
	if campus and not doc.get("campus"):
		doc.campus = campus
	if cost_center and not doc.cost_center:
		doc.cost_center = cost_center
