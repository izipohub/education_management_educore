"""Documents a student or applicant takes away as PDF: the offer letter and the proof of registration.

Each is open to the person it is about (the applicant's login, the student's login) and to staff who may read
the record (campus and faculty User Permissions apply). The letterhead is the university's name in its brand
colour (EduCore Branding); both carry the record's number so the university can confirm them.
"""

import frappe
from frappe import _
from frappe.utils import formatdate, fmt_money, nowdate
from frappe.utils.pdf import get_pdf

from educore.registration import rules as registration_rules

ADMISSIONS_ROLES = ("Admissions Officer", "Registrar", "Registry Officer", "System Manager")

STYLE = """
<style>
  body { font-family: "Helvetica", "Arial", sans-serif; font-size: 11pt; color: #1f2430; }
  .head { border-bottom: 3px solid %(colour)s; padding-bottom: 10px; margin-bottom: 24px; }
  .head .name { font-family: Georgia, serif; font-size: 20pt; color: %(colour)s; }
  .head .office { color: #6b6f7a; font-size: 10pt; margin-top: 2px; }
  h1 { font-family: Georgia, serif; font-size: 15pt; margin: 0 0 14px; }
  table.facts { border-collapse: collapse; margin: 0 0 18px; }
  table.facts td { padding: 3px 18px 3px 0; vertical-align: top; }
  table.facts td.k { color: #6b6f7a; width: 150px; }
  table.list { width: 100%%; border-collapse: collapse; margin: 6px 0 18px; }
  table.list th { text-align: left; font-size: 9pt; color: #6b6f7a; border-bottom: 1px solid #c9c4b8; padding: 5px 6px; }
  table.list td { border-bottom: 1px solid #e6e2d8; padding: 5px 6px; }
  table.list .num { text-align: right; }
  .foot { margin-top: 28px; color: #6b6f7a; font-size: 9pt; border-top: 1px solid #e6e2d8; padding-top: 8px; }
  p { line-height: 1.45; margin: 0 0 10px; }
</style>
"""


def _brand() -> dict:
	try:
		from educore_theme.branding import get_branding

		brand = get_branding()
	except Exception:
		brand = {}
	from educore.admissions.notify import university

	return {"name": university(), "colour": brand.get("primary_color") or "#1E3A8A"}


def _page(office: str, body: str) -> str:
	brand = _brand()
	return (
		"<html><head><meta charset='utf-8'>" + STYLE % {"colour": frappe.utils.escape_html(brand["colour"])} + "</head><body>"
		f"<div class='head'><div class='name'>{frappe.utils.escape_html(brand['name'])}</div><div class='office'>{office}</div></div>"
		f"{body}</body></html>"
	)


def _send(filename: str, html: str):
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = get_pdf(html)
	frappe.local.response.type = "pdf"


def _e(value) -> str:
	return frappe.utils.escape_html(str(value)) if value not in (None, "") else ""


