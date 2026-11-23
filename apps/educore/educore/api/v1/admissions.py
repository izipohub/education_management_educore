"""Admission decisions, for the Vue app's admissions queue.

Reads go through frappe.get_list, so each officer sees only the applicants their campus User Permission
allows. Decisions go through the "EduCore Admission Decision" workflow, which checks the role, and the
applicant's validation, which checks intake capacity and the reason (educore.academics.students).
"""

import os

import frappe
from frappe import _
from frappe.model.workflow import apply_workflow, get_transitions
from frappe.utils import add_months, getdate, now_datetime, nowdate, validate_email_address

from educore.admissions import application as rules
from educore.admissions import pathways
from educore.admissions import fees, notify, offers

STATUSES = ("Applied", "Approved", "Rejected", "Declined", "Lapsed", "Admitted")
NEEDS_REASON = ("Reject", "Withdraw Offer")

FIELDS = [
	"name",
	"title",
	"first_name",
	"last_name",
	"educore_programme_offering as offering",
	"program",
	"campus",
	"educore_mode_of_study as mode_of_study",
	"academic_year",
	"application_date",
	"application_status as status",
	"educore_decided_by as decided_by",
	"educore_decided_on as decided_on",
	"educore_decision_reason as decision_reason",
	"educore_points as points",
	"educore_fee_status as fee_status",
	"educore_offer_status as offer_status",
	"educore_offer_deadline as offer_deadline",
]

#: who checks documents and waives fees
REVIEW_ROLES = ("Admissions Officer", "Registrar", "System Manager")


def _actions(doc) -> list[str]:
	"""The workflow actions the current user may take on this applicant now"""
	if not doc.has_permission("write"):
		return []
	return [t.action for t in get_transitions(doc)]


def _completeness(doc) -> dict:
	"""For an online application: documents verified of those required, the fee, and what blocks a decision"""
	online = bool(doc.get("educore_applicant_user"))
	required = rules.required_documents(doc) if online else []
	verified = {d.document_type for d in doc.get("educore_documents") or [] if d.status == "Verified"}
	rejected = [d.document_type for d in doc.get("educore_documents") or [] if d.status == "Rejected"]
	blockers = rules.decision_blockers(doc)
	return {
		"online": online,
		"documents_required": len(required),
		"documents_verified": len([d for d in required if d in verified]),
		"documents_rejected": rejected,
		"blockers": blockers,
		"ready": not blockers,
	}


def _row(row) -> dict:
	row = dict(row)
	row["applicant"] = row.get("title") or " ".join(p for p in (row.get("first_name"), row.get("last_name")) if p)
	doc = frappe.get_doc("Student Applicant", row["name"])
	row["actions"] = _actions(doc)
	row["choices"] = [
		{"rank": c.rank, "offering": c.programme_offering, "program": c.program, "campus": c.campus, "eligibility": c.eligibility}
		for c in doc.get("educore_choices") or []
	]
	row.update(_completeness(doc))
	return row


def _filters(status: str, academic_year: str | None) -> dict:
	filters = {"application_status": status}
	if academic_year:
		filters["academic_year"] = academic_year
	return filters


@frappe.whitelist(methods=["GET"])
def applications(
	status: str = "Applied",
	academic_year: str | None = None,
	search: str | None = None,
	start: int = 0,
	page_length: int = 50,
) -> dict:
	if status not in STATUSES:
		frappe.throw(_("Unknown status {0}").format(status))
	years = sorted(
		set(frappe.get_list("Student Applicant", pluck="academic_year", distinct=True, limit=0)), reverse=True
	)
	# no year asked for: the newest year this user has applications in
	academic_year = academic_year or (years[0] if years else None)
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [["first_name", "like", like], ["last_name", "like", like], ["name", "like", like]]

	rows = frappe.get_list(
		"Student Applicant",
		filters=_filters(status, academic_year),
		or_filters=or_filters,
		fields=FIELDS,
		order_by="application_date asc, name asc",
		start=int(start),
		page_length=min(int(page_length), 200),
	)
	counts = {
		s: len(frappe.get_list("Student Applicant", filters=_filters(s, academic_year), pluck="name", limit=0))
		for s in STATUSES
	}
	return {
		"rows": [_row(r) for r in rows],
		"counts": counts,
		"academic_year": academic_year,
		"academic_years": years,
		"capacity": _capacity({r.offering for r in rows if r.offering}, {r.academic_year for r in rows}),
	}


def _places(doc) -> dict | None:
	"""Places offered so far on the offering applied for, against its capacity"""
	offering = doc.get("educore_programme_offering")
	if not offering or not doc.academic_year:
		return None
	return _capacity({offering}, {doc.academic_year}).get(f"{offering}|{doc.academic_year}")


