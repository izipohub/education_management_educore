"""Application pathways: the routes into the university (docs/architecture/online-applications.md, "Pathways").

A pathway (Admission Pathway) says who it is for, its level (undergraduate or postgraduate), what eligibility is
judged on (its evidence), a minimum age, how many referees and which documents. Every one of those is the
university's to set: EduCore installs the five common routes once, as a starting point, and never changes them
afterwards. Being international is not a pathway: it is the applicant's status (Student Applicant.
educore_international) and changes the identity documents and the fee, on whichever pathway they apply.
"""

import frappe
from frappe import _
from frappe.utils import date_diff, getdate

SCHOOL_RESULTS = "School results"
WORK_EXPERIENCE = "Work experience"
STUDIES_ELSEWHERE = "Studies elsewhere"
STUDIES_HERE = "Studies here"
PRIOR_QUALIFICATION = "Prior qualification"

UNDERGRADUATE, POSTGRADUATE = "Undergraduate", "Postgraduate"

#: document: (guidance, must be certified); the documents the default pathways ask for, only when missing
DEFAULT_DOCUMENTS = {
	"NSSC Statement of Results or Certificate": ("Your latest NSSCO / NSSCAS / NSSCH results.", 1),
	"Foreign School Leaving Certificate": ("Your final school certificate and results, from the country you finished school in.", 1),
	"NQA Evaluation of Foreign Qualifications": ("The Namibia Qualifications Authority's evaluation of your foreign qualifications.", 0),
	"Curriculum Vitae": ("Your work history, with dates.", 0),
	"Proof of Employment": ("A letter from your employer or employers confirming your position and dates.", 0),
	"Motivation Letter": ("One page: why this programme, and what you bring to it.", 0),
	"Academic Record": ("The full academic record (transcript) of your studies after school.", 1),
	"Degree or Diploma Certificate": ("The certificate of your highest qualification.", 1),
	"Course Outlines": ("The outlines of the courses you passed, for the faculty to decide credits.", 0),
}

#: name: settings and documents ((document, asked of, required), ...)
DEFAULT_PATHWAYS = {
	"School leaver": {
		"level": UNDERGRADUATE,
		"evidence": SCHOOL_RESULTS,
		"sort_order": 10,
		"documents": (
			("NSSC Statement of Results or Certificate", "Home applicants", 1),
			("Foreign School Leaving Certificate", "International applicants", 1),
			("NQA Evaluation of Foreign Qualifications", "International applicants", 1),
		),
	},
	"Mature age entry": {
		"level": UNDERGRADUATE,
		"evidence": WORK_EXPERIENCE,
		"min_age": 23,
		"sort_order": 20,
		"description": "Your school results do not meet the requirements, but your work experience does. "
		"An entry test or interview may be required.",
		"documents": (
			("Curriculum Vitae", "Everyone", 1),
			("Proof of Employment", "Everyone", 1),
			("Motivation Letter", "Everyone", 1),
			("NSSC Statement of Results or Certificate", "Home applicants", 0),
		),
	},
	"Advanced standing / transfer": {
		"level": UNDERGRADUATE,
		"evidence": STUDIES_ELSEWHERE,
		"sort_order": 30,
		"description": "You studied at another university or college and want credit for the courses you passed.",
		"documents": (
			("Academic Record", "Everyone", 1),
			("Course Outlines", "Everyone", 0),
			("NSSC Statement of Results or Certificate", "Home applicants", 1),
			("Foreign School Leaving Certificate", "International applicants", 1),
			("NQA Evaluation of Foreign Qualifications", "International applicants", 0),
		),
	},
	"Resumption of studies": {
		"level": UNDERGRADUATE,
		"evidence": STUDIES_HERE,
		"sort_order": 40,
		"description": "You studied here before, stopped, and want to come back.",
		"documents": (("Motivation Letter", "Everyone", 0),),
	},
	"Postgraduate": {
		"level": POSTGRADUATE,
		"evidence": PRIOR_QUALIFICATION,
		"referees_required": 2,
		"sort_order": 50,
		"documents": (
			("Degree or Diploma Certificate", "Everyone", 1),
			("Academic Record", "Everyone", 1),
			("Curriculum Vitae", "Everyone", 1),
			("Motivation Letter", "Everyone", 1),
			("NQA Evaluation of Foreign Qualifications", "International applicants", 1),
		),
	},
}


#: Admission Settings fields added after sites existed: their default, written once if the site never had a value
SETTINGS_DEFAULTS = {
	"home_country": "Namibia",
	"max_choices": 3,
	"approval_needs_verified_documents": 1,
	"approval_needs_fee": 1,
	"offer_response_days": 14,
	"offer_reminder_days": 3,
	"enrolment_needs_acceptance": 1,
	"notify_applicants": 1,
}


