"""Sponsors, for Finance and Financial Aid: the bursaries, loan funds and employers that pay students' fees, the
students each pays for in a year, what it was invoiced, what it paid and what it owes (educore.finance.sponsors).

Recording a sponsorship moves the sponsor's share off the student's invoice for the year as soon as that invoice
exists (registration approved); before that, it is applied when the registration is approved and invoiced.
"""

import frappe
from frappe import _
from frappe.utils import flt

from educore.finance import sponsors as sponsorship

#: who records sponsors and sponsorships
SPONSOR_ROLES = ("Bursar", "Finance Officer", "Student Fees Officer", "Financial Aid Officer", "System Manager")
SPONSOR_FIELDS = ("sponsor_name", "sponsor_type", "contact_person", "email", "phone", "address", "payment_days", "disabled")
SPONSOR_TYPES = ("Government fund", "Bursary", "Scholarship", "Employer", "Other")
COVER_TYPES = (sponsorship.FULL, sponsorship.PERCENT, sponsorship.AMOUNT)


def _require():
	if not set(frappe.get_roles()) & set(SPONSOR_ROLES):
		frappe.throw(_("Sponsors are Finance's"), frappe.PermissionError)


def _years() -> list[str]:
	years = set(frappe.get_all("Sponsorship", pluck="academic_year", distinct=True))
	years |= set(frappe.get_all("Program Enrollment", filters={"docstatus": 1}, pluck="academic_year", distinct=True))
	years |= set(frappe.get_all("Registration Period", pluck="academic_year"))
	return sorted((y for y in years if y), reverse=True)


def _current_year(years: list[str]) -> str | None:
	"""The year to show first: the latest with approved registrations, else the latest"""
	enrolled = set(frappe.get_all("Program Enrollment", filters={"docstatus": 1}, pluck="academic_year", distinct=True))
	return next((y for y in years if y in enrolled), years[0] if years else None)


def _owing(customer: str | None) -> float:
	if not customer:
		return 0.0
	return flt(
		frappe.db.sql(
			"select sum(outstanding_amount) from `tabSales Invoice` where customer = %s and docstatus = 1", customer
		)[0][0],
		2,
	)


@frappe.whitelist(methods=["GET"])
def sponsors(academic_year: str | None = None) -> dict:
	"""Every sponsor: students and amount for the year, what it owes"""
	_require()
	years = _years()
	academic_year = academic_year or _current_year(years)
	counts = {
		r.sponsor: r
		for r in frappe.db.sql(
			"""select sponsor, count(name) as students, sum(amount) as invoiced from `tabSponsorship`
			where academic_year = %s and status != %s group by sponsor""",
			(academic_year, sponsorship.WITHDRAWN),
			as_dict=True,
		)
	}
	rows = []
	for s in frappe.get_all("Sponsor", fields=["name", "sponsor_name", "sponsor_type", "customer", "disabled"], order_by="sponsor_name asc"):
		year = counts.get(s.name) or {}
		rows.append(
			{
				"name": s.name,
				"sponsor_name": s.sponsor_name,
				"sponsor_type": s.sponsor_type,
				"disabled": s.disabled,
				"students": year.get("students") or 0,
				"invoiced": flt(year.get("invoiced")),
				"owing": _owing(s.customer),
			}
		)
	return {"academic_year": academic_year, "academic_years": years, "rows": rows, "types": list(SPONSOR_TYPES)}


def _cover_label(row) -> str:
	if row.cover_type == sponsorship.PERCENT:
		return _("{0}% of fees").format(frappe.utils.fmt_money(row.cover_value, precision=0).replace(",", " "))
	if row.cover_type == sponsorship.AMOUNT:
		return _("N$ {0}").format(frappe.utils.fmt_money(row.cover_value, precision=2))
	return _("Full fees")