def _capacity(offerings: set[str], years: set[str]) -> dict:
	"""Places offered so far against each offering's intake capacity, per academic year"""
	result = {}
	for offering in offerings:
		capacity = frappe.db.get_value("Programme Offering", offering, "intake_capacity") or None
		for year in years:
			taken = frappe.db.count(
				"Student Applicant",
				{
					"educore_programme_offering": offering,
					"academic_year": year,
					"application_status": ("in", ("Approved", "Admitted")),
				},
			)
			result[f"{offering}|{year}"] = {"capacity": capacity, "taken": taken}
	return result


@frappe.whitelist(methods=["POST"])
def decide(
	name: str, action: str, reason: str | None = None, conditions: str | None = None, offering: str | None = None
) -> dict:
	"""Approve (optionally another of the applicant's choices, and with offer conditions), Reject, Withdraw Offer
	or Reconsider an application"""
	doc = frappe.get_doc("Student Applicant", name)
	# campus scope and role: before anything is written
	doc.check_permission("write")
	if action == "Approve" and offering and offering != doc.educore_programme_offering:
		_offer_choice(doc, offering)
	if action == "Approve":
		# saved first, like the reason: the workflow action reloads the applicant
		doc.db_set("educore_offer_conditions", (conditions or "").strip() or None)
	if action in NEEDS_REASON:
		if not (reason or "").strip():
			frappe.throw(_("Give the reason for this decision"))
		# saved first: the workflow action reloads the applicant from the database
		doc.db_set("educore_decision_reason", reason.strip())
	apply_workflow(doc, action)
	row = frappe.get_list("Student Applicant", filters={"name": name}, fields=FIELDS, limit=1)[0]
	return _row(row)


def _offer_choice(doc, offering: str):
	"""Offer another of the applicant's choices (e.g. the second, when the first is full): it becomes the offering
	under decision. Saved first, like the reason: the workflow action reloads the applicant."""
	choice = next((c for c in doc.get("educore_choices") or [] if c.programme_offering == offering), None)
	if not choice:
		frappe.throw(_("{0} is not one of the applicant's choices").format(offering))
	campus = frappe.db.get_value("Programme Offering", offering, "campus")
	# the officer's own campuses (their User Permissions): another campus's officers offer its places
	if campus not in frappe.get_list("Campus", pluck="name", limit=0):
		frappe.throw(_("{0} is at {1}: an officer there makes this offer").format(offering, campus), frappe.PermissionError)
	program = frappe.db.get_value("Programme Offering", offering, "program")
	doc.db_set({"educore_programme_offering": offering, "program": program, "campus": campus})
	doc.add_comment("Info", _("Offer made on choice {0}: {1}").format(choice.rank, offering))


# --- reviewing an online application --------------------------------------------------------------------


def _reviewable(name: str, write: bool = False):
	"""The applicant, if this user may see it (campus scope); for changes, also the admissions roles"""
	doc = frappe.get_doc("Student Applicant", name)
	doc.check_permission("write" if write else "read")
	if write and not set(frappe.get_roles()) & set(REVIEW_ROLES):
		frappe.throw(_("Only admissions staff check documents and fees"), frappe.PermissionError)
	return doc


def _certification_problem(row) -> str | None:
	if not frappe.get_cached_value("Admission Document Type", row.document_type, "must_be_certified"):
		return None
	if not row.certified_on:
		return _("No certification date given")
	max_age = rules.settings().certification_max_age_months or 0
	if max_age and getdate(row.certified_on) < getdate(add_months(nowdate(), -max_age)):
		return _("Certified more than {0} months ago").format(max_age)
	return None


