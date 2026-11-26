"""Documents as PDF: the offer letter, the proof of registration, the academic record, the award certificate and
the graduation ceremony list.

Each is open to the person it is about (the applicant's login, the student's login) and to staff who may read
the record (campus and faculty User Permissions apply). The letterhead is the university's name in its brand
colour (EduCore Branding); both carry the record's number so the university can confirm them.
"""

import frappe
from frappe import _
from frappe.utils import flt, formatdate, fmt_money, getdate, nowdate
from frappe.utils.pdf import get_pdf

from educore.registration import rules as registration_rules

ADMISSIONS_ROLES = ("Admissions Officer", "Registrar", "Registry Officer", "System Manager")

STYLE = """
<style>
  @page { margin: 0; }
  body { font-family: "DejaVu Sans", sans-serif; font-size: 9.5pt; color: #1f2430; margin: 0; }
  .brandname { font-size: 14pt; font-weight: bold; color: %(colour)s; vertical-align: middle; padding-left: 10px; }
  .sheet { padding: 0 0 0 0; }
  .letterhead { width: 100%%; border-collapse: collapse; }
  .letterhead td { vertical-align: middle; }
  .letterhead .logo img { height: 46px; }
  .letterhead .who { text-align: right; font-size: 8.5pt; color: #4b4f5a; line-height: 1.45; padding-right: 6px; }
  .letterhead .who .office { font-size: 10pt; font-weight: bold; color: %(colour)s; }
  .rule { height: 3px; background: %(colour)s; margin: 10px 0 2px; }
  .rule-thin { height: 1px; background: %(accent)s; margin: 0 0 22px; }
  h1 { font-size: 15pt; letter-spacing: 2px; color: %(colour)s; margin: 0; }
  .title-row { width: 100%%; border-collapse: collapse; margin-bottom: 16px; }
  .title-row td { vertical-align: bottom; }
  .ref { text-align: right; font-size: 8.5pt; color: #4b4f5a; line-height: 1.5; padding-right: 6px; }
  .ref b, .verify b { margin-left: 3px; }
  .ref b { color: #1f2430; }
  p { line-height: 1.5; margin: 0 0 10px; }
  .panels { width: 100%%; border-collapse: separate; border-spacing: 0; margin: 6px 0 16px; }
  .panels > tbody > tr > td { width: 50%%; vertical-align: top; }
  .panels > tbody > tr > td:first-child { padding-right: 8px; }
  .panels > tbody > tr > td:last-child { padding-left: 8px; }
  .box { border: 1px solid #c9c4b8; }
  .box .cap { background: #f4f2ec; padding: 5px 9px; font-size: 8pt; font-weight: bold; letter-spacing: 1px; color: #4b4f5a; text-transform: uppercase; border-bottom: 1px solid #c9c4b8; }
  .box table { width: 100%%; border-collapse: collapse; }
  .box td { padding: 4px 9px; font-size: 9pt; vertical-align: top; }
  .box td.k { color: #6b6f7a; width: 42%%; }
  table.list { width: 100%%; border-collapse: collapse; margin: 4px 0 6px; }
  table.list th { text-align: left; font-size: 8pt; letter-spacing: 1px; text-transform: uppercase; color: #4b4f5a; background: #f4f2ec; border: 1px solid #c9c4b8; padding: 5px 8px; }
  table.list td { border: 1px solid #e0dccf; padding: 5px 8px; font-size: 9pt; }
  table.list .num { text-align: right; }
  table.list tfoot td { font-weight: bold; background: #faf9f5; }
  table.list tr.sub td { color: #4b4f5a; font-size: 8.5pt; background: #faf9f5; }
  .section { font-size: 8pt; font-weight: bold; letter-spacing: 1px; text-transform: uppercase; color: #4b4f5a; margin: 14px 0 4px; }
  .sign { width: 100%%; border-collapse: collapse; margin-top: 34px; }
  .sign td { vertical-align: bottom; width: 50%%; }
  .sign .line { border-top: 1px solid #1f2430; width: 70%%; padding-top: 4px; font-size: 9pt; }
  .stamp { border: 1px dashed #a3a6ad; width: 130px; height: 80px; margin-left: auto; text-align: center; color: #a3a6ad; font-size: 8pt; line-height: 80px; }
  .verify { width: 100%%; border-collapse: collapse; margin-top: 26px; border-top: 1px solid #e0dccf; }
  .verify td { padding-top: 10px; font-size: 8pt; color: #6b6f7a; vertical-align: middle; line-height: 1.5; }
  .verify img { width: 74px; height: 74px; }
  .verify b { color: #1f2430; }
  .foot { margin-top: 28px; color: #6b6f7a; font-size: 8.5pt; border-top: 1px solid #e0dccf; padding-top: 8px; }
  h1.letter { font-size: 13pt; letter-spacing: 0; color: #1f2430; margin: 12px 0 12px; }
</style>
"""


