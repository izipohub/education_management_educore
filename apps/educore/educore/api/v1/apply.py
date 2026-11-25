"""The online application, for the Vue app's applicant portal (docs/architecture/online-applications.md).

- register() and options() are open to guests: anyone may create an applicant account and see what is on offer.
- Everything else works on the signed-in applicant's own application only: it is found by the session's user
  (Student Applicant.educore_applicant_user), never by a name or number the browser sends. Writes are made by
  these functions after that check, so applicants need no permission on Student Applicant itself, and the
  fields they may set are listed here. Points, eligibility and document verification are computed or set by
  the university, never taken from the browser.
"""

import os
import re

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.utils import cint, getdate, nowdate, validate_email_address

from educore.admissions import application as rules
from educore.admissions import fees, notify, offers, pathways

ALLOWED_FILE_TYPES = {".pdf": "application/pdf", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}

#: fields an applicant may set on their draft
PERSONAL_FIELDS = (
	"first_name",
	"middle_name",
	"last_name",
	"date_of_birth",
	"gender",
	"nationality",
	"student_mobile_number",
	"address_line_1",
	"address_line_2",
	"city",
	"country",
	# the particulars Namibian universities ask (custom fields on Student Applicant)
	"educore_title",
	"educore_previous_surname",
	"educore_marital_status",
	"educore_home_language",
	"educore_home_town",
	"educore_region_of_origin",
	"educore_minority_group",
	"educore_national_id",
	"educore_passport_number",
	"educore_passport_expiry",
	"educore_study_permit",
	"educore_alternative_phone",
	"educore_postal_address",
	"educore_kin_relationship",
	"educore_kin_name",
	"educore_kin_phone",
	"educore_kin_email",
	"educore_kin_address",
	"educore_fee_payer",
	"educore_fee_payer_name",
	"educore_fee_payer_email",
	"educore_fee_payer_phone",
	"educore_disability",
	"educore_support_needs",
)

#: phone numbers are kept with their country code: +264811234567
PHONE_FIELDS = ("student_mobile_number", "educore_alternative_phone", "educore_kin_phone", "educore_fee_payer_phone")
EMAIL_FIELDS = ("educore_kin_email", "educore_fee_payer_email")

PRIOR_FIELDS = ("qualification", "institution", "country", "nqf_level", "year_completed", "average")
EMPLOYMENT_FIELDS = ("employer", "position", "from_date", "to_date", "duties")
REFEREE_FIELDS = ("full_name", "position", "institution", "email", "phone")


# --- account -------------------------------------------------------------------------------------------


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=5, seconds=60 * 60)
def register(first_name: str, last_name: str, email: str, password: str) -> dict:
	"""An applicant account (a portal login with the Applicant position); then sign in as usual"""
	from educore.access.demo_users import new_user

	email = (email or "").strip().lower()
	validate_email_address(email, throw=True)
	if not (first_name or "").strip() or not (last_name or "").strip():
		frappe.throw(_("Give your first name and last name"))
	if frappe.db.exists("User", email):
		frappe.throw(_("There is already an account for {0}. Sign in instead.").format(email))
	# Frappe checks the password against the site's password policy when the user is saved
	new_user(email=email, first_name=first_name.strip(), last_name=last_name.strip(), password=password, positions=["Applicant"])
	return {"email": email}


# --- what can be applied for ---------------------------------------------------------------------------


def _open_intakes() -> list[dict]:
	intakes = frappe.get_all(
		"Student Admission",
		filters={"published": 1, "enable_admission_application": 1},
		fields=["name", "title", "academic_year", "admission_start_date", "admission_end_date"],
		order_by="admission_end_date asc",
	)
	return [i for i in intakes if rules.intake_open(i.name)]


