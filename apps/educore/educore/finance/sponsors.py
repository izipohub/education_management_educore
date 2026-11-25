"""Sponsors: bursaries, scholarships, loan funds (NSFAF), training levies (NTA) and employers that pay students' fees.

A Sponsor is an ERPNext Customer in the "Sponsor" customer group, with its own receivable account (Sponsor
Debtors), so what sponsors owe is kept apart from what students owe. Its number (SPN-00001) is the reference on its
EFT payments.

A Sponsorship is one sponsor paying one student's fees for one academic year: full fees, a percent of them, or an
amount. Once the student's invoice for that year exists (it is made when the registration is approved,
educore.finance.student_fees), apply() moves the sponsor's share off it:

- a credit note to the student against their invoice, "Sponsored by <sponsor>", line by line in proportion, so the
  student owes only the rest (and the registration deposit is worked out on that rest);
- an invoice to the sponsor for the same lines, naming the student, posted to the same campus cost centre.

Income is booked once (the student's invoice) and moved, never doubled. A late registration fee is the student's own
and is never sponsored. Withdrawing a sponsorship cancels both, as long as the sponsor has not paid towards it.
"""

import re

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, nowdate

SPONSOR_DEBTORS = "Sponsor Debtors"
CUSTOMER_GROUP = "Sponsor"
FULL, PERCENT, AMOUNT = "Full fees", "Percent of fees", "Amount"
RECORDED, INVOICED, WITHDRAWN = "Recorded", "Invoiced", "Withdrawn"
#: fee lines a sponsor never pays
NOT_SPONSORED = ("Late Registration Fee",)
#: a sponsor number in free text, e.g. "SPN-00001"
SPONSOR_NUMBER = re.compile(r"\bSPN-\d{5,}\b", re.IGNORECASE)


# --- setup ---------------------------------------------------------------------------------------------


def ensure_sponsor_setup(company: str):
	"""The Sponsor Debtors account and the Sponsor customer group that uses it (from ensure_fee_setup)"""
	from educore.finance.student_fees import _account

	debtors = _account(company, SPONSOR_DEBTORS, "Accounts Receivable", "Receivable")
	if not frappe.db.exists("Customer Group", CUSTOMER_GROUP):
		frappe.get_doc(
			{"doctype": "Customer Group", "customer_group_name": CUSTOMER_GROUP, "parent_customer_group": "All Customer Groups"}
		).insert(ignore_permissions=True)
	group = frappe.get_doc("Customer Group", CUSTOMER_GROUP)
	if not any(row.company == company for row in group.accounts):
		group.append("accounts", {"company": company, "account": debtors})
		group.save(ignore_permissions=True)


def _company() -> str:
	return frappe.db.get_value("Campus", {"is_main_campus": 1}, "company") or frappe.defaults.get_global_default("company")


def validate_sponsor(doc, method=None):
	doc.sponsor_name = (doc.sponsor_name or "").strip()
	if doc.payment_days is not None and doc.payment_days < 0:
		frappe.throw(_("Days to pay cannot be negative"))


def ensure_customer(doc, method=None):
	"""The sponsor's ERPNext Customer, made with the sponsor"""
	if doc.customer and frappe.db.exists("Customer", doc.customer):
		return doc.customer
	ensure_sponsor_setup(_company())
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": doc.sponsor_name,
			"customer_group": CUSTOMER_GROUP,
			"customer_type": "Company",
			"territory": frappe.db.get_single_value("Selling Settings", "territory") or "All Territories",
		}
	).insert(ignore_permissions=True)
	doc.db_set("customer", customer.name)
	return customer.name


# --- sponsorships --------------------------------------------------------------------------------------


def validate_sponsorship(doc, method=None):
	if frappe.db.get_value("Sponsor", doc.sponsor, "disabled"):
		frappe.throw(_("{0} is no longer sponsoring").format(doc.sponsor_name or doc.sponsor))
	if doc.cover_type == PERCENT and not 0 < flt(doc.cover_value) <= 100:
		frappe.throw(_("The percent must be more than 0 and at most 100"))
	if doc.cover_type == AMOUNT and flt(doc.cover_value) <= 0:
		frappe.throw(_("Enter the amount the sponsor pays"))
	if doc.cover_type == FULL:
		doc.cover_value = 0
	if doc.status != WITHDRAWN and frappe.db.exists(
		"Sponsorship",
		{"sponsor": doc.sponsor, "student": doc.student, "academic_year": doc.academic_year, "status": ("!=", WITHDRAWN), "name": ("!=", doc.name or "")},
	):
		frappe.throw(_("{0} already sponsors {1} in {2}").format(doc.sponsor_name or doc.sponsor, doc.student_name or doc.student, doc.academic_year))
	if not doc.recorded_by:
		doc.recorded_by = frappe.session.user