@frappe.whitelist(methods=["GET"])
def sponsor(name: str, academic_year: str | None = None) -> dict:
	"""One sponsor: its details, the students it pays for in the year, its invoices and payments"""
	_require()
	doc = frappe.get_doc("Sponsor", name)
	years = _years()
	academic_year = academic_year or _current_year(years)
	students = []
	for s in frappe.get_all(
		"Sponsorship",
		filters={"sponsor": name, "academic_year": academic_year},
		fields=["name", "student", "student_name", "cover_type", "cover_value", "amount", "status", "sponsor_reference", "sponsor_invoice"],
		order_by="student_name asc",
	):
		enrolment = frappe.db.get_value(
			"Program Enrollment",
			{"student": s.student, "academic_year": academic_year, "docstatus": 1},
			["program", "campus"],
			as_dict=True,
		) or frappe._dict()
		owing = flt(frappe.db.get_value("Sales Invoice", s.sponsor_invoice, "outstanding_amount")) if s.sponsor_invoice else 0.0
		students.append(
			{
				**s,
				"cover": _cover_label(s),
				"program": enrolment.program,
				"campus": enrolment.campus,
				"owing": owing,
				# recorded: waiting for the student's registration for the year to be approved and invoiced
				"can_withdraw": s.status != sponsorship.WITHDRAWN and (s.status == sponsorship.RECORDED or owing >= flt(s.amount)),
			}
		)
	payments = (
		frappe.get_all(
			"Payment Entry",
			filters={"party_type": "Customer", "party": doc.customer, "docstatus": 1, "payment_type": "Receive"},
			fields=["name", "posting_date", "paid_amount", "unallocated_amount", "reference_no"],
			order_by="posting_date desc",
			limit=50,
		)
		if doc.customer
		else []
	)
	students.sort(key=lambda s: s["status"] == sponsorship.WITHDRAWN)  # withdrawn last
	active = [s for s in students if s["status"] != sponsorship.WITHDRAWN]
	return {
		"named": _named(name, academic_year, {s["student"] for s in active}),
		**{f: doc.get(f) for f in ("name", *SPONSOR_FIELDS, "customer")},
		"academic_year": academic_year,
		"academic_years": years,
		"students": students,
		"payments": [{**p, "posting_date": str(p.posting_date)} for p in payments],
		"totals": {
			"students": len(active),
			"invoiced": flt(sum(flt(s["amount"]) for s in active), 2),
			"owing_year": flt(sum(s["owing"] for s in active), 2),
			"owing": _owing(doc.customer),
			"waiting": len([s for s in active if s["status"] == sponsorship.RECORDED]),
		},
		"types": list(SPONSOR_TYPES),
		"cover_types": list(COVER_TYPES),
	}


@frappe.whitelist(methods=["POST"])
def save_sponsor(data: dict | str, name: str | None = None) -> dict:
	"""A new sponsor, or changes to one"""
	_require()
	data = frappe.parse_json(data) or {}
	doc = frappe.get_doc("Sponsor", name) if name else frappe.new_doc("Sponsor")
	for field in SPONSOR_FIELDS:
		if field in data:
			doc.set(field, data[field])
	if doc.sponsor_type not in SPONSOR_TYPES:
		frappe.throw(_("Choose the kind of sponsor"))
	if not (doc.sponsor_name or "").strip():
		frappe.throw(_("Enter the sponsor's name"))
	doc.flags.ignore_permissions = True
	doc.save()
	return sponsor(doc.name)


@frappe.whitelist(methods=["POST"])
def add_student(
	sponsor_id: str,
	student: str,
	academic_year: str,
	cover_type: str,
	cover_value: float | str | None = None,
	sponsor_reference: str | None = None,
) -> dict:
	"""The sponsor pays this student's fees for the year; their share moves to the sponsor once invoiced"""
	_require()
	if cover_type not in COVER_TYPES:
		frappe.throw(_("Choose what the sponsor covers"))
	if not frappe.db.exists("Student", student):
		frappe.throw(_("Choose a student"))
	doc = frappe.get_doc(
		{
			"doctype": "Sponsorship",
			"sponsor": sponsor_id,
			"student": student,
			"academic_year": academic_year,
			"cover_type": cover_type,
			"cover_value": flt(cover_value),
			"sponsor_reference": (sponsor_reference or "").strip() or None,
		}
	)
	doc.insert(ignore_permissions=True)
	sponsorship.apply(doc.name)
	return sponsor(sponsor_id, academic_year)


@frappe.whitelist(methods=["POST"])
def withdraw(name: str) -> dict:
	"""The sponsor does not pay for this student after all"""
	_require()
	sponsorship.withdraw(name)
	sponsor_id, year = frappe.db.get_value("Sponsorship", name, ["sponsor", "academic_year"])
	return sponsor(sponsor_id, year)


@frappe.whitelist(methods=["GET"])
def find_students(search: str) -> list[dict]:
	"""Students by name, number or ID number"""
	_require()
	like = f"%{(search or '').strip()}%"
	return frappe.get_all(
		"Student",
		or_filters=[["student_name", "like", like], ["name", "like", like], ["educore_national_id", "like", like]],
		fields=["name", "student_name", "campus"],
		order_by="student_name asc",
		limit=20,
	)


def _named(sponsor_id: str, academic_year: str | None, recorded: set[str]) -> list[dict]:
	"""Students registered for the year whose funding route is this sponsor's (said on their application), with no
	sponsorship recorded yet: Financial Aid confirms the award and adds them"""
	routes = frappe.get_all("Funding Route", filters={"sponsor": sponsor_id}, pluck="name")
	if not routes or not academic_year:
		return []
	rows = frappe.db.sql(
		"""select s.name as student, s.student_name, pe.program, pe.campus
		from tabStudent s join `tabProgram Enrollment` pe on pe.student = s.name and pe.docstatus = 1 and pe.academic_year = %s
		where s.educore_fee_payer in %s and s.enabled = 1 order by s.student_name""",
		(academic_year, routes),
		as_dict=True,
	)
	return [r for r in rows if r.student not in recorded]