@frappe.whitelist(allow_guest=True, methods=["GET"])
def options() -> dict:
	"""Open intakes, the offerings and their entry requirements, subjects, grades and required documents"""
	settings = rules.settings()
	offerings = frappe.get_all(
		"Programme Offering",
		filters={"is_active": 1},
		fields=["name", "program", "campus", "mode_of_study"],
		order_by="program asc, campus asc",
	)
	programmes = {}
	for offering in offerings:
		if offering.program not in programmes:
			program = frappe.get_cached_doc("Program", offering.program)
			programmes[offering.program] = {
				"code": program.get("educore_programme_code"),
				"qualification": program.get("educore_qualification_type"),
				"nqf_level": program.get("educore_nqf_level"),
				"duration_years": program.get("educore_duration_years"),
				"faculty": (program.department or "").rsplit(" - ", 1)[0],
				"level": program.get("educore_study_level") or pathways.UNDERGRADUATE,
				"min_points": program.get("educore_min_points"),
				"min_prior_nqf": program.get("educore_min_prior_nqf"),
				"min_prior_average": program.get("educore_min_prior_average"),
				"subject_requirements": [
					{"subject": r.subject, "level": r.level, "grade": r.grade}
					for r in program.get("educore_subject_requirements") or []
				],
			}
		offering.update(programmes[offering.program])

	grades: dict[str, list[str]] = {}
	for row in settings.points_scale:
		grades.setdefault(row.level, []).append(row.grade)
	return {
		"intakes": _open_intakes(),
		"offerings": offerings,
		"subjects": frappe.get_all(
			"School Subject", filters={"requirement_only": 0}, pluck="name", order_by="name asc"
		),
		"grades": grades,
		"best_subjects": settings.best_subjects,
		"scale_is_placeholder": bool(settings.scale_is_placeholder),
		"documents": frappe.get_all(
			"Admission Document Type",
			filters={"active": 1},
			fields=["name", "required_for", "must_be_certified", "description"],
			order_by="required_for asc, name asc",
		),
		"certification_max_age_months": settings.certification_max_age_months,
		"max_file_size_mb": settings.max_file_size_mb,
		"max_choices": rules.max_choices(),
		"home_country": settings.home_country or "Namibia",
		"countries": frappe.get_all("Country", pluck="name", order_by="name asc"),
		"dial_codes": _dial_codes(),
		"pathways": pathways.active(),
		# who pays: each route with what it asks and whether it pays the application fee
		"funding_routes": _funding_routes(),
	}


def _funding_routes() -> list[dict]:
	from educore.admissions import funding

	return funding.active()


def _dial_codes() -> list[dict]:
	"""Each country's calling code (Frappe's country data), for the phone fields"""
	from frappe.geo.country_info import get_all

	return sorted(
		({"country": name, "code": info["isd"]} for name, info in get_all().items() if info.get("isd")),
		key=lambda c: c["country"],
	)


@frappe.whitelist(methods=["GET"])
def schools(search: str = "") -> list[dict]:
	search = (search or "").strip()
	if len(search) < 2:
		return []
	like = f"%{search}%"
	return frappe.get_all(
		"Secondary School",
		filters={"active": 1},
		or_filters=[["school_name", "like", like], ["town", "like", like], ["centre_number", "like", like]],
		fields=["name", "school_name", "town", "region", "centre_number"],
		order_by="school_name asc",
		limit=20,
	)


# --- the applicant's own application -------------------------------------------------------------------


def _require_applicant():
	if frappe.session.user == "Guest" or "Applicant" not in frappe.get_roles():
		frappe.throw(_("Sign in with your applicant account"), frappe.PermissionError)


def _own_application(for_update: bool = False):
	_require_applicant()
	name = frappe.db.get_value(
		"Student Applicant", {"educore_applicant_user": frappe.session.user}, "name", order_by="creation desc"
	)
	if not name:
		return None
	return frappe.get_doc("Student Applicant", name, for_update=for_update)