def ensure_defaults():
	"""Settings added since a site was set up, and the common routes on a site that has no pathways yet (from
	every migrate; a no-op afterwards). Applications from before pathways become school leavers."""
	stored = set(
		frappe.db.sql_list("select field from `tabSingles` where doctype = 'Admission Settings'")
	)
	for field, value in SETTINGS_DEFAULTS.items():
		if field not in stored:
			frappe.db.set_single_value("Admission Settings", field, value)

	if frappe.db.count("Admission Pathway"):
		return
	for document, (guidance, certified) in DEFAULT_DOCUMENTS.items():
		if not frappe.db.exists("Admission Document Type", document):
			frappe.get_doc(
				{
					"doctype": "Admission Document Type",
					"document_name": document,
					"required_for": "Pathway only",
					"must_be_certified": certified,
					"description": guidance,
				}
			).insert(ignore_permissions=True)
	asked_by_pathways = {d for p in DEFAULT_PATHWAYS.values() for d, _asked, _req in p["documents"]}
	for document in asked_by_pathways:
		# school results were asked of every Namibian applicant before pathways; now only where a pathway asks
		frappe.db.set_value("Admission Document Type", document, "required_for", "Pathway only")

	for name, spec in DEFAULT_PATHWAYS.items():
		frappe.get_doc(
			{
				"doctype": "Admission Pathway",
				"pathway_name": name,
				"level": spec["level"],
				"evidence": spec["evidence"],
				"min_age": spec.get("min_age", 0),
				"referees_required": spec.get("referees_required", 0),
				"sort_order": spec["sort_order"],
				"description": spec.get("description"),
				"documents": [
					{"document_type": d, "applies_to": asked, "required": required}
					for d, asked, required in spec["documents"]
				],
			}
		).insert(ignore_permissions=True)

	if frappe.db.has_column("Student Applicant", "educore_pathway"):
		frappe.db.sql(
			"""update `tabStudent Applicant` set educore_international = 1
			where educore_pathway = 'International'"""
		)
		frappe.db.sql(
			"""update `tabStudent Applicant` set educore_pathway = 'School leaver'
			where ifnull(educore_pathway, '') in ('', 'International')"""
		)


# --- an application's pathway --------------------------------------------------------------------------


def of(doc):
	"""The application's pathway, or None (a paper application captured before pathways)"""
	name = doc.get("educore_pathway")
	return frappe.get_cached_doc("Admission Pathway", name) if name else None


def evidence(doc) -> str:
	pathway = of(doc)
	return pathway.evidence if pathway else SCHOOL_RESULTS


def level(doc) -> str:
	pathway = of(doc)
	return pathway.level if pathway else UNDERGRADUATE


def is_international(doc) -> bool:
	return bool(doc.get("educore_international"))


def age_on_intake(doc) -> int | None:
	"""Age in whole years on 1 January of the intake's academic year"""
	if not doc.get("date_of_birth") or not doc.get("academic_year"):
		return None
	start = frappe.db.get_value("Academic Year", doc.academic_year, "year_start_date")
	if not start:
		return None
	birth, on = getdate(doc.date_of_birth), getdate(f"{getdate(start).year}-01-01")
	return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


def work_years(doc) -> float:
	"""Years of work, overlapping jobs counted once"""
	today = getdate()
	spans = sorted(
		(getdate(row.from_date), getdate(row.to_date) if row.to_date else today)
		for row in doc.get("educore_employment") or []
		if row.from_date
	)
	days, current_start, current_end = 0, None, None
	for start, end in spans:
		if end < start:
			continue
		if current_end is None or start > current_end:
			if current_end is not None:
				days += date_diff(current_end, current_start)
			current_start, current_end = start, end
		else:
			current_end = max(current_end, end)
	if current_end is not None:
		days += date_diff(current_end, current_start)
	return round(days / 365.25, 1)


def check_programme_level(doc, program: str):
	"""A choice must be at the pathway's level: undergraduate pathways cannot choose a master's, and so on"""
	wanted = level(doc)
	actual = frappe.get_cached_value("Program", program, "educore_study_level") or UNDERGRADUATE
	if actual != wanted:
		frappe.throw(
			_("{0} is a {1} programme: apply for it on a {2} pathway").format(program, actual.lower(), actual.lower())
		)


def active() -> list[dict]:
	"""The pathways applicants can choose, in order, with their documents"""
	result = []
	for name in frappe.get_all("Admission Pathway", filters={"active": 1}, pluck="name", order_by="sort_order asc, name asc"):
		pathway = frappe.get_cached_doc("Admission Pathway", name)
		result.append(
			{
				"name": pathway.name,
				"level": pathway.level,
				"evidence": pathway.evidence,
				"min_age": pathway.min_age or 0,
				"referees_required": pathway.referees_required or 0,
				"description": pathway.description,
				"documents": [
					{"document_type": d.document_type, "applies_to": d.applies_to, "required": bool(d.required)}
					for d in pathway.documents
				],
			}
		)
	return result
