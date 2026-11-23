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
from educore.academics.students import copy_particulars
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

#: what each enrolled student wrote on their form: gender, national ID, home language, region, town, next of kin
#: (relationship, name), who pays (and the sponsor)
PARTICULARS = {
	"student1.whk": ("Female", "06041200711", "Oshiwambo", "Omusati", "Outapi", "Mother", "Hileni Amukoto", "Sponsor or bursary", "NSFAF"),
	"student2.whk": ("Male", "05090300422", "Damara/Nama", "Erongo", "Omaruru", "Father", "Johannes Garoeb", "Parent or guardian", None),
	"student1.osh": ("Female", "05112500198", "Oshiwambo", "Oshana", "Ondangwa", "Mother", "Ndeshi Shilongo", "Sponsor or bursary", "NSFAF"),
	"student2.osh": ("Male", "06020800356", "Oshiwambo", "Ohangwena", "Eenhana", "Guardian", "Selma Iiyambo", "Parent or guardian", None),
	"student1.kmp": ("Female", "99070100845", "Afrikaans", "Karas", "Keetmanshoop", "Spouse or partner", "Jacobus Beukes", "Employer", "Karas Regional Council"),
	"student2.kmp": ("Male", "05031700623", "Afrikaans", "Hardap", "Mariental", "Father", "Willem Kooper", "Self", None),
}


def _particulars(login: str) -> dict:
	gender, national_id, language, region, town, relationship, kin, payer, sponsor = PARTICULARS[login]
	number = national_id[-4:]
	return {
		"gender": gender,
		"educore_title": "Ms" if gender == "Female" else "Mr",
		"educore_national_id": national_id,
		"educore_home_language": language,
		"educore_region_of_origin": region,
		"educore_home_town": town,
		"student_mobile_number": f"+26481555{number}",
		"educore_kin_relationship": relationship,
		"educore_kin_name": kin,
		"educore_kin_phone": f"+26481666{number}",
		"educore_fee_payer": payer,
		"educore_fee_payer_name": sponsor,
	}


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
	elif email and not frappe.db.get_value("Student Applicant", existing, "student_email_id"):
		# captured before the paper form asked for an email: as a real form would give it
		frappe.db.set_value("Student Applicant", existing, "student_email_id", email)
	if frappe.db.get_value("Student Applicant", existing, "application_status") == "Draft":
		apply_workflow(frappe.get_doc("Student Applicant", existing), "Submit")
	if approve and frappe.db.get_value("Student Applicant", existing, "application_status") == "Applied":
		apply_workflow(frappe.get_doc("Student Applicant", existing), "Approve")
	return existing


def _paper_email(first: str, last: str) -> str:
	"""The email written on a paper form; it becomes the student's login on registration"""
	return f"{first}.{last}@{DOMAIN}".lower()


def _unreferenced_deposit():
	"""A cash deposit at a branch without the student number, as happens in practice: left for Finance to assign"""
	description = "CASH DEP KEETMANSHOOP BRANCH A BEUKES"
	account = frappe.db.get_single_value("Admission Settings", "fee_bank_account")
	if not account or frappe.db.exists("Bank Transaction", {"description": description}):
		return
	line = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"date": frappe.utils.add_days(frappe.utils.nowdate(), -2),
			"bank_account": account,
			"company": frappe.db.get_value("Bank Account", account, "company"),
			"deposit": 2000,
			"currency": "NAD",
			"description": description,
		}
	).insert(ignore_permissions=True)
	line.submit()


def create():
	_assert_development_site()
	ensure_academic_year(2026)
	ensure_academic_year(2027)

	enrolled = 0
	for login, first, last, offering in ENROLLED:
		email = f"{login}@{DOMAIN}"
		applicant = _applicant(first, last, offering, 2026, email=email, approve=True)
		# their particulars, as on the form (set before the student is made, so they are copied across)
		if not frappe.db.get_value("Student Applicant", applicant, "educore_national_id"):
			frappe.db.set_value("Student Applicant", applicant, _particulars(login), update_modified=False)
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
		if not frappe.db.get_value("Student", student, "educore_national_id"):
			copy_particulars(student)
		enrolled += 1

	_unreferenced_deposit()
	for first, last, offering in APPLICANTS:
		_applicant(first, last, offering, 2027, email=_paper_email(first, last))
	for first, last, offering in OFFERED:
		_applicant(first, last, offering, 2027, email=_paper_email(first, last), approve=True)
	for first, last, offering, reason in REJECTED:
		applicant = _applicant(first, last, offering, 2027, email=_paper_email(first, last))
		if frappe.db.get_value("Student Applicant", applicant, "application_status") == "Applied":
			# the reason is saved first, as on the form: a workflow action reloads the document
			frappe.db.set_value("Student Applicant", applicant, "educore_decision_reason", reason)
			apply_workflow(frappe.get_doc("Student Applicant", applicant), "Reject")

	from educore.setup.demo_finance import invoice_and_pay
	from educore.setup.demo_teaching import create_course_groups

	fees = invoice_and_pay()
	groups = create_course_groups()
	print(f"{groups} course groups created")
	from educore.setup import demo_results

	print(f"{demo_results.create()} mark sheets created")

	from educore.setup.demo_online import create as create_online_application

	for online in create_online_application():
		print(f"online application {online} (see educore.setup.demo_online)")

	from educore.setup.demo_registration import create as create_registration

	create_registration()
	print("2027 registration period open; see educore.setup.demo_registration")
	frappe.db.commit()
	print(
		f"{enrolled} students enrolled for 2026; for 2027: {len(APPLICANTS)} applications pending, "
		f"{len(OFFERED)} offered, {len(REJECTED)} rejected; fees: {fees}"
	)