def _serialise(doc) -> dict:
	documents = {d.document_type: d for d in doc.get("educore_documents") or []}
	school = (
		frappe.db.get_value(
			"Secondary School", doc.educore_secondary_school, ["name", "school_name", "town", "region"], as_dict=True
		)
		if doc.get("educore_secondary_school")
		else None
	)
	return {
		"name": doc.name,
		"status": doc.application_status,
		"editable": doc.application_status == "Draft",
		"intake": doc.student_admission,
		"academic_year": doc.academic_year,
		"pathway": doc.get("educore_pathway"),
		"international": bool(doc.get("educore_international")),
		"personal": {field: doc.get(field) for field in (*PERSONAL_FIELDS, "student_email_id")},
		"school": school,
		"exam_number": doc.get("educore_exam_number"),
		"exam_year": doc.get("educore_exam_year"),
		"results": [{"subject": r.subject, "level": r.level, "grade": r.grade, "points": r.points} for r in doc.educore_results],
		"points": doc.get("educore_points"),
		"prior_qualifications": [
			{field: row.get(field) for field in PRIOR_FIELDS} for row in doc.get("educore_prior_qualifications") or []
		],
		"previous_student_number": doc.get("educore_previous_student_number"),
		"employment": [
			{field: str(row.get(field)) if row.get(field) and "date" in field else row.get(field) for field in EMPLOYMENT_FIELDS}
			for row in doc.get("educore_employment") or []
		],
		"work_years": doc.get("educore_work_years"),
		"referees": [{field: row.get(field) for field in REFEREE_FIELDS} for row in doc.get("educore_referees") or []],
		"choices": [
			{
				"rank": c.rank,
				"offering": c.programme_offering,
				"program": c.program,
				"campus": c.campus,
				"eligibility": c.eligibility,
				"eligibility_note": c.eligibility_note,
			}
			for c in doc.educore_choices
		],
		"documents": [
			{
				"document_type": name,
				"uploaded": name in documents,
				"file_name": _file_name(documents[name]) if name in documents else None,
				"file_url": documents[name].file if name in documents else None,
				"certified_on": str(documents[name].certified_on) if name in documents and documents[name].certified_on else None,
				"status": documents[name].status if name in documents else None,
				"rejection_reason": documents[name].rejection_reason if name in documents else None,
				"required": required,
			}
			for name, required in _documents_in_order(doc)
		],
		"missing": rules.missing(doc) if doc.application_status == "Draft" else [],
		"declaration": bool(doc.get("educore_declaration")),
		"submitted_on": str(doc.educore_submitted_on) if doc.get("educore_submitted_on") else None,
		"decision_reason": doc.get("educore_decision_reason") if doc.application_status == "Rejected" else None,
		"fee": _fee(doc),
		"offer": _offer(doc),
	}


def _offer(doc) -> dict | None:
	"""The offer letter's content, once there is an offer (online applications only)"""
	if not doc.get("educore_offer_status"):
		return None
	from educore.finance.student_fees import fee_structure_for

	offering = frappe.db.get_value(
		"Programme Offering", doc.educore_programme_offering, ["program", "campus", "mode_of_study"], as_dict=True
	)
	structure = fee_structure_for(doc.educore_programme_offering, doc.academic_year)
	start = frappe.db.get_value("Academic Term", doc.academic_term, "term_start_date") if doc.academic_term else None
	return {
		"status": doc.educore_offer_status,
		"programme": offering.program,
		"campus": offering.campus,
		"mode_of_study": offering.mode_of_study,
		"academic_year": doc.academic_year,
		"starts_on": str(start) if start else None,
		"annual_fees": frappe.db.get_value("Fee Structure", structure, "total_amount") if structure else None,
		"conditions": doc.get("educore_offer_conditions"),
		"deadline": str(doc.educore_offer_deadline) if doc.get("educore_offer_deadline") else None,
		"responded_on": str(doc.educore_offer_responded_on) if doc.get("educore_offer_responded_on") else None,
		"decided_on": str(doc.educore_decided_on) if doc.get("educore_decided_on") else None,
		"university": notify.university(),
	}


def _fee(doc) -> dict:
	"""What to pay and how: EFT with the application number as reference (card once DPO is connected)"""
	settings = rules.settings()
	return {
		"amount": doc.get("educore_fee_amount"),
		"status": doc.get("educore_fee_status") or "Unpaid",
		"paid_on": str(doc.educore_fee_paid_on) if doc.get("educore_fee_paid_on") else None,
		"reference": doc.name,
		"bank": fees.bank_details(),
		"card_payments": bool(settings.card_payments_enabled),
	}


def _file_name(row) -> str:
	if row.get("file_doc"):
		name = frappe.db.get_value("File", row.file_doc, "file_name")
		if name:
			return name
	return os.path.basename(row.file or "")


