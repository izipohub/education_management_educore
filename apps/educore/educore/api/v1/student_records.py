"""Student records, for the registry: the list of students and one student's record.

Reads go through frappe.get_list and the student's own read permission, so campus and faculty User Permissions
apply: a Windhoek registry officer sees Windhoek's students only. Nothing here writes.
"""

import frappe
from frappe import _
from frappe.utils import flt

from educore.api.v1.apply import PERSONAL_FIELDS
from educore.registration import rules as registration_rules

#: who opens student records in the app
RECORD_ROLES = (
	"Registrar",
	"Registry Officer",
	"Faculty Officer",
	"Dean",
	"Head of Department",
	"Campus Director",
	"Executive Management",
	"System Manager",
)


def _require_records_role():
	if not set(frappe.get_roles()) & set(RECORD_ROLES):
		frappe.throw(_("Student records are for the registry and faculty offices"), frappe.PermissionError)


def _latest_enrolment(student: str) -> dict | None:
	return frappe.db.get_value(
		"Program Enrollment",
		{"student": student, "docstatus": 1},
		["name", "program", "educore_programme_offering as offering", "academic_year", "educore_year_of_study as year_of_study"],
		as_dict=True,
		order_by="academic_year desc, enrollment_date desc",
	)


def _owing(student: str) -> float:
	return flt(
		frappe.db.sql(
			"select sum(outstanding_amount) from `tabSales Invoice` where docstatus = 1 and student = %s", student
		)[0][0]
	)


@frappe.whitelist(methods=["GET"])
def students(
	search: str | None = None,
	campus: str | None = None,
	program: str | None = None,
	standing: str | None = None,
	status: str = "Active",
) -> dict:
	"""The students this user may see, newest first, with their programme, year and what they owe"""
	_require_records_role()
	filters = {"enabled": 1 if status == "Active" else 0}
	if campus:
		filters["campus"] = campus
	if standing:
		filters["educore_academic_standing"] = standing
	or_filters = None
	if search:
		like = f"%{search.strip()}%"
		or_filters = [["student_name", "like", like], ["name", "like", like], ["educore_national_id", "like", like]]
	rows = frappe.get_list(
		"Student",
		filters=filters,
		or_filters=or_filters,
		fields=["name", "student_name", "campus", "student_email_id", "educore_academic_standing as standing", "joining_date"],
		order_by="joining_date desc, name desc",
		limit=500,
	)
	out = []
	for row in rows:
		enrolment = _latest_enrolment(row.name) or {}
		if program and enrolment.get("program") != program:
			continue
		out.append({**row, **{k: enrolment.get(k) for k in ("program", "offering", "academic_year", "year_of_study")}, "owing": _owing(row.name)})
	return {
		"rows": out,
		"campuses": frappe.get_list("Campus", pluck="name", order_by="name asc", limit=0),
		"programmes": frappe.get_all("Program", filters={"educore_programme_code": ("is", "set")}, pluck="name", order_by="name asc"),
		"standings": [o for o in (frappe.get_meta("Student").get_field("educore_academic_standing").options or "").split("\n") if o],
	}


@frappe.whitelist(methods=["GET"])
def student(name: str) -> dict:
	"""One student's record: who they are, their next of kin, every year's registration, fees and documents"""
	_require_records_role()
	doc = frappe.get_doc("Student", name)
	doc.check_permission("read")  # campus and faculty scope

	enrolments = []
	for pe in frappe.get_all(
		"Program Enrollment",
		filters={"student": name, "docstatus": ("<", 2)},
		fields=[
			"name", "program", "educore_programme_offering as offering", "campus", "academic_year",
			"educore_year_of_study as year_of_study", "enrollment_date", "docstatus",
			"educore_registration_status as registration_status",
		],
		order_by="academic_year desc, enrollment_date desc",
	):
		when = registration_rules.semesters(pe.program)
		courses = sorted(
			(
				{"course": c.course, "course_name": c.course_name, "credits": registration_rules.credits(c.course), "semester": when.get(c.course, "Year")}
				for c in frappe.get_doc("Program Enrollment", pe.name).courses
			),
			key=lambda c: (registration_rules.SEMESTER_ORDER.get(c["semester"], 9), c["course_name"]),
		)
		enrolments.append({
			**pe,
			"status": "Registered" if pe.docstatus == 1 else (pe.registration_status or "Draft"),
			"courses": courses,
			"credits": sum(c["credits"] for c in courses),
		})

	invoices = frappe.get_all(
		"Sales Invoice",
		filters={"student": name, "docstatus": 1},
		fields=["name", "posting_date", "grand_total", "outstanding_amount", "status"],
		order_by="posting_date desc",
	)
	documents = []
	if doc.student_applicant:
		documents = [
			{"document_type": d.document_type, "status": d.status, "file_url": d.file}
			for d in frappe.get_doc("Student Applicant", doc.student_applicant).get("educore_documents") or []
		]
	guardians = []
	for row in doc.guardians:
		g = frappe.db.get_value("Guardian", row.guardian, ["mobile_number", "email_address", "work_address"], as_dict=True) or {}
		guardians.append({"name": row.guardian_name, "relation": row.relation, "phone": g.get("mobile_number"), "email": g.get("email_address"), "address": g.get("work_address")})

	return {
		"name": doc.name,
		"student_name": doc.student_name,
		"enabled": bool(doc.enabled),
		"campus": doc.get("campus"),
		"joining_date": str(doc.joining_date) if doc.joining_date else None,
		"application": doc.student_applicant,
		"login": doc.user,
		"standing": doc.get("educore_academic_standing"),
		"standing_note": doc.get("educore_standing_note"),
		"personal": {
			"email": doc.student_email_id,
			"mobile": doc.student_mobile_number,
			"date_of_birth": str(doc.date_of_birth) if doc.date_of_birth else None,
			"gender": doc.gender,
			"nationality": doc.nationality,
			"address": doc.address_line_1,
			"city": doc.city,
		},
		"particulars": {
			field: str(doc.get(field)) if field == "educore_passport_expiry" and doc.get(field) else doc.get(field)
			for field in PERSONAL_FIELDS
			if field.startswith("educore_")
		},
		"guardians": guardians,
		"enrolments": enrolments,
		"invoices": invoices,
		"owing": flt(sum(flt(i.outstanding_amount) for i in invoices), 2),
		"documents": documents,
	}