@frappe.whitelist(methods=["GET"])
def review(name: str) -> dict:
	"""Everything an admissions officer needs to check one application"""
	doc = _reviewable(name)
	required = set(rules.required_documents(doc))
	school = (
		frappe.db.get_value(
			"Secondary School",
			doc.educore_secondary_school,
			["school_name", "town", "region", "centre_number", "emis_number", "added_by_applicant"],
			as_dict=True,
		)
		if doc.get("educore_secondary_school")
		else None
	)
	from educore.api.v1.apply import PERSONAL_FIELDS

	return {
		"name": doc.name,
		"applicant": doc.title,
		# identity, origin, next of kin, who pays, support (the particulars on the form)
		"particulars": {
			field: str(doc.get(field)) if field == "educore_passport_expiry" and doc.get(field) else doc.get(field)
			for field in PERSONAL_FIELDS
			if field.startswith("educore_")
		},
		"status": doc.application_status,
		"intake": doc.student_admission,
		"pathway": doc.get("educore_pathway"),
		"international": bool(doc.get("educore_international")),
		"age": pathways.age_on_intake(doc),
		"submitted_on": str(doc.educore_submitted_on) if doc.get("educore_submitted_on") else None,
		"personal": {
			"email": doc.student_email_id,
			"date_of_birth": str(doc.date_of_birth) if doc.date_of_birth else None,
			"gender": doc.gender,
			"nationality": doc.nationality,
			"mobile": doc.student_mobile_number,
			"city": doc.city,
			"address": doc.address_line_1,
		},
		"school": school,
		"exam_number": doc.get("educore_exam_number"),
		"exam_year": doc.get("educore_exam_year"),
		"results": [{"subject": r.subject, "level": r.level, "grade": r.grade, "points": r.points} for r in doc.educore_results],
		"points": doc.get("educore_points"),
		"prior_qualifications": [
			{"qualification": r.qualification, "institution": r.institution, "country": r.country,
			 "nqf_level": r.nqf_level, "year_completed": r.year_completed, "average": r.average}
			for r in doc.get("educore_prior_qualifications") or []
		],
		"previous_student_number": doc.get("educore_previous_student_number"),
		"employment": [
			{"employer": r.employer, "position": r.position, "from_date": str(r.from_date) if r.from_date else None,
			 "to_date": str(r.to_date) if r.to_date else None, "duties": r.duties}
			for r in doc.get("educore_employment") or []
		],
		"work_years": doc.get("educore_work_years"),
		"referees": [
			{"full_name": r.full_name, "position": r.position, "institution": r.institution, "email": r.email, "phone": r.phone}
			for r in doc.get("educore_referees") or []
		],
		"choices": [
			{"rank": c.rank, "offering": c.programme_offering, "program": c.program, "campus": c.campus,
			 "eligibility": c.eligibility, "eligibility_note": c.eligibility_note}
			for c in doc.educore_choices
		],
		"documents": [
			{
				"document_type": d.document_type,
				"required": d.document_type in required,
				"file_url": d.file,
				"file_name": os.path.basename(d.file or ""),
				"certified_on": str(d.certified_on) if d.certified_on else None,
				"certification_problem": _certification_problem(d),
				"status": d.status,
				"rejection_reason": d.rejection_reason,
				"verified_by": d.verified_by,
				"verified_on": str(d.verified_on) if d.verified_on else None,
			}
			for d in doc.educore_documents
		],
		"missing_documents": sorted(required - {d.document_type for d in doc.educore_documents}),
		"fee": {
			"amount": doc.get("educore_fee_amount"),
			"status": doc.get("educore_fee_status"),
			"paid_on": str(doc.educore_fee_paid_on) if doc.get("educore_fee_paid_on") else None,
			"voucher": doc.get("educore_fee_voucher"),
			"bank_transaction": doc.get("educore_fee_bank_transaction"),
			"note": doc.get("educore_fee_note"),
		},
		"offer": _offer(doc),
		"academic_year": doc.academic_year,
		"places": _places(doc),
		"can_review": bool(set(frappe.get_roles()) & set(REVIEW_ROLES)) and doc.has_permission("write"),
		"actions": _actions(doc),
		**_completeness(doc),
	}


def _offer(doc) -> dict | None:
	if not doc.get("educore_offer_status") and not doc.get("educore_offer_conditions"):
		return None
	return {
		"status": doc.get("educore_offer_status"),
		"deadline": str(doc.educore_offer_deadline) if doc.get("educore_offer_deadline") else None,
		"responded_on": str(doc.educore_offer_responded_on) if doc.get("educore_offer_responded_on") else None,
		"conditions": doc.get("educore_offer_conditions"),
		"decline_reason": doc.get("educore_offer_decline_reason"),
	}


@frappe.whitelist(methods=["POST"])
def verify_document(name: str, document_type: str, verdict: str, reason: str | None = None) -> dict:
	"""Verified, or Rejected with a reason the applicant sees (they can then upload it again)"""
	if verdict not in ("Verified", "Rejected"):
		frappe.throw(_("A document is Verified or Rejected"))
	doc = _reviewable(name, write=True)
	if doc.application_status != "Applied":
		frappe.throw(_("Documents are checked while an application is waiting for a decision"))
	row = next((d for d in doc.educore_documents if d.document_type == document_type), None)
	if not row:
		frappe.throw(_("{0} has not uploaded {1}").format(doc.title, document_type))
	if verdict == "Rejected" and not (reason or "").strip():
		frappe.throw(_("Tell the applicant why the document is rejected"))
	row.status = verdict
	row.rejection_reason = reason.strip() if verdict == "Rejected" else None
	row.verified_by = frappe.session.user
	row.verified_on = now_datetime()
	doc.save()
	if verdict == "Rejected":
		notify.send(doc, "document_rejected", document=document_type, reason=row.rejection_reason)
	return review(name)