def _documents_in_order(doc) -> list[tuple[str, bool]]:
	"""What this applicant is asked for (required first), then anything uploaded that no longer is (after
	changing pathway): shown so it can be removed"""
	plan = rules.document_plan(doc)
	extra = [d.document_type for d in doc.get("educore_documents") or [] if d.document_type not in plan]
	return [*plan.items(), *((name, False) for name in extra)]


@frappe.whitelist(methods=["GET"])
def my_application() -> dict | None:
	doc = _own_application()
	return _serialise(doc) if doc else None


def _first_term(academic_year: str) -> str | None:
	return frappe.db.get_value(
		"Academic Term", {"academic_year": academic_year}, "name", order_by="term_start_date asc"
	)


@frappe.whitelist(methods=["POST"])
def save(data: dict | str) -> dict:
	"""Create or update the applicant's draft. Only the fields listed in this module are taken."""
	data = frappe.parse_json(data) if isinstance(data, str) else frappe._dict(data)
	doc = _own_application(for_update=True)
	if doc and doc.application_status != "Draft":
		frappe.throw(_("Your application is submitted and can no longer be changed"))

	if not doc:
		intake = data.get("intake")
		if not intake or intake not in [i.name for i in _open_intakes()]:
			frappe.throw(_("Choose an intake that is open for applications"))
		user = frappe.get_cached_doc("User", frappe.session.user)
		academic_year = frappe.db.get_value("Student Admission", intake, "academic_year")
		doc = frappe.new_doc("Student Applicant")
		doc.update(
			{
				"first_name": user.first_name,
				"last_name": user.last_name,
				"student_email_id": user.name,
				"educore_applicant_user": user.name,
				"student_admission": intake,
				"academic_year": academic_year,
				"academic_term": _first_term(academic_year),
				# the first route the university lists (usually school leaver) until the applicant picks another
				"educore_pathway": next((p["name"] for p in pathways.active()), None),
			}
		)

	apply_fields(doc, data)

	doc.flags.ignore_permissions = True
	if doc.is_new():
		_insert_draft(doc)
	else:
		doc.save()
	return _serialise(doc)


def apply_fields(doc, data):
	"""The applicant's details from the form, onto a draft: only the fields listed in this module are taken.
	Used for an online draft and for a paper application staff capture (educore.api.v1.admissions.capture)."""
	personal = data.get("personal") or {}
	for field in PERSONAL_FIELDS:
		if field in personal:
			doc.set(field, (personal[field] or None) if not isinstance(personal[field], str) else personal[field].strip() or None)
	if doc.get("date_of_birth") and getdate(doc.date_of_birth) >= getdate(nowdate()):
		frappe.throw(_("Check your date of birth"))
	for field in PHONE_FIELDS:
		doc.set(field, phone(doc.get(field)))
	for field in EMAIL_FIELDS:
		if doc.get(field):
			validate_email_address(doc.get(field), throw=True)
	if not doc.get("educore_disability"):
		doc.educore_support_needs = None
	if "international" in data:
		doc.educore_international = 1 if data.get("international") else 0
	if data.get("pathway") and data["pathway"] != doc.get("educore_pathway"):
		_change_pathway(doc, data["pathway"])

	if "school" in data:
		doc.educore_secondary_school = _school(data.get("school") or {})
	for field, target in (("exam_number", "educore_exam_number"), ("exam_year", "educore_exam_year")):
		if field in data:
			doc.set(target, cint(data[field]) if field == "exam_year" and data[field] else data[field] or None)

	if "results" in data:
		doc.set("educore_results", [])
		for row in data.get("results") or []:
			if row.get("subject") and row.get("level") and row.get("grade"):
				doc.append("educore_results", {"subject": row["subject"], "level": row["level"], "grade": str(row["grade"]).strip()})
	if "choices" in data:
		doc.set("educore_choices", [])
		for rank, offering in enumerate(data.get("choices") or [], start=1):
			if offering:
				doc.append("educore_choices", {"rank": rank, "programme_offering": offering})

	if "previous_student_number" in data:
		doc.educore_previous_student_number = (data.get("previous_student_number") or "").strip() or None
	_set_rows(doc, data, "prior_qualifications", "educore_prior_qualifications", PRIOR_FIELDS, ("qualification", "institution"))
	_set_rows(doc, data, "employment", "educore_employment", EMPLOYMENT_FIELDS, ("employer", "position", "from_date"))
	_set_rows(doc, data, "referees", "educore_referees", REFEREE_FIELDS, ("full_name", "email"))
	for row in doc.get("educore_referees") or []:
		validate_email_address(row.email, throw=True)
		row.phone = phone(row.phone)
	for row in doc.get("educore_employment") or []:
		if row.to_date and getdate(row.to_date) < getdate(row.from_date):
			frappe.throw(_("{0}: the end date is before the start date").format(row.employer))


