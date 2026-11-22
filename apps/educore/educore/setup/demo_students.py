"""Demo students and applicants for EduCore Demo University (development only).

    bench --site educore.localhost execute educore.setup.demo_students.create

Run after create_demo_university and the test users (educore.access.test_users). It goes through the real
flow, so it also exercises it: application on an offering → approved → Education's enroll_student →
Program Enrollment submitted for 2026. Each enrolled student is linked to its test login
(student1.whk@…). Pending applications for the 2027 intake give the admissions officers work.
Re-running adds whatever is missing.
"""

import frappe
from education.education.api import enroll_student
from frappe.model.workflow import apply_workflow

from educore.academics.calendar import ensure_academic_year, term
from educore.access.demo_users import DOMAIN, _assert_development_site

#: login, first name, last name, offering: enrolled in 2026
ENROLLED = [
	("student1.whk", "Ndapewa", "Amukoto", "BCS-WHK-FT"),
	("student2.whk", "Lukas", "Garoeb", "BNS-WHK-FT"),
	("student1.osh", "Martha", "Shilongo", "BCS-OSH-FT"),
	("student2.osh", "Tangeni", "Iiyambo", "BEDP-OSH-FT"),
	("student1.kmp", "Anna", "Beukes", "BACC-KMP-PT"),
	("student2.kmp", "Petrus", "Kooper", "DAF-KMP-FT"),
]

#: first name, last name, offering: applied for 2027, not yet decided
APPLICANTS = [
	("Selma", "Nghifikwa", "BCS-WHK-FT"),
	("Johannes", "Swartbooi", "BSAMS-WHK-FT"),
	("Hilma", "Nakale", "DIT-OSH-FT"),
	("Elias", "Haimbodi", "BACC-OSH-FT"),
	("Rosalia", "Fredericks", "BBA-KMP-PT"),
	("David", "Isaacs", "BACC-KMP-PT"),
]


#: approved for 2027, not yet enrolled. BSAMS-WHK-FT has 2 places, so these fill it and approving
#: Johannes Swartbooi (pending, above) is refused: the capacity rule, to try by hand
OFFERED = [
	("Maria", "Kandjii", "BSAMS-WHK-FT"),
	("Simon", "Hango", "BSAMS-WHK-FT"),
]

#: rejected for 2027, with the reason
REJECTED = [
	("Frieda", "Mbango", "DIT-OSH-FT", "Does not meet the minimum entry requirement in Mathematics."),
]


def _applicant(first, last, offering, year, email=None, approve=False):
	"""A paper application captured by staff: created as a Draft and submitted (the workflow's Submit);
	approve=True also takes the workflow's Approve action"""
	existing = frappe.db.get_value("Student Applicant", {"first_name": first, "last_name": last})
	if not existing:
		existing = (
			frappe.get_doc(
				{
					"doctype": "Student Applicant",
					"first_name": first,
					"last_name": last,
					"educore_programme_offering": offering,
					"academic_year": str(year),
					"academic_term": term(year, "Semester 1"),
					"application_date": f"{year - 1}-09-15",
					"student_email_id": email,
					"nationality": "Namibian",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	if frappe.db.get_value("Student Applicant", existing, "application_status") == "Draft":
		apply_workflow(frappe.get_doc("Student Applicant", existing), "Submit")
	if approve and frappe.db.get_value("Student Applicant", existing, "application_status") == "Applied":
		apply_workflow(frappe.get_doc("Student Applicant", existing), "Approve")
	return existing


def create():
	_assert_development_site()
	ensure_academic_year(2026)
	ensure_academic_year(2027)

	enrolled = 0
	for login, first, last, offering in ENROLLED:
		email = f"{login}@{DOMAIN}"
		applicant = _applicant(first, last, offering, 2026, email=email, approve=True)
		student = frappe.db.get_value("Student", {"student_applicant": applicant})
		if not student:
			enrollment = enroll_student(applicant)
			enrollment.enrollment_date = "2026-02-02"
			enrollment.save(ignore_permissions=True)
			enrollment.submit()
			student = enrollment.student
		if frappe.db.exists("User", email) and not frappe.db.get_value("Student", student, "user"):
			frappe.db.set_value("Student", student, "user", email)
		# the test login carries the student's own name, as a real student's login does
		if frappe.db.exists("User", email) and frappe.db.get_value("User", email, "first_name") != first:
			user = frappe.get_doc("User", email)
			user.first_name, user.last_name = first, last
			user.save(ignore_permissions=True)
		enrolled += 1

	for first, last, offering in APPLICANTS:
		_applicant(first, last, offering, 2027)
	for first, last, offering in OFFERED:
		_applicant(first, last, offering, 2027, approve=True)
	for first, last, offering, reason in REJECTED:
		applicant = _applicant(first, last, offering, 2027)
		if frappe.db.get_value("Student Applicant", applicant, "application_status") == "Applied":
			# the reason is saved first, as on the form: a workflow action reloads the document
			frappe.db.set_value("Student Applicant", applicant, "educore_decision_reason", reason)
			apply_workflow(frappe.get_doc("Student Applicant", applicant), "Reject")

	from educore.setup.demo_finance import invoice_and_pay
	from educore.setup.demo_teaching import create_course_groups

	fees = invoice_and_pay()
	groups = create_course_groups()
	print(f"{groups} course groups created")

	from educore.setup.demo_online import create as create_online_application

	for online in create_online_application():
		print(f"online application {online} (see educore.setup.demo_online)")
	frappe.db.commit()
	print(
		f"{enrolled} students enrolled for 2026; for 2027: {len(APPLICANTS)} applications pending, "
		f"{len(OFFERED)} offered, {len(REJECTED)} rejected; fees: {fees}"
	)
