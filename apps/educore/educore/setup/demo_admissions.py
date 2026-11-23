"""Online-application setup for EduCore Demo University (development only).

The points scale here is a PLACEHOLDER, flagged as such in Admission Settings: a university loads its own published
scale. The schools are fictional, with "DEMO-" codes: real schools come from the Ministry of Education's register
(EMIS numbers, DNEA centre numbers), never from made-up codes. Called from create_demo_university; re-running adds
what is missing and leaves anything already set alone.
"""

import frappe

#: PLACEHOLDER points per grade (NSSCO A*..G, NSSCAS a..e, NSSCH 1..4); replace with the university's scale
PLACEHOLDER_SCALE = {
	"NSSCO": {"A*": 8, "A": 7, "B": 6, "C": 5, "D": 4, "E": 3, "F": 2, "G": 1},
	"NSSCAS": {"a": 10, "b": 9, "c": 8, "d": 7, "e": 6},
	"NSSCH": {"1": 10, "2": 9, "3": 8, "4": 7},
}

#: subject: counts as (a requirement group)
SUBJECTS = {
	"English": None,  # requirement group only
	"English Second Language": "English",
	"English First Language": "English",
	"Mathematics": None,
	"Physical Science": None,
	"Biology": None,
	"Geography": None,
	"History": None,
	"Accounting": None,
	"Business Studies": None,
	"Economics": None,
	"Computer Studies": None,
	"Development Studies": None,
	"Agriculture": None,
	"Afrikaans First Language": None,
	"Oshindonga First Language": None,
	"Otjiherero First Language": None,
	"German Foreign Language": None,
}

#: programme code: (minimum points, [(subject, level, minimum grade)])
REQUIREMENTS = {
	"BCS": (25, [("English", "NSSCO", "E"), ("Mathematics", "NSSCO", "C")]),
	"DIT": (22, [("English", "NSSCO", "E"), ("Mathematics", "NSSCO", "D")]),
	"BSAMS": (25, [("English", "NSSCO", "E"), ("Mathematics", "NSSCO", "C")]),
	"BACC": (25, [("English", "NSSCO", "E"), ("Mathematics", "NSSCO", "C")]),
	"DAF": (22, [("English", "NSSCO", "E"), ("Mathematics", "NSSCO", "D")]),
	"BBA": (25, [("English", "NSSCO", "E"), ("Mathematics", "NSSCO", "D")]),
	"BEDP": (27, [("English", "NSSCO", "D")]),
	"BNS": (28, [("English", "NSSCO", "D"), ("Biology", "NSSCO", "C")]),
}

#: identity documents: (required for, must be certified, guidance); the evidence documents (school results,
#: academic records ...) come with the pathways (educore.admissions.pathways)
DOCUMENTS = {
	"National ID or Passport": ("All applicants", 1, "Both sides of your Namibian ID card, or your passport's photo page."),
	"Birth Certificate": ("Namibian applicants", 1, "Your full birth certificate."),
	"Study Permit or Visa": ("International applicants", 1, "Or your application for one."),
	"Marriage Certificate": ("Optional", 1, "Only if your surname differs from the one on your school results."),
}

#: fictional schools: name, town, region, ownership, demo centre number
SCHOOLS = [
	("Khomas Demo Secondary School", "Windhoek", "Khomas", "Government", "DEMO-101"),
	("Windhoek Demo High School", "Windhoek", "Khomas", "Private", "DEMO-102"),
	("Oshana Demo High School", "Oshakati", "Oshana", "Government", "DEMO-201"),
	("Ohangwena Demo Secondary School", "Eenhana", "Ohangwena", "Government", "DEMO-202"),
	("ǁKaras Demo Secondary School", "Keetmanshoop", "ǁKaras", "Government", "DEMO-301"),
	("Erongo Demo College", "Swakopmund", "Erongo", "Private", "DEMO-401"),
]

INTAKE = "2027 Intake"

#: a fictional bank and account for the fee, shown to applicants as EFT details
DEMO_BANK = "Demo Commercial Bank"
DEMO_ACCOUNT_NUMBER = "DEMO-62-0000-0001"