def _brand() -> dict:
	try:
		from educore_theme.branding import get_branding

		brand = get_branding()
	except Exception:
		brand = {}
	from educore.admissions.notify import university

	return {
		"name": university(),
		"colour": brand.get("primary_color") or "#1E3A8A",
		"accent": brand.get("accent_color") or "#F2B33D",
		"logo": brand.get("logo"),
		"mark": brand.get("mark"),
	}


def _file_bytes(url: str | None) -> tuple[bytes, str] | None:
	"""A logo's bytes from where it is kept (an app's assets, or an uploaded file), with its type; the PDF tool
	may not fetch from the site, so the image is put into the page itself"""
	import os

	if not url:
		return None
	path = None
	if url.startswith("/assets/"):
		app, _, rest = url[len("/assets/") :].partition("/")
		try:
			path = os.path.join(frappe.get_app_path(app), "public", rest)
		except Exception:
			path = None
	elif url.startswith("/files/"):
		path = frappe.get_site_path("public", "files", url[len("/files/") :])
	elif url.startswith("/private/files/"):
		path = frappe.get_site_path("private", "files", url[len("/private/files/") :])
	if not path or not os.path.isfile(path):
		return None
	types = {".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
	kind = types.get(os.path.splitext(path)[1].lower())
	if not kind:
		return None
	with open(path, "rb") as f:
		return f.read(), kind


def _data_uri(content: bytes, kind: str) -> str:
	import base64

	return f"data:{kind};base64,{base64.b64encode(content).decode()}"


def _contact() -> list[str]:
	"""The university's postal address and contact details, from its ERPNext Company"""
	company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company") or frappe.db.get_default("company")
	if not company:
		return []
	lines = []
	address = frappe.get_all(
		"Address",
		filters=[["Dynamic Link", "link_doctype", "=", "Company"], ["Dynamic Link", "link_name", "=", company]],
		fields=["address_line1", "address_line2", "city", "country"],
		order_by="is_your_company_address desc, is_primary_address desc",
		limit=1,
	)
	if address:
		a = address[0]
		lines.append(", ".join(x for x in (a.address_line1, a.address_line2, a.city, a.country) if x))
	info = frappe.db.get_value("Company", company, ["phone_no", "email", "website"], as_dict=True) or {}
	contact = " · ".join(x for x in (f"Tel {info.phone_no}" if info.get("phone_no") else None, info.get("email"), info.get("website")) if x)
	if contact:
		lines.append(contact)
	return lines


LOGO_HEIGHT = 46


def _logo_html(brand: dict) -> str:
	"""The logo, sized: an SVG with only a viewBox has no size of its own, which the PDF tool draws as nothing"""
	import re

	logo = _file_bytes(brand["logo"])
	# a wordmark drawn with a web font (SVG text) cannot be set faithfully by the PDF tool: the brand's icon and
	# the university's name are used instead; a picture logo (PNG, JPG) or an SVG of shapes is used as it is
	if not logo or (logo[1] == "image/svg+xml" and b"<text" in logo[0]):
		mark = _file_bytes(brand.get("mark"))
		icon = f"<img src='{_data_uri(*mark)}' height='{LOGO_HEIGHT}' width='{LOGO_HEIGHT}' alt='' style='vertical-align:middle'>" if mark else ""
		return f"{icon}<span class='brandname'>{_e(brand['name'])}</span>"
	content, kind = logo
	width = None
	if kind == "image/svg+xml":
		text = content.decode("utf-8", "ignore")
		box = re.search(r'viewBox="\s*[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)\s*"', text)
		if box and float(box.group(2)):
			width = round(LOGO_HEIGHT * float(box.group(1)) / float(box.group(2)))
			text = re.sub(r"<svg\b", f'<svg width="{width}" height="{LOGO_HEIGHT}"', text, count=1)
			content = text.encode()
	size = f"height='{LOGO_HEIGHT}'" + (f" width='{width}'" if width else "")
	return f"<img src='{_data_uri(content, kind)}' {size} alt=''>"


def _page(office: str, body: str) -> str:
	"""A page on the university's letterhead: its logo, the office, its address and contact details"""
	brand = _brand()
	logo_html = _logo_html(brand)
	# the name stands beside the icon on the left; a picture logo carries it itself
	who = "".join(f"<div>{_e(line)}</div>" for line in _contact())
	return (
		"<html><head><meta charset='utf-8'>"
		+ STYLE % {"colour": _e(brand["colour"]), "accent": _e(brand["accent"])}
		+ "</head><body><div class='sheet'>"
		"<table class='letterhead'><tr>"
		f"<td class='logo'>{logo_html}</td>"
		f"<td class='who'><div class='office'>{_e(office)}</div>{who}</td>"
		"</tr></table><div class='rule'></div><div class='rule-thin'></div>"
		f"{body}</div></body></html>"
	)


def _send(filename: str, html: str, orientation: str = "Portrait", margin: str = "14mm", shrink: bool = True):
	frappe.local.response.filename = filename
	frappe.local.response.filecontent = get_pdf(
		html,
		{"margin-top": margin, "margin-bottom": margin, "margin-left": "16mm", "margin-right": "16mm", "page-size": "A4", "orientation": orientation},
		smart_shrinking=shrink,
	)
	frappe.local.response.type = "pdf"


def _e(value) -> str:
	return frappe.utils.escape_html(str(value)) if value not in (None, "") else ""


# --- verifying a document ------------------------------------------------------------------------------------


def _code(reference: str) -> str:
	"""A short code that only this site can make for a reference, so a document's QR can be checked"""
	import hashlib
	import hmac

	secret = (frappe.local.conf.get("encryption_key") or frappe.local.site).encode()
	return hmac.new(secret, reference.encode(), hashlib.sha256).hexdigest()[:10].upper()


def _verify_url(reference: str) -> str:
	from frappe.utils import get_url

	return f"{get_url()}/api/method/educore.api.v1.documents.verify?ref={reference}&code={_code(reference)}"


def _qr(url: str) -> str:
	import io

	import pyqrcode

	buffer = io.BytesIO()
	pyqrcode.create(url, error="M").svg(buffer, scale=4, quiet_zone=1)
	return _data_uri(buffer.getvalue(), "image/svg+xml")


@frappe.whitelist(allow_guest=True, methods=["GET"])
def verify(ref: str, code: str):
	"""What a scanned proof of registration leads to: whether the registration is genuine and current"""
	if ref and code == _code(ref) and frappe.db.exists("Student", ref):
		student = frappe.db.get_value("Student", ref, ["student_name", "educore_completed_on", "educore_completed_programme"], as_dict=True)
		completed = (
			_(", who completed the {0} on {1}").format(_e(student.educore_completed_programme), formatdate(student.educore_completed_on, "dd MMMM yyyy"))
			if student.educore_completed_on
			else ""
		)
		frappe.respond_as_web_page(
			_("Academic record confirmed"),
			_("{0} ({1}) is a student of record of the university{2}.").format(_e(student.student_name), _e(ref), completed),
			indicator_color="green",
		)
		return
	valid = bool(ref) and code == _code(ref) and frappe.db.exists("Program Enrollment", {"name": ref, "docstatus": 1})
	if not valid:
		frappe.respond_as_web_page(_("Not confirmed"), _("This document could not be confirmed. Contact the Office of the Registrar."), http_status_code=404, indicator_color="red")
		return
	pe = frappe.db.get_value("Program Enrollment", ref, ["student_name", "program", "academic_year"], as_dict=True)
	frappe.respond_as_web_page(
		_("Registration confirmed"),
		_("{0} is registered for the {1} academic year in the {2}. Reference {3}.").format(
			_e(pe.student_name), _e(pe.academic_year), _e(pe.program), _e(ref)
		),
		indicator_color="green",
	)


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
		f"<h1 class='letter'>Offer of a place: {_e(offering.program)}</h1>"
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

	brand = _brand()
	program = frappe.db.get_value(
		"Program", pe.program, ["educore_qualification_type", "educore_nqf_level", "department"], as_dict=True
	) or {}
	year = frappe.db.get_value("Academic Year", pe.academic_year, ["year_start_date", "year_end_date"], as_dict=True) or {}
	date = lambda d: formatdate(d, "dd MMMM yyyy") if d else None  # noqa: E731
	full_name = " ".join(x for x in (student.get("educore_title"), student.student_name) if x)
	mode = (pe.get("educore_mode_of_study") or "").lower()
	identity_label, identity = (
		("National ID number", student.get("educore_national_id"))
		if student.get("educore_national_id")
		else ("Passport number", student.get("educore_passport_number"))
	)

	def box(caption: str, facts: list[tuple[str, object]]) -> str:
		rows = "".join(f"<tr><td class='k'>{_e(k)}</td><td>{_e(v)}</td></tr>" for k, v in facts if v not in (None, ""))
		return f"<div class='box'><div class='cap'>{_e(caption)}</div><table>{rows}</table></div>"

	student_box = box("Student", [
		("Full name", full_name),
		("Student number", student.name),
		(identity_label, identity),
		("Date of birth", date(student.date_of_birth)),
		("Nationality", student.nationality),
	])
	programme_box = box("Programme", [
		("Programme", pe.program),
		("Qualification", program.get("educore_qualification_type")),
		("NQF level", program.get("educore_nqf_level")),
		("Department", (program.get("department") or "").rsplit(" - ", 1)[0]),
		("Campus", pe.get("campus")),
		("Mode of study", pe.get("educore_mode_of_study")),
		("Year of study", pe.get("educore_year_of_study") or None),
	])

	# the courses by when they run (the programme's curriculum), with the credits of each period
	when = registration_rules.semesters(pe.program)
	courses = []
	for c in pe.courses:
		code, nqf = frappe.db.get_value("Course", c.course, ["educore_course_code", "educore_nqf_level"]) or (None, None)
		courses.append((when.get(c.course, "Year"), code or c.course, c.course_name, nqf, registration_rules.credits(c.course)))
	courses.sort(key=lambda c: (registration_rules.SEMESTER_ORDER.get(c[0], 9), c[1]))
	course_rows = ""
	for period in sorted({c[0] for c in courses}, key=lambda p: registration_rules.SEMESTER_ORDER.get(p, 9)):
		group = [c for c in courses if c[0] == period]
		label = registration_rules.SEMESTER_LABELS.get(period, period)
		course_rows += "".join(
			f"<tr><td>{_e(label)}</td><td>{_e(code)}</td><td>{_e(name)}</td><td class='num'>{_e(nqf)}</td><td class='num'>{credits}</td></tr>"
			for _period, code, name, nqf, credits in group
		)
		course_rows += f"<tr class='sub'><td colspan='4'>{_e(label)}: {len(group)} courses</td><td class='num'>{sum(c[4] for c in group)}</td></tr>"
	courses_html = (
		"<div class='section'>Registered courses</div>"
		"<table class='list'><thead><tr><th>Period</th><th>Code</th><th>Course</th><th class='num'>NQF level</th><th class='num'>Credits</th></tr></thead>"
		f"<tbody>{course_rows}</tbody>"
		f"<tfoot><tr><td colspan='4'>Total for the year: {len(courses)} courses</td><td class='num'>{sum(c[4] for c in courses)}</td></tr></tfoot></table>"
		if courses
		else ""
	)
	period = (
		f" (from {date(year.get('year_start_date'))} to {date(year.get('year_end_date'))})"
		if year.get("year_start_date") and year.get("year_end_date")
		else ""
	)

	body = (
		"<table class='title-row'><tr>"
		"<td><h1>PROOF OF REGISTRATION</h1></td>"
		f"<td class='ref'>Reference <b>{_e(pe.name)}</b><br>Date issued <b>{date(nowdate())}</b></td>"
		"</tr></table>"
		"<p>To whom it may concern</p>"
		f"<p>This is to certify that <b>{_e(full_name)}</b>, student number <b>{_e(student.name)}</b>, is registered as a "
		f"{_e(mode + ' ' if mode else '')}student of {_e(brand['name'])} for the <b>{_e(pe.academic_year)}</b> academic year{_e(period)}"
		+ (f", from {date(pe.enrollment_date)}" if pe.enrollment_date else "")
		+ ", in the programme and courses below.</p>"
		f"<table class='panels'><tr><td>{student_box}</td><td>{programme_box}</td></tr></table>"
		+ courses_html
		+ "<table class='sign'><tr>"
		"<td><div class='line'>Registrar<br><span style='color:#6b6f7a'>Office of the Registrar</span></div></td>"
		"<td><div class='stamp'>Official stamp</div></td>"
		"</tr></table>"
		"<table class='verify'><tr>"
		f"<td style='width:84px'><img src='{_qr(_verify_url(pe.name))}' alt=''></td>"
		f"<td>Scan the code to confirm this registration with the university, or quote reference <b>{_e(pe.name)}</b> "
		f"and code <b>{_code(pe.name)}</b> to the Office of the Registrar.<br>"
		f"Valid for the {_e(pe.academic_year)} academic year only. Issued electronically by {_e(brand['name'])}.</td>"
		"</tr></table>"
	)
	_send(f"Proof of registration {student.name} {pe.academic_year}.pdf", _page("Office of the Registrar", body))


# --- academic record ----------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def academic_record(student: str):
	"""Every published result, year by year, for the student or the registry; interim until the programme is
	completed"""
	from educore.api.v1.student_records import RECORD_ROLES

	doc = frappe.get_doc("Student", student)
	if doc.user != frappe.session.user:
		if not set(frappe.get_roles()) & set(RECORD_ROLES):
			frappe.throw(_("Not permitted"), frappe.PermissionError)
		doc.check_permission("read")
	_send(f"Academic record {doc.name}.pdf", academic_record_html(student))


def academic_record_pdf(student: str) -> bytes:
	"""The academic record as PDF bytes, to attach to an email (an issued transcript)"""
	return get_pdf(
		academic_record_html(student),
		{"margin-top": "14mm", "margin-bottom": "14mm", "margin-left": "16mm", "margin-right": "16mm", "page-size": "A4"},
	)


def academic_record_html(student: str) -> str:
	"""The academic record page (no permission check: callers check)"""
	from educore.academics import results as exam_results

	doc = frappe.get_doc("Student", student)
	brand = _brand()
	date = lambda d: formatdate(d, "dd MMMM yyyy") if d else None  # noqa: E731
	latest = frappe.db.get_value(
		"Program Enrollment",
		{"student": student, "docstatus": 1},
		["program", "campus", "educore_mode_of_study"],
		as_dict=True,
		order_by="academic_year desc",
	) or {}
	program = frappe.db.get_value(
		"Program", latest.get("program"), ["educore_qualification_type", "educore_nqf_level", "educore_credits"], as_dict=True
	) if latest.get("program") else None
	program = program or {}
	completed = doc.get("educore_completed_on")

	rows = frappe.db.sql(
		"""select ms.academic_year, ms.course, e.final_mark, e.grade, e.result, e.first_result
		from `tabMark Sheet Entry` e join `tabMark Sheet` ms on ms.name = e.parent
		where ms.status = 'Published' and e.student = %s order by ms.academic_year, ms.course""",
		student,
		as_dict=True,
	)
	years, passed_total = "", 0
	for year in sorted({r.academic_year for r in rows}):
		lines, attempted, passed = "", 0, 0
		year_rows = [r for r in rows if r.academic_year == year]
		year_rows.sort(key=lambda r: frappe.db.get_value("Course", r.course, "educore_course_code") or r.course)
		for r in year_rows:
			code, nqf = frappe.db.get_value("Course", r.course, ["educore_course_code", "educore_nqf_level"]) or (None, None)
			credits = registration_rules.credits(r.course)
			attempted += credits
			if r.result == "Pass":
				passed += credits
			shown_final = f"{flt(r.final_mark):g}" if r.result not in ("Not admitted", "Absent") and r.final_mark is not None else ""
			note = " (supplementary)" if r.first_result else ""
			lines += (
				f"<tr><td>{_e(code or r.course)}</td><td>{_e(r.course)}</td><td class='num'>{_e(nqf)}</td><td class='num'>{credits}</td>"
				f"<td class='num'>{_e(shown_final)}</td><td>{_e(r.grade)}</td><td>{_e(r.result)}{_e(note)}</td></tr>"
			)
		passed_total += passed
		years += (
			f"<div class='section'>{_e(year)}</div>"
			"<table class='list'><thead><tr><th>Code</th><th>Course</th><th class='num'>NQF</th><th class='num'>Credits</th>"
			"<th class='num'>Final</th><th>Grade</th><th>Result</th></tr></thead>"
			f"<tbody>{lines}</tbody>"
			f"<tfoot><tr><td colspan='3'>Credits passed in {_e(year)}</td><td class='num'>{passed}</td><td colspan='3'>of {attempted} taken</td></tr></tfoot></table>"
		)
	if not rows:
		years = "<p>No results have been published yet.</p>"

	identity_label, identity = (
		("National ID number", doc.get("educore_national_id"))
		if doc.get("educore_national_id")
		else ("Passport number", doc.get("educore_passport_number"))
	)

	def box(caption: str, facts: list[tuple[str, object]]) -> str:
		body = "".join(f"<tr><td class='k'>{_e(k)}</td><td>{_e(v)}</td></tr>" for k, v in facts if v not in (None, ""))
		return f"<div class='box'><div class='cap'>{_e(caption)}</div><table>{body}</table></div>"

	required = program.get("educore_credits")
	student_box = box("Student", [
		("Full name", " ".join(x for x in (doc.get("educore_title"), doc.student_name) if x)),
		("Student number", doc.name),
		(identity_label, identity),
		("Date of birth", date(doc.date_of_birth)),
		("First registered", date(doc.joining_date)),
	])
	programme_box = box("Programme", [
		("Programme", latest.get("program")),
		("Qualification", program.get("educore_qualification_type")),
		("NQF level", program.get("educore_nqf_level")),
		("Campus", latest.get("campus")),
		("Credits passed", f"{passed_total} of {required}" if required else passed_total),
		("Completed", date(completed) if completed else "Not yet"),
	])
	bands = ", ".join(f"{g} {t:g} and above" for g, t in exam_results.grade_bands())
	rules = exam_results.settings()
	body = (
		"<table class='title-row'><tr>"
		f"<td><h1>{'ACADEMIC RECORD' if completed else 'INTERIM ACADEMIC RECORD'}</h1></td>"
		f"<td class='ref'>Student <b>{_e(doc.name)}</b><br>Date issued <b>{date(nowdate())}</b></td>"
		"</tr></table>"
		f"<table class='panels'><tr><td>{student_box}</td><td>{programme_box}</td></tr></table>"
		+ years
		+ f"<p style='margin-top:12px;color:#6b6f7a;font-size:8.5pt'>Grades: {_e(bands)}. Pass mark {flt(rules.pass_mark):g}. "
		"A supplementary pass is recorded at the university's set mark. Only results approved by an examination board "
		"and published appear on this record.</p>"
		"<table class='sign'><tr>"
		"<td><div class='line'>Registrar<br><span style='color:#6b6f7a'>Office of the Registrar</span></div></td>"
		"<td><div class='stamp'>Official stamp</div></td>"
		"</tr></table>"
		"<table class='verify'><tr>"
		f"<td style='width:84px'><img src='{_qr(_verify_url(doc.name))}' alt=''></td>"
		f"<td>Scan the code to confirm this record with the university, or quote student number <b>{_e(doc.name)}</b> "
		f"and code <b>{_code(doc.name)}</b> to the Office of the Registrar.<br>"
		f"{'Final record.' if completed else 'Interim record: the student has not completed the programme.'} Issued electronically by {_e(brand['name'])}.</td>"
		"</tr></table>"
	)
	return _page("Office of the Registrar", body)


# --- completing a programme -----------------------------------------------------------------------------------

#: who prints award certificates (the original is handed over once, by the registry) and ceremony lists
CERTIFICATE_ROLES = ("Registrar", "Registry Officer", "System Manager")

CERTIFICATE_STYLE = """
<style>
  body { font-family: "DejaVu Serif", serif; color: #1f2430; margin: 0; }
  .frame { border: 3px solid %(colour)s; padding: 5px; }
  .inner { border: 1px solid %(accent)s; padding: 9mm 18mm 6mm; text-align: center; height: 155mm; }
  .logo img { height: 22mm !important; width: auto; }
  .logo .brandname { display: none; }
  .uni { font-size: 24pt; letter-spacing: 3px; color: %(colour)s; margin: 4mm 0 9mm; text-transform: uppercase; }
  .lead { font-size: 12pt; font-style: italic; color: #4b4f5a; margin: 0 0 4mm; }
  .name { font-size: 28pt; font-weight: bold; margin: 0 0 6mm; }
  .qual { font-size: 20pt; font-weight: bold; color: %(colour)s; margin: 3mm 0 2mm; }
  .nqf { font-size: 10.5pt; color: #4b4f5a; margin: 0 0 7mm; font-family: "DejaVu Sans", sans-serif; }
  .sign { width: 100%%; border-collapse: collapse; margin-top: 20mm; }
  .sign td { width: 33%%; vertical-align: bottom; text-align: center; font-family: "DejaVu Sans", sans-serif; font-size: 9pt; }
  .sign .line { border-top: 1px solid #1f2430; width: 75%%; margin: 0 auto; padding-top: 4px; }
  .foot { width: 100%%; border-collapse: collapse; margin-top: 10mm; font-family: "DejaVu Sans", sans-serif; font-size: 7.5pt; color: #6b6f7a; text-align: left; }
  .foot td { vertical-align: middle; }
  .foot img { width: 62px; height: 62px; }
  .foot b { color: #1f2430; }
</style>
"""


def _require_certificate_role():
	if not set(frappe.get_roles()) & set(CERTIFICATE_ROLES):
		frappe.throw(_("Certificates are printed by the Office of the Registrar"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def award_certificate(student: str):
	"""The award certificate for a completed programme, as the Senate approved it; printed by the registry"""
	_require_certificate_role()
	doc = frappe.get_doc("Student", student)
	doc.check_permission("read")
	if not doc.get("educore_completed_on"):
		frappe.throw(_("{0} has not completed a programme").format(doc.student_name))
	# the original certificate is handed over once the student is financially cleared (educore.finance.clearance)
	from educore.finance.clearance import require_for_graduation

	require_for_graduation(doc.name, doc.student_name)
	program = doc.educore_completed_programme
	nqf, qualification = frappe.db.get_value("Program", program, ["educore_nqf_level", "educore_qualification_type"]) or (None, None)
	brand = _brand()
	completed = formatdate(doc.educore_completed_on, "dd MMMM yyyy")
	number = f"{doc.name}/{getdate(doc.educore_completed_on).year}"
	body = (
		"<div class='frame'><div class='inner'>"
		f"<div class='logo'>{_logo_html(brand)}</div>"
		f"<div class='uni'>{_e(brand['name'])}</div>"
		"<p class='lead'>This is to certify that</p>"
		f"<div class='name'>{_e(doc.student_name)}</div>"
		"<p class='lead'>having fulfilled the requirements prescribed by the university, was awarded the</p>"
		f"<div class='qual'>{_e(program)}</div>"
		f"<div class='nqf'>{_e(qualification) + ' · ' if qualification else ''}{'NQF level ' + _e(nqf) if nqf else ''}</div>"
		f"<p class='lead'>on {_e(completed)}{', by resolution of the ' + _e(doc.educore_completion_reference) if doc.get('educore_completion_reference') else ''}.</p>"
		"<table class='sign'><tr>"
		"<td><div class='line'>Vice-Chancellor</div></td>"
		"<td></td>"
		"<td><div class='line'>Registrar</div></td>"
		"</tr></table>"
		"<table class='foot'><tr>"
		f"<td style='width:70px'><img src='{_qr(_verify_url(doc.name))}' alt=''></td>"
		f"<td>Certificate <b>{_e(number)}</b> · student number <b>{_e(doc.name)}</b> · code <b>{_code(doc.name)}</b><br>"
		"Scan the code, or quote the student number and code to the Office of the Registrar, to confirm this award.</td>"
		"</tr></table>"
		"</div></div>"
	)
	html = (
		"<html><head><meta charset='utf-8'>"
		+ CERTIFICATE_STYLE % {"colour": _e(brand["colour"]), "accent": _e(brand["accent"])}
		+ f"</head><body>{body}</body></html>"
	)
	_send(f"Certificate {doc.name}.pdf", html, orientation="Landscape", margin="10mm", shrink=False)


@frappe.whitelist(methods=["GET"])
def ceremony_list(reference: str | None = None, year: str | None = None):
	"""The graduation ceremony list: completed students by faculty and qualification, for one Senate meeting or a
	year's completions"""
	_require_certificate_role()
	filters = {"educore_completed_on": ("is", "set")}
	if reference:
		filters["educore_completion_reference"] = reference
	if year:
		filters["educore_completed_on"] = ("between", (f"{year}-01-01", f"{year}-12-31"))
	students = frappe.get_list(
		"Student",
		filters=filters,
		fields=["name", "student_name", "educore_completed_programme as program", "educore_completed_on as completed_on", "educore_completion_reference as reference"],
		order_by="student_name asc",
		limit=0,
	)
	groups: dict[str, dict[str, list]] = {}
	for s in students:
		department, nqf = frappe.db.get_value("Program", s.program, ["department", "educore_nqf_level"]) or (None, None)
		faculty = (department or _("Other")).rsplit(" - ", 1)[0]
		groups.setdefault(faculty, {}).setdefault(s.program, []).append(frappe._dict(s, nqf=nqf))
	sections = ""
	for faculty in sorted(groups):
		sections += f"<div class='section' style='font-size:10pt;color:#1f2430'>{_e(faculty)}</div>"
		for program in sorted(groups[faculty], key=lambda p: (-(flt(groups[faculty][p][0]["nqf"])), p)):
			rows = groups[faculty][program]
			lines = "".join(
				f"<tr><td class='num'>{i}</td><td>{_e(r.student_name)}</td><td>{_e(r.name)}</td><td>{formatdate(r.completed_on, 'dd-MM-yyyy')}</td></tr>"
				for i, r in enumerate(rows, 1)
			)
			sections += (
				f"<table class='list'><thead><tr><th colspan='4'>{_e(program)} ({len(rows)})</th></tr>"
				"<tr><th class='num' style='width:28px'>#</th><th>Name</th><th>Student number</th><th>Completed</th></tr></thead>"
				f"<tbody>{lines}</tbody></table>"
			)
	if not students:
		sections = "<p>No completions recorded for this selection.</p>"
	scope = reference or (_("Completions in {0}").format(year) if year else _("All completions"))
	body = (
		"<table class='title-row'><tr>"
		"<td><h1>GRADUATION LIST</h1></td>"
		f"<td class='ref'>{_e(scope)}<br>Graduates <b>{len(students)}</b><br>Date printed <b>{formatdate(nowdate(), 'dd MMMM yyyy')}</b></td>"
		"</tr></table>"
		+ sections
		+ "<p class='foot'>Students whose completion the Senate approved, as recorded by the Office of the Registrar.</p>"
	)
	_send("Graduation list.pdf", _page("Office of the Registrar", body))


# --- sponsor statement ---------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def sponsor_statement(sponsor: str, academic_year: str):
	"""The students a sponsor pays for in a year, with what it was invoiced, has paid and owes: what Finance sends a
	sponsor to claim the fees (educore.finance.sponsors)"""
	from educore.admissions.fees import bank_details
	from educore.api.v1.sponsors import SPONSOR_ROLES

	if not set(frappe.get_roles()) & set(SPONSOR_ROLES):
		frappe.throw(_("Not permitted"), frappe.PermissionError)
	doc = frappe.get_doc("Sponsor", sponsor)
	brand = _brand()
	date = lambda d: formatdate(d, "dd MMMM yyyy") if d else ""  # noqa: E731
	money = lambda v: f"N$ {frappe.utils.fmt_money(v, precision=2)}"  # noqa: E731

	rows, invoiced, owing = "", 0.0, 0.0
	for s in frappe.get_all(
		"Sponsorship",
		filters={"sponsor": sponsor, "academic_year": academic_year, "status": "Invoiced"},
		fields=["student", "student_name", "sponsor_reference", "sponsor_invoice", "amount"],
		order_by="student_name asc",
	):
		program = frappe.db.get_value("Program Enrollment", {"student": s.student, "academic_year": academic_year, "docstatus": 1}, "program")
		left = flt(frappe.db.get_value("Sales Invoice", s.sponsor_invoice, "outstanding_amount"))
		invoiced += flt(s.amount)
		owing += left
		rows += (
			f"<tr><td>{_e(s.student)}</td><td>{_e(s.student_name)}</td><td>{_e(program)}</td><td>{_e(s.sponsor_reference)}</td>"
			f"<td>{_e(s.sponsor_invoice)}</td><td class='num'>{money(s.amount)}</td><td class='num'>{money(flt(s.amount) - left)}</td>"
			f"<td class='num'>{money(left)}</td></tr>"
		)
	bank = bank_details()
	addressee = "".join(f"<div>{_e(line)}</div>" for line in (doc.contact_person, doc.sponsor_name, *(doc.address or "").splitlines()) if line)
	body = (
		"<table class='title-row'><tr>"
		f"<td><h1>SPONSOR STATEMENT {_e(academic_year)}</h1></td>"
		f"<td class='ref'>Sponsor number <b>{_e(doc.name)}</b><br>Date issued <b>{date(nowdate())}</b></td>"
		"</tr></table>"
		f"<div style='margin-bottom:10px'>{addressee}</div>"
		f"<p>The fees of the students below for the {_e(academic_year)} academic year, invoiced to {_e(doc.sponsor_name)}.</p>"
		"<table class='list'><thead><tr><th>Student number</th><th>Student</th><th>Programme</th><th>Your reference</th>"
		"<th>Invoice</th><th class='num'>Invoiced</th><th class='num'>Paid</th><th class='num'>Due</th></tr></thead>"
		f"<tbody>{rows or '<tr><td colspan=8>No students invoiced for this year.</td></tr>'}</tbody>"
		f"<tfoot><tr><td colspan='5'>Total</td><td class='num'>{money(invoiced)}</td><td class='num'>{money(invoiced - owing)}</td>"
		f"<td class='num'>{money(owing)}</td></tr></tfoot></table>"
		+ (
			"<div class='section'>Payment</div>"
			f"<p>By EFT to {_e(bank['bank_name'])}, {_e(bank['account_name'])}, account {_e(bank['account_number'])}"
			+ (f", branch {_e(bank['branch_code'])}" if bank.get("branch_code") else "")
			+ f". Please quote <b>{_e(doc.name)}</b> as the reference.</p>"
			if bank.get("account_number")
			else ""
		)
		+ f"<p style='color:#6b6f7a'>Issued electronically by {_e(brand['name'])}, Finance.</p>"
	)
	_send(f"Sponsor statement {doc.name} {academic_year}.pdf", _page("Finance", body), orientation="Landscape")