# --- offer letter ----------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def offer_letter(name: str):
	"""The offer of a place, for the applicant or admissions staff"""
	from educore.finance.student_fees import fee_structure_for

	doc = frappe.get_doc("Student Applicant", name)
	own = doc.get("educore_applicant_user") == frappe.session.user
	if not own:
		if not set(frappe.get_roles()) & set(ADMISSIONS_ROLES):
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		doc.check_permission("read")
	if doc.application_status not in ("Approved", "Admitted"):
		frappe.throw(_("{0} has no offer").format(name))

	offering = frappe.db.get_value("Programme Offering", doc.educore_programme_offering, ["program", "campus", "mode_of_study"], as_dict=True)
	structure = fee_structure_for(doc.educore_programme_offering, doc.academic_year)
	fees = frappe.db.get_value("Fee Structure", structure, "total_amount") if structure else None
	start = frappe.db.get_value("Academic Term", doc.academic_term, "term_start_date") if doc.academic_term else None
	first = doc.first_name or doc.title

	paragraphs = [
		f"We are pleased to offer you a place in the <b>{_e(offering.program)}</b> at {_e(offering.campus)}, "
		f"{_e((offering.mode_of_study or '').lower())}, for the {_e(doc.academic_year)} academic year"
		+ (f", starting on {formatdate(start, 'dd-MM-yyyy')}" if start else "")
		+ ".",
	]
	if doc.get("educore_offer_conditions"):
		paragraphs.append(f"This offer is subject to the following conditions: {_e(doc.educore_offer_conditions)}")
	if fees:
		paragraphs.append(f"First-year fees: N$ {fmt_money(fees, precision=2)}.")
	if doc.get("educore_offer_deadline") and doc.get("educore_applicant_user"):
		paragraphs.append(f"Please accept or decline this offer in the applicant portal by {formatdate(doc.educore_offer_deadline, 'dd-MM-yyyy')}.")
	elif not doc.get("educore_applicant_user"):
		paragraphs.append("Please confirm your acceptance at the campus registry office.")

	body = (
		f"<p>{formatdate(doc.get('educore_decided_on') or nowdate(), 'dd-MM-yyyy')}</p>"
		f"<p>{_e(' '.join(x for x in (doc.get('educore_title'), doc.title) if x))}<br>Application {_e(doc.name)}</p>"
		f"<h1>Offer of a place: {_e(offering.program)}</h1>"
		f"<p>Dear {_e(first)},</p>"
		+ "".join(f"<p>{p}</p>" for p in paragraphs)
		+ f"<p>Yours sincerely,<br>Admissions Office<br>{_e(_brand()['name'])}</p>"
		f"<div class='foot'>Application {_e(doc.name)} · issued {formatdate(nowdate(), 'dd-MM-yyyy')}</div>"
	)
	_send(f"Offer letter {doc.name}.pdf", _page("Admissions Office", body))


# --- proof of registration ----------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def proof_of_registration(enrollment: str):
	"""Confirmation that a student is registered for a year: for the student, their sponsor, or the registry"""
	pe = frappe.get_doc("Program Enrollment", enrollment)
	student = frappe.get_doc("Student", pe.student)
	if student.user != frappe.session.user:
		from educore.api.v1.student_records import RECORD_ROLES

		if not set(frappe.get_roles()) & set(RECORD_ROLES):
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		student.check_permission("read")
	if pe.docstatus != 1:
		frappe.throw(_("{0} is not registered for {1} yet").format(student.student_name, pe.academic_year))

	courses = [(c.course, c.course_name, registration_rules.credits(c.course)) for c in pe.courses]
	rows = "".join(
		f"<tr><td>{_e(frappe.db.get_value('Course', code, 'educore_course_code') or code)}</td><td>{_e(name)}</td><td class='num'>{credits}</td></tr>"
		for code, name, credits in courses
	)
	identity = student.get("educore_national_id") or student.get("educore_passport_number")
	facts = [
		("Student", f"{student.student_name}"),
		("Student number", student.name),
		("Identity number" if student.get("educore_national_id") else "Passport number", identity),
		("Programme", pe.program),
		("Offering", pe.get("educore_programme_offering")),
		("Campus", pe.get("campus")),
		("Mode of study", pe.get("educore_mode_of_study")),
		("Academic year", pe.academic_year),
		("Year of study", pe.get("educore_year_of_study")),
		("Registered from", formatdate(pe.enrollment_date, "dd-MM-yyyy") if pe.enrollment_date else None),
	]
	body = (
		"<h1>Proof of registration</h1>"
		f"<p>This confirms that the student below is registered at {_e(_brand()['name'])} for the {_e(pe.academic_year)} academic year.</p>"
		"<table class='facts'>"
		+ "".join(f"<tr><td class='k'>{k}</td><td>{_e(v)}</td></tr>" for k, v in facts if v)
		+ "</table>"
		+ (
			"<table class='list'><thead><tr><th>Code</th><th>Course</th><th class='num'>Credits</th></tr></thead>"
			f"<tbody>{rows}</tbody><tfoot><tr><td></td><td><b>Total</b></td><td class='num'><b>{sum(c[2] for c in courses)}</b></td></tr></tfoot></table>"
			if courses
			else ""
		)
		+ "<p>Office of the Registrar</p>"
		f"<div class='foot'>Registration {_e(pe.name)} · issued {formatdate(nowdate(), 'dd-MM-yyyy')}. "
		"The registry confirms this document on request, quoting the registration number.</div>"
	)
	_send(f"Proof of registration {student.name} {pe.academic_year}.pdf", _page("Office of the Registrar", body))