@frappe.whitelist(methods=["POST"])
def extend_offer(name: str, deadline: str) -> dict:
	"""A later response deadline for an offer still awaiting the applicant's answer"""
	doc = _reviewable(name, write=True)
	offers.extend(doc, deadline)
	return review(name)


@frappe.whitelist(methods=["POST"])
def waive_fee(name: str, reason: str) -> dict:
	"""Finance waives an application's fee, with a reason (educore.admissions.fees.WAIVE_ROLES)"""
	fees.waive(name, reason)
	return dict(zip(("status", "note"), frappe.db.get_value("Student Applicant", name, ["educore_fee_status", "educore_fee_note"])))


# --- paper applications ----------------------------------------------------------------------------------

#: who captures a hard-copy application received at a campus
CAPTURE_ROLES = ("Admissions Officer", "Registrar")


def _require_capture():
	if not set(frappe.get_roles()) & set(CAPTURE_ROLES):
		frappe.throw(_("Only admissions officers and the Registrar capture applications"), frappe.PermissionError)


@frappe.whitelist(methods=["GET"])
def capture_options() -> dict:
	"""The intakes a paper application can be captured for (also after online applications close: forms posted in
	time are still captured)"""
	_require_capture()
	intakes = frappe.get_all(
		"Student Admission",
		filters={"enable_admission_application": 1},
		fields=["name", "title", "academic_year", "admission_end_date"],
		order_by="academic_year desc, admission_end_date desc",
	)
	settings = rules.settings()
	return {
		"intakes": intakes,
		# the fee for a paper form, paid at a campus cashier (Admission Settings)
		"fees": {"local": settings.fee_paper_local, "international": settings.fee_paper_international},
	}


@frappe.whitelist(methods=["POST"])
def capture(data: dict | str) -> dict:
	"""A hard-copy application typed in by staff: the same details and checks as an online one, then submitted.

	It has no applicant login (offers are answered in person) and was checked at the counter, so documents and
	the fee are not asked for online. The email given on the form becomes the student's login on registration.
	It is inserted with the officer's own permissions, so campus User Permissions apply; Frappe's workflow then
	keeps the officer who captured it from approving it themselves."""
	from educore.api.v1 import apply

	_require_capture()
	data = frappe.parse_json(data) if isinstance(data, str) else frappe._dict(data)
	personal = frappe._dict(data.get("personal") or {})

	intake = data.get("intake")
	academic_year = frappe.db.get_value("Student Admission", {"name": intake, "enable_admission_application": 1}, "academic_year") if intake else None
	if not academic_year:
		frappe.throw(_("Choose the intake applied for"))
	for field, label in (("first_name", _("first name")), ("last_name", _("surname")), ("date_of_birth", _("date of birth"))):
		if not (personal.get(field) or "").strip():
			frappe.throw(_("Give the applicant's {0}").format(label))
	email = (data.get("email") or "").strip().lower()
	if not email:
		frappe.throw(_("Give the applicant's email address: it becomes their login when they register"))
	validate_email_address(email, throw=True)
	other = frappe.db.get_value(
		"Student Applicant",
		{"student_email_id": email, "academic_year": academic_year, "application_status": ("not in", ("Rejected", "Declined", "Lapsed"))},
		"name",
	)
	if other:
		frappe.throw(_("{0} already has an application for {1}: {2}").format(email, academic_year, other))
	if not [c for c in data.get("choices") or [] if c]:
		frappe.throw(_("Choose at least one programme"))

	doc = frappe.new_doc("Student Applicant")
	doc.update(
		{
			"student_email_id": email,
			"student_admission": intake,
			"academic_year": academic_year,
			"academic_term": apply._first_term(academic_year),
			"application_date": data.get("received_on") or nowdate(),
		}
	)
	if not data.get("pathway"):
		data["pathway"] = next((p["name"] for p in pathways.active()), None)
	apply.apply_fields(doc, data)
	# the paper fee, paid at the campus cashier: the receipt number, once paid
	doc.educore_fee_amount = fees.fee_for(doc)
	receipt = (data.get("receipt_number") or "").strip()
	doc.educore_fee_status = "Paid" if receipt else "Unpaid"
	if receipt:
		doc.educore_fee_paid_on = doc.application_date
		doc.educore_fee_note = _("Paid at the campus cashier, receipt {0}").format(receipt)
	apply._insert_draft(doc)
	doc.add_comment("Info", _("Paper application captured by {0}").format(frappe.session.user))
	apply_workflow(doc, "Submit")
	return {"name": doc.name}