def year_invoice(student: str, academic_year: str) -> str | None:
	"""The student's invoice for the year's fees (made when the year's registration was approved)"""
	enrolments = frappe.get_all(
		"Program Enrollment", filters={"student": student, "academic_year": academic_year, "docstatus": 1}, pluck="name"
	)
	if not enrolments:
		return None
	return frappe.db.get_value(
		"Sales Invoice", {"educore_program_enrollment": ("in", enrolments), "docstatus": 1, "is_return": 0}, "name"
	)


def _share(cover_type: str, cover_value: float, base: float, left: float) -> float:
	"""What the sponsor pays of the year's sponsorable fees (base), with what other sponsors leave (left)"""
	if cover_type == FULL:
		wanted = base
	elif cover_type == PERCENT:
		wanted = base * flt(cover_value) / 100
	else:
		wanted = flt(cover_value)
	return flt(max(0.0, min(wanted, left)), 2)


def sponsored_estimate(student: str, academic_year: str, year_fees: float) -> float:
	"""The sponsors' share of a year's fees before it is invoiced (the registration deposit is on the rest)"""
	left = flt(year_fees)
	total = 0.0
	for s in frappe.get_all(
		"Sponsorship",
		filters={"student": student, "academic_year": academic_year, "status": ("!=", WITHDRAWN)},
		fields=["cover_type", "cover_value", "amount", "status"],
		order_by="creation asc",
	):
		share = flt(s.amount) if s.status == INVOICED else _share(s.cover_type, s.cover_value, year_fees, left)
		total += share
		left -= share
	return flt(min(total, year_fees), 2)


def apply_for(student: str, academic_year: str) -> list[str]:
	"""Every recorded sponsorship of the student's year, once its invoice exists (oldest first)"""
	done = []
	for name in frappe.get_all(
		"Sponsorship", filters={"student": student, "academic_year": academic_year, "status": RECORDED}, pluck="name", order_by="creation asc"
	):
		if apply(name):
			done.append(name)
	return done


def apply(sponsorship: str) -> str | None:
	"""Move the sponsor's share off the student's invoice onto an invoice to the sponsor; the sponsor invoice"""
	from educore.finance.student_fees import _as_system

	with _as_system():
		return _apply(sponsorship)


def _sponsorable(invoice) -> list:
	return [item for item in invoice.items if item.item_code not in NOT_SPONSORED and flt(item.amount) > 0]


