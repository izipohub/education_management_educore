"""Enrolment of admitted applicants, for the Vue app's registry screen.

An approved applicant becomes a student through Education's own enroll_student (Student, then Program
Enrollment), submitted here; submitting invoices the year's fees (educore.finance.student_fees). Reads go
through frappe.get_list, so each registry officer sees only their campus.
"""

import frappe
from education.education.api import enroll_student
from frappe import _
from frappe.utils import getdate, nowdate, validate_email_address

from educore.admissions import offers
from educore.finance.student_fees import fee_structure_for

FIELDS = [
	"name",
	"title",
	"first_name",
	"last_name",
	"student_email_id as email",
	"educore_programme_offering as offering",
	"program",
	"campus",
	"educore_mode_of_study as mode_of_study",
	"academic_year",
	"academic_term",
	"application_status as status",
	"educore_decided_on as decided_on",
	"educore_applicant_user as applicant_user",
	"educore_offer_status as offer_status",
	"educore_offer_deadline as offer_deadline",
]


def _default_enrollment_date(academic_term: str | None) -> str:
	"""The first term's start, or today once that has passed"""
	start = frappe.db.get_value("Academic Term", academic_term, "term_start_date") if academic_term else None
	today = getdate(nowdate())
	return str(max(getdate(start), today) if start else today)


def _offer_row(row) -> dict:
	row = dict(row)
	row["applicant"] = row.get("title") or " ".join(p for p in (row.get("first_name"), row.get("last_name")) if p)
	structure = fee_structure_for(row["offering"], row["academic_year"]) if row.get("offering") else None
	row["fees"] = frappe.db.get_value("Fee Structure", structure, "total_amount") if structure else None
	row["enrollment_date"] = _default_enrollment_date(row.get("academic_term"))
	row["online"] = bool(row.pop("applicant_user", None))
	# online offers are enrolled once accepted, when the university says so (Admission Settings)
	row["needs_acceptance"] = row["online"] and _needs_acceptance() and row.get("offer_status") != offers.ACCEPTED
	return row


def _needs_acceptance() -> bool:
	return bool(frappe.get_cached_doc("Admission Settings").enrolment_needs_acceptance)


def _admitted_row(row) -> dict:
	row = dict(row)
	row.pop("applicant_user", None)
	row["applicant"] = row.get("title") or " ".join(p for p in (row.get("first_name"), row.get("last_name")) if p)
	student = frappe.db.get_value("Student", {"student_applicant": row["name"]}, ["name", "user"], as_dict=True)
	row["student"] = student.name if student else None
	row["student_login"] = student.user if student else None
	enrollment = (
		frappe.db.get_value(
			"Program Enrollment",
			{"student": student.name, "docstatus": 1},
			["name", "enrollment_date"],
			as_dict=True,
			order_by="enrollment_date desc",
		)
		if student
		else None
	)
	row["enrollment"] = enrollment.name if enrollment else None
	row["enrollment_date"] = str(enrollment.enrollment_date) if enrollment else None
	invoice = (
		frappe.db.get_value(
			"Sales Invoice",
			{"educore_program_enrollment": enrollment.name, "docstatus": 1},
			["name", "grand_total", "outstanding_amount", "status"],
			as_dict=True,
		)
		if enrollment
		else None
	)
	row["invoice"] = dict(invoice) if invoice else None
	return row


#: Enrolment is registry work; admissions officers also hold Academics User, but decide on applications only
ENROL_ROLES = ("Registry Officer", "Registrar", "System Manager")


def can_enrol() -> bool:
	return (
		bool(set(frappe.get_roles()) & set(ENROL_ROLES))
		and frappe.has_permission("Student", "create")
		and frappe.has_permission("Program Enrollment", "submit")
	)


@frappe.whitelist(methods=["GET"])
def enrolments(academic_year: str | None = None, search: str | None = None) -> dict:
	"""Offers waiting to be enrolled (Approved) and those already enrolled (Admitted)"""
	years = sorted(set(frappe.get_list("Student Applicant", pluck="academic_year", distinct=True, limit=0)), reverse=True)
	academic_year = academic_year or (years[0] if years else None)
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [["first_name", "like", like], ["last_name", "like", like], ["name", "like", like]]

	def rows(status):
		filters = {"application_status": status}
		if academic_year:
			filters["academic_year"] = academic_year
		return frappe.get_list(
			"Student Applicant",
			filters=filters,
			or_filters=or_filters,
			fields=FIELDS,
			order_by="educore_decided_on asc, name asc",
			limit=500,
		)

	return {
		"academic_year": academic_year,
		"academic_years": years,
		"can_enrol": can_enrol(),
		"waiting": [_offer_row(r) for r in rows("Approved")],
		"enrolled": [_admitted_row(r) for r in rows("Admitted")],
	}


@frappe.whitelist(methods=["POST"])
def enrol(name: str, email: str | None = None, enrollment_date: str | None = None) -> dict:
	"""Make an approved applicant a student: Student record, login, enrolment and the year's fees"""
	applicant = frappe.get_doc("Student Applicant", name)
	# campus scope (User Permissions) and the right to enrol, before anything is written
	applicant.check_permission("read")
	if not can_enrol():
		frappe.throw(_("You are not allowed to enrol students"), frappe.PermissionError)
	if applicant.application_status != "Approved":
		frappe.throw(_("{0} is {1}: only an approved applicant can be enrolled").format(name, applicant.application_status))
	if offers.needs_acceptance(applicant):
		frappe.throw(_("{0} has not accepted the offer yet").format(applicant.title))

	email = (email or "").strip().lower() or applicant.student_email_id
	if not email:
		frappe.throw(_("Give the student's email address: it becomes their login"))
	validate_email_address(email, throw=True)
	existing_student = frappe.db.get_value("Student", {"student_email_id": email})
	if existing_student:
		frappe.throw(_("{0} is already the email of student {1}").format(email, existing_student))
	if email != applicant.student_email_id:
		applicant.db_set("student_email_id", email)

	enrollment = enroll_student(name)
	enrollment.enrollment_date = enrollment_date or _default_enrollment_date(applicant.academic_term)
	enrollment.save()
	enrollment.submit()

	row = frappe.get_list("Student Applicant", filters={"name": name}, fields=FIELDS, limit=1)[0]
	return _admitted_row(row)