def _fee_bank_account():
	from educore.finance.student_fees import CENTRAL_BANK, ensure_fee_setup

	company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company")
	if not company:
		return
	ensure_fee_setup(company)
	if not frappe.db.exists("Bank", DEMO_BANK):
		frappe.get_doc({"doctype": "Bank", "bank_name": DEMO_BANK}).insert(ignore_permissions=True)
	abbr = frappe.get_cached_value("Company", company, "abbr")
	account = frappe.db.get_value("Bank Account", {"account": f"{CENTRAL_BANK} - {abbr}"})
	if not account:
		account = (
			frappe.get_doc(
				{
					"doctype": "Bank Account",
					"account_name": "University Main Account",
					"bank": DEMO_BANK,
					"account": f"{CENTRAL_BANK} - {abbr}",
					"is_company_account": 1,
					"company": company,
					"bank_account_no": DEMO_ACCOUNT_NUMBER,
					"branch_code": "DEMO-000",
				}
			)
			.insert(ignore_permissions=True)
			.name
		)
	settings = frappe.get_single("Admission Settings")
	if not settings.fee_bank_account:
		# applicants are shown this ERPNext account's bank, number and branch (educore.admissions.fees.bank_details)
		settings.fee_bank_account = account
		settings.fee_namibian = settings.fee_namibian or 150
		settings.fee_international = settings.fee_international or 300
		settings.fee_paper_local = settings.fee_paper_local or 200
		settings.fee_paper_international = settings.fee_paper_international or 350
		settings.save(ignore_permissions=True)


def create_admissions_setup():
	for subject, counts_as in SUBJECTS.items():
		if not frappe.db.exists("School Subject", subject):
			frappe.get_doc(
				{"doctype": "School Subject", "subject_name": subject, "requirement_only": int(subject == "English")}
			).insert(ignore_permissions=True)
	for subject, counts_as in SUBJECTS.items():
		if counts_as and not frappe.db.get_value("School Subject", subject, "counts_as"):
			frappe.db.set_value("School Subject", subject, "counts_as", counts_as)

	settings = frappe.get_single("Admission Settings")
	if not settings.points_scale:
		for level, grades in PLACEHOLDER_SCALE.items():
			for grade, points in grades.items():
				settings.append("points_scale", {"level": level, "grade": grade, "points": points})
		settings.scale_is_placeholder = 1
		settings.best_subjects = 5
		settings.certification_max_age_months = 3
		settings.max_file_size_mb = 5
		settings.save(ignore_permissions=True)

	_fee_bank_account()

	for name, (required_for, certified, guidance) in DOCUMENTS.items():
		if not frappe.db.exists("Admission Document Type", name):
			frappe.get_doc(
				{
					"doctype": "Admission Document Type",
					"document_name": name,
					"required_for": required_for,
					"must_be_certified": certified,
					"description": guidance,
				}
			).insert(ignore_permissions=True)

	for name, town, region, ownership, centre in SCHOOLS:
		if not frappe.db.exists("Secondary School", {"centre_number": centre}):
			frappe.get_doc(
				{
					"doctype": "Secondary School",
					"school_name": name,
					"town": town,
					"region": region,
					"ownership": ownership,
					"centre_number": centre,
					"emis_number": centre.replace("DEMO-", "DEMO-EMIS-"),
				}
			).insert(ignore_permissions=True)

	for code, (min_points, requirements) in REQUIREMENTS.items():
		program = frappe.db.get_value("Program", {"educore_programme_code": code})
		if not program:
			continue
		doc = frappe.get_doc("Program", program)
		if doc.get("educore_min_points"):
			continue
		doc.educore_min_points = min_points
		for subject, level, grade in requirements:
			doc.append("educore_subject_requirements", {"subject": subject, "level": level, "grade": grade})
		doc.save(ignore_permissions=True)

	if frappe.db.exists("Student Admission", INTAKE):
		# programmes added after the intake was created (e.g. the MBA)
		intake = frappe.get_doc("Student Admission", INTAKE)
		listed = {row.program for row in intake.program_details}
		for program in frappe.get_all("Program", filters={"educore_programme_code": ("is", "set")}, pluck="name"):
			if program not in listed:
				intake.append("program_details", {"program": program, "application_fee": 150, "min_age": 16})
		if len(intake.program_details) > len(listed):
			intake.save(ignore_permissions=True)
	else:
		frappe.get_doc(
			{
				"doctype": "Student Admission",
				"title": INTAKE,
				"academic_year": "2027",
				"admission_start_date": "2026-05-22",
				"admission_end_date": "2027-01-31",
				"published": 1,
				"enable_admission_application": 1,
				"program_details": [
					{"program": p, "application_fee": 150, "min_age": 16}
					for p in frappe.get_all("Program", filters={"educore_programme_code": ("is", "set")}, pluck="name")
				],
			}
		).insert(ignore_permissions=True)