def phone(value: str | None) -> str | None:
	"""A phone number with its country code, digits only after the +: '+264 81 123 4567' is +264811234567"""
	if not value:
		return None
	digits = re.sub(r"[\s\-().]", "", str(value))
	if not re.fullmatch(r"\+\d{7,15}", digits):
		frappe.throw(_("{0}: give the number with its country code, e.g. +264 81 123 4567").format(value))
	return digits


def _change_pathway(doc, pathway: str):
	"""A pathway the university has open; choices at the other level no longer apply and are dropped"""
	if not frappe.db.exists("Admission Pathway", {"name": pathway, "active": 1}):
		frappe.throw(_("Choose one of the pathways listed"))
	doc.educore_pathway = pathway
	level = pathways.level(doc)
	doc.set("educore_choices", [c for c in doc.get("educore_choices") or [] if _level_of(c.programme_offering) == level])


def _level_of(offering: str) -> str:
	program = frappe.db.get_value("Programme Offering", offering, "program")
	return frappe.get_cached_value("Program", program, "educore_study_level") or pathways.UNDERGRADUATE


def _set_rows(doc, data, key: str, table: str, fields: tuple, needed: tuple):
	"""Replace a table with the rows sent, keeping only the fields listed; rows missing a needed field are skipped"""
	if key not in data:
		return
	doc.set(table, [])
	for row in data.get(key) or []:
		clean = {}
		for field in fields:
			value = row.get(field)
			clean[field] = value.strip() or None if isinstance(value, str) else value
		if all(clean.get(field) for field in needed):
			doc.append(table, clean)


def _insert_draft(doc):
	"""Education names an applicant from its intake's programme, so a new draft needs one: the first choice's.
	A draft with no choice yet is saved without the intake, which is added straight after."""
	first = next((c.programme_offering for c in doc.educore_choices if c.programme_offering), None)
	if first:
		doc.program = frappe.db.get_value("Programme Offering", first, "program")
		doc.insert()
		return
	intake, doc.student_admission = doc.student_admission, None
	doc.insert()
	doc.student_admission = intake
	doc.save()


def _school(school: dict) -> str | None:
	"""A school from the list, or one the applicant typed in (added for admissions to check)"""
	if school.get("name"):
		if not frappe.db.exists("Secondary School", {"name": school["name"], "active": 1}):
			frappe.throw(_("Choose your school from the list"))
		return school["name"]
	typed = (school.get("school_name") or "").strip()
	if not typed:
		return None
	existing = frappe.db.get_value("Secondary School", {"school_name": typed, "town": (school.get("town") or "").strip() or None})
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Secondary School",
				"school_name": typed,
				"town": (school.get("town") or "").strip() or None,
				"country": school.get("country") or "Namibia",
				"added_by_applicant": 1,
			}
		)
		.insert(ignore_permissions=True)
		.name
	)