def _apply(name: str) -> str | None:
	from educore.finance.student_fees import ensure_fiscal_year

	doc = frappe.get_doc("Sponsorship", name)
	if doc.status != RECORDED:
		return doc.sponsor_invoice
	invoice_name = year_invoice(doc.student, doc.academic_year)
	if not invoice_name:
		return None  # applied when the year's registration is approved and invoiced
	invoice = frappe.get_doc("Sales Invoice", invoice_name)
	lines = _sponsorable(invoice)
	base = flt(sum(flt(i.amount) for i in lines), 2)
	taken = flt(
		sum(
			flt(a)
			for a in frappe.get_all(
				"Sponsorship",
				filters={"student": doc.student, "academic_year": doc.academic_year, "status": INVOICED},
				pluck="amount",
			)
		),
		2,
	)
	amount = _share(doc.cover_type, doc.cover_value, base, base - taken)
	if amount <= 0:
		frappe.throw(_("{0}'s fees for {1} are sponsored in full already").format(doc.student_name, doc.academic_year))

	# the share of each fee line, in proportion; the last line takes the rounding
	shares, running = [], 0.0
	for index, item in enumerate(lines):
		part = flt(amount - running, 2) if index == len(lines) - 1 else flt(flt(item.amount) * amount / base, 2)
		running += part
		shares.append((item, part))

	sponsor = frappe.get_doc("Sponsor", doc.sponsor)
	customer = ensure_customer(sponsor)
	posting_date = max(getdate(invoice.posting_date), getdate(nowdate()))
	ensure_fiscal_year(posting_date, invoice.company)
	what = _("Sponsored by {0}, {1}").format(sponsor.sponsor_name, doc.academic_year)

	credit = frappe.new_doc("Sales Invoice")
	credit.update(
		{
			"customer": invoice.customer,
			"student": doc.student,
			"company": invoice.company,
			"is_return": 1,
			"return_against": invoice.name,
			# set against the student's invoice: it is what they owe that goes down
			"update_outstanding_for_self": 0,
			"set_posting_time": 1,
			"posting_date": posting_date,
			"debit_to": invoice.debit_to,
			"cost_center": invoice.cost_center,
			"campus": invoice.get("campus"),
			"educore_sponsorship": doc.name,
			"remarks": what,
		}
	)
	for item, part in shares:
		credit.append(
			"items",
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": _("{0}, {1}").format(item.item_name, what),
				"qty": -1,
				"rate": part,
				"cost_center": item.cost_center,
				"income_account": item.income_account,
			},
		)
	credit.insert(ignore_permissions=True)
	credit.submit()

	student_label = f"{doc.student_name} ({doc.student})"
	bill = frappe.new_doc("Sales Invoice")
	bill.update(
		{
			"customer": customer,
			"company": invoice.company,
			"set_posting_time": 1,
			"posting_date": posting_date,
			"due_date": add_days(posting_date, sponsor.payment_days or 0),
			"debit_to": f"{SPONSOR_DEBTORS} - {frappe.get_cached_value('Company', invoice.company, 'abbr')}",
			"cost_center": invoice.cost_center,
			"campus": invoice.get("campus"),
			"educore_sponsorship": doc.name,
			"educore_sponsored_student": doc.student,
			"po_no": (doc.sponsor_reference or "")[:140] or None,
			"remarks": _("Fees {0} of {1}{2}").format(
				doc.academic_year, student_label, f", {doc.sponsor_reference}" if doc.sponsor_reference else ""
			),
		}
	)
	for item, part in shares:
		bill.append(
			"items",
			{
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": _("{0} {1}, {2}").format(item.item_name, doc.academic_year, student_label),
				"qty": 1,
				"rate": part,
				"cost_center": item.cost_center,
				"income_account": item.income_account,
			},
		)
	bill.insert(ignore_permissions=True)
	bill.submit()

	doc.db_set({"status": INVOICED, "amount": amount, "sponsor_invoice": bill.name, "credit_note": credit.name})
	return bill.name


def withdraw(name: str):
	"""The sponsor does not pay after all: its invoice and the student's credit note are cancelled"""
	from educore.finance.student_fees import _as_system

	doc = frappe.get_doc("Sponsorship", name)
	if doc.status == WITHDRAWN:
		return
	if doc.status == INVOICED:
		total, outstanding = frappe.db.get_value("Sales Invoice", doc.sponsor_invoice, ["grand_total", "outstanding_amount"])
		if flt(outstanding) < flt(total):
			frappe.throw(_("{0} has paid towards this sponsorship: reverse the payment first").format(doc.sponsor_name))
		with _as_system():
			for invoice in (doc.sponsor_invoice, doc.credit_note):
				if invoice and frappe.db.get_value("Sales Invoice", invoice, "docstatus") == 1:
					frappe.get_doc("Sales Invoice", invoice).cancel()
	doc.db_set("status", WITHDRAWN)


# --- payments ------------------------------------------------------------------------------------------


def sponsor_numbers_in(*texts) -> list[str]:
	found = []
	for text in texts:
		for match in SPONSOR_NUMBER.findall(text or ""):
			number = match.upper()
			if number not in found:
				found.append(number)
	return found


def record_payment(sponsor: str, bank_transaction: str) -> str | None:
	from educore.finance.student_fees import _as_system
	from educore.finance.student_payments import book_receipt

	sponsor_doc = frappe.get_doc("Sponsor", sponsor)
	with _as_system():
		customer = ensure_customer(sponsor_doc)
		return book_receipt(customer, bank_transaction, _("Sponsor payment, {0}").format(sponsor_doc.sponsor_name))


def match_bank_transactions() -> int:
	"""Scheduled hourly: a deposit naming one sponsor number is that sponsor's payment"""
	from educore.finance.student_payments import unallocated_deposits

	matched = 0
	for deposit in unallocated_deposits():
		numbers = [n for n in sponsor_numbers_in(deposit.description, deposit.reference_number) if frappe.db.exists("Sponsor", n)]
		if len(numbers) == 1 and record_payment(numbers[0], deposit.name):
			matched += 1
	return matched