@frappe.whitelist(methods=["POST"])
def upload_document(document_type: str, certified_on: str | None = None) -> dict:
	"""One document (multipart field "file"), stored privately; replaces an earlier upload of the same document"""
	doc = _own_application(for_update=True)
	if not doc:
		frappe.throw(_("Start your application first"))
	if doc.application_status != "Draft" and not _replacing_rejected(doc, document_type):
		frappe.throw(_("Your application is submitted and can no longer be changed"))
	if not frappe.db.exists("Admission Document Type", {"name": document_type, "active": 1}):
		frappe.throw(_("Unknown document {0}").format(document_type))

	upload = frappe.request.files.get("file") if frappe.request and frappe.request.files else None
	if not upload or not upload.filename:
		frappe.throw(_("Choose a file to upload"))
	extension = os.path.splitext(upload.filename)[1].lower()
	if extension not in ALLOWED_FILE_TYPES:
		frappe.throw(_("Upload a PDF, JPG or PNG file"))
	content = upload.stream.read()
	limit = (rules.settings().max_file_size_mb or 5) * 1024 * 1024
	if len(content) > limit:
		frappe.throw(_("The file is larger than {0} MB").format(rules.settings().max_file_size_mb or 5))
	if not content:
		frappe.throw(_("The file is empty"))
	if certified_on and getdate(certified_on) > getdate(nowdate()):
		frappe.throw(_("The certification date cannot be in the future"))

	safe_type = "".join(ch if ch.isalnum() else "-" for ch in document_type).strip("-").lower()
	try:
		# Frappe checks the content (a PDF is parsed, so a damaged or disguised file is refused)
		file_doc = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"{doc.name}-{safe_type}{extension}",
				"attached_to_doctype": "Student Applicant",
				"attached_to_name": doc.name,
				"is_private": 1,
				"content": content,
			}
		).insert(ignore_permissions=True)
	except frappe.ValidationError:
		raise
	except Exception:
		# the applicant's file, not a system fault: tell them, log nothing
		frappe.throw(_("The file could not be read. Scan it again as a PDF, JPG or PNG and upload that."))

	previous = [d for d in doc.educore_documents if d.document_type == document_type]
	for row in previous:
		_delete_file(row)
		doc.remove(row)
	doc.append(
		"educore_documents",
		{
			"document_type": document_type,
			"file": file_doc.file_url,
			"file_doc": file_doc.name,
			"certified_on": certified_on or None,
			"status": "Pending",
		},
	)
	doc.flags.ignore_permissions = True
	doc.save()
	return _serialise(doc)


def _replacing_rejected(doc, document_type: str) -> bool:
	"""After submitting, an applicant may replace only a document admissions rejected"""
	return doc.application_status == "Applied" and any(
		d.document_type == document_type and d.status == "Rejected" for d in doc.educore_documents
	)


def _delete_file(row):
	"""This upload's own File record only: identical uploads share one stored file, and Frappe keeps the stored
	file while another File record still points to it"""
	if row.get("file_doc") and frappe.db.exists("File", row.file_doc):
		frappe.delete_doc("File", row.file_doc, ignore_permissions=True, force=True)


@frappe.whitelist(methods=["POST"])
def remove_document(document_type: str) -> dict:
	doc = _own_application(for_update=True)
	if not doc or doc.application_status != "Draft":
		frappe.throw(_("Only a draft application can be changed"))
	for row in [d for d in doc.educore_documents if d.document_type == document_type]:
		_delete_file(row)
		doc.remove(row)
	doc.flags.ignore_permissions = True
	doc.save()
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def submit(declaration: bool | str = False) -> dict:
	"""Submit the draft: the workflow's Submit action, after the completeness checks"""
	doc = _own_application(for_update=True)
	if not doc or doc.application_status != "Draft":
		frappe.throw(_("There is no draft application to submit"))
	if not cint(declaration if not isinstance(declaration, str) else declaration.lower() in ("1", "true", "yes")):
		frappe.throw(_("Accept the declaration to submit the application"))
	doc.educore_declaration = 1
	doc.application_status = "Applied"
	doc.flags.ignore_permissions = True
	# the workflow checks the transition itself: Draft → Applied is the Applicant's "Submit"
	doc.save()
	doc.add_comment("Workflow", _("Submitted online"))
	return _serialise(doc)


@frappe.whitelist(methods=["POST"])
def accept_offer() -> dict:
	doc = _own_application(for_update=True)
	if not doc:
		frappe.throw(_("There is no offer awaiting your response"))
	offers.accept(doc)
	return _serialise(frappe.get_doc("Student Applicant", doc.name))


@frappe.whitelist(methods=["POST"])
def decline_offer(reason: str | None = None) -> dict:
	doc = _own_application(for_update=True)
	if not doc:
		frappe.throw(_("There is no offer awaiting your response"))
	offers.decline(doc, reason)
	return _serialise(frappe.get_doc("Student Applicant", doc.name))
