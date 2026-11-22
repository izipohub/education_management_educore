"""EduCore's fields on upstream DocTypes, created after install and every migrate.

Faculties, schools and departments are nodes of ERPNext's Department tree, the one Education's Program and
Course and HR's Employee already link to (AGENT.md 5.1.1): University units → Faculty / School → Academic
Department. EduCore adds what that tree lacks: the kind of unit, a short code, and the campuses it works on.
"""

from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

UNIT_TYPES = ("Faculty", "School", "Academic Department", "Administrative Division", "Support Unit")
#: Units that own programmes and courses
ACADEMIC_UNIT_TYPES = ("Faculty", "School", "Academic Department")
QUALIFICATION_TYPES = (
	"Certificate",
	"Diploma",
	"Bachelor's Degree",
	"Honours Degree",
	"Postgraduate Diploma",
	"Master's Degree",
	"Doctoral Degree",
)
#: Unit types that hold other units, and the types each may sit under
GROUP_UNIT_TYPES = ("Faculty", "School", "Administrative Division")
ALLOWED_PARENTS = {
	"Faculty": ("",),
	"School": ("", "Faculty"),
	"Academic Department": ("Faculty", "School"),
	"Administrative Division": ("",),
	"Support Unit": ("", "Administrative Division"),
}

CUSTOM_FIELDS = {
	"Department": [
		{
			"fieldname": "educore_unit_type",
			"label": "Unit Type",
			"fieldtype": "Select",
			"options": "\n" + "\n".join(UNIT_TYPES),
			"insert_after": "department_name",
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Faculties and schools hold academic departments; divisions hold support units.",
		},
		{
			"fieldname": "educore_unit_code",
			"label": "Unit Code",
			"fieldtype": "Data",
			"length": 12,
			"insert_after": "educore_unit_type",
			"unique": 1,
			"description": "Short code, e.g. FST for the Faculty of Science and Technology.",
		},
		{
			"fieldname": "educore_campuses",
			"label": "Campuses",
			"fieldtype": "Table MultiSelect",
			"options": "Unit Campus",
			"insert_after": "educore_unit_code",
			"description": "Campuses this unit works on. A faculty may span several campuses.",
		},
	],
	# Programmes: university-wide; which campus runs them, and how, is a Programme Offering
	"Program": [
		{
			"fieldname": "educore_programme_code",
			"label": "Programme Code",
			"fieldtype": "Data",
			"length": 12,
			"unique": 1,
			"insert_after": "program_abbreviation",
			"in_list_view": 1,
			"description": "e.g. BCS. Used in offering and student records; keep it stable.",
		},
		{
			"fieldname": "educore_qualification_section",
			"label": "Qualification",
			"fieldtype": "Section Break",
			"insert_after": "educore_programme_code",
		},
		{
			"fieldname": "educore_qualification_type",
			"label": "Qualification Type",
			"fieldtype": "Select",
			"options": "\n" + "\n".join(QUALIFICATION_TYPES),
			"insert_after": "educore_qualification_section",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "educore_nqf_level",
			"label": "NQF Level",
			"fieldtype": "Int",
			"insert_after": "educore_qualification_type",
			"description": "Namibian Qualifications Framework level, 1 to 10.",
		},
		{
			"fieldname": "educore_qualification_column",
			"fieldtype": "Column Break",
			"insert_after": "educore_nqf_level",
		},
		{
			"fieldname": "educore_credits",
			"label": "Total Credits",
			"fieldtype": "Int",
			"insert_after": "educore_qualification_column",
		},
		{
			"fieldname": "educore_duration_years",
			"label": "Minimum Duration (Years)",
			"fieldtype": "Float",
			"precision": "1",
			"insert_after": "educore_credits",
			"description": "Full-time. Part-time and distance offerings may take longer.",
		},
		{
			"fieldname": "educore_entry_section",
			"label": "Entry Requirements",
			"fieldtype": "Section Break",
			"insert_after": "educore_duration_years",
		},
		{
			"fieldname": "educore_min_points",
			"label": "Minimum Points",
			"fieldtype": "Int",
			"insert_after": "educore_entry_section",
			"description": "On the university's points scale (Admission Settings), over the best subjects counted.",
		},
		{
			"fieldname": "educore_subject_requirements",
			"label": "Subject Requirements",
			"fieldtype": "Table",
			"options": "Programme Subject Requirement",
			"insert_after": "educore_min_points",
		},
	],
	"Course": [
		{
			"fieldname": "educore_course_code",
			"label": "Course Code",
			"fieldtype": "Data",
			"length": 12,
			"unique": 1,
			"insert_after": "course_name",
			"in_list_view": 1,
			"description": "e.g. CMP1511.",
		},
		{
			"fieldname": "educore_credits",
			"label": "Credits",
			"fieldtype": "Int",
			"insert_after": "department",
			"in_list_view": 1,
		},
		{
			"fieldname": "educore_nqf_level",
			"label": "NQF Level",
			"fieldtype": "Int",
			"insert_after": "educore_credits",
		},
	],
	# Admissions: an applicant applies for an offering (programme + campus + mode), not just a programme
	"Student Applicant": [
		{
			"fieldname": "educore_programme_offering",
			"label": "Programme Offering",
			"fieldtype": "Link",
			"options": "Programme Offering",
			"insert_after": "program",
			"in_list_view": 1,
			"description": "The programme at a campus, in a mode of study. Sets the programme.",
		},
		{
			"fieldname": "campus",
			"label": "Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"fetch_from": "educore_programme_offering.campus",
			"read_only": 1,
			"insert_after": "educore_programme_offering",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "educore_mode_of_study",
			"label": "Mode of Study",
			"fieldtype": "Data",
			"fetch_from": "educore_programme_offering.mode_of_study",
			"read_only": 1,
			"insert_after": "campus",
		},
		{
			"fieldname": "educore_decision_section",
			"label": "Admission Decision",
			"fieldtype": "Section Break",
			"insert_after": "educore_mode_of_study",
			"collapsible": 1,
		},
		{
			"fieldname": "educore_decision_reason",
			"label": "Decision Notes",
			"fieldtype": "Small Text",
			"insert_after": "educore_decision_section",
			"description": "Required to reject an application or withdraw an offer.",
		},
		{
			"fieldname": "educore_decision_column",
			"fieldtype": "Column Break",
			"insert_after": "educore_decision_reason",
		},
		{
			"fieldname": "educore_decided_by",
			"label": "Decided By",
			"fieldtype": "Link",
			"options": "User",
			"read_only": 1,
			"insert_after": "educore_decision_column",
		},
		{
			"fieldname": "educore_decided_on",
			"label": "Decided On",
			"fieldtype": "Datetime",
			"read_only": 1,
			"insert_after": "educore_decided_by",
		},
		# the online application (educore/admissions/application.py)
		{
			"fieldname": "educore_application_section",
			"label": "Online Application",
			"fieldtype": "Section Break",
			"insert_after": "educore_decided_on",
		},
		{
			"fieldname": "educore_applicant_user",
			"label": "Applicant's Login",
			"fieldtype": "Link",
			"options": "User",
			"read_only": 1,
			"insert_after": "educore_application_section",
		},
		{
			"fieldname": "educore_pathway",
			"label": "Pathway",
			"fieldtype": "Select",
			"options": "School leaver\nInternational",
			"default": "School leaver",
			"insert_after": "educore_applicant_user",
		},
		{
			"fieldname": "educore_submitted_on",
			"label": "Submitted On",
			"fieldtype": "Datetime",
			"read_only": 1,
			"insert_after": "educore_pathway",
		},
		{
			"fieldname": "educore_declaration",
			"label": "Declaration Accepted",
			"fieldtype": "Check",
			"read_only": 1,
			"insert_after": "educore_submitted_on",
			"description": "The applicant declared the information true and complete (their electronic signature).",
		},
		{
			"fieldname": "educore_choices",
			"label": "Programme Choices",
			"fieldtype": "Table",
			"options": "Applicant Choice",
			"insert_after": "educore_declaration",
		},
		{
			"fieldname": "educore_school_section",
			"label": "School and Results",
			"fieldtype": "Section Break",
			"insert_after": "educore_choices",
		},
		{
			"fieldname": "educore_secondary_school",
			"label": "Secondary School",
			"fieldtype": "Link",
			"options": "Secondary School",
			"insert_after": "educore_school_section",
		},
		{
			"fieldname": "educore_exam_number",
			"label": "Examination Number",
			"fieldtype": "Data",
			"insert_after": "educore_secondary_school",
		},
		{
			"fieldname": "educore_exam_year",
			"label": "Examination Year",
			"fieldtype": "Int",
			"insert_after": "educore_exam_number",
		},
		{
			"fieldname": "educore_points",
			"label": "Points",
			"fieldtype": "Int",
			"read_only": 1,
			"insert_after": "educore_exam_year",
			"in_list_view": 1,
		},
		{
			"fieldname": "educore_results",
			"label": "School Results",
			"fieldtype": "Table",
			"options": "Applicant School Result",
			"insert_after": "educore_points",
		},
		{
			"fieldname": "educore_documents_section",
			"label": "Documents",
			"fieldtype": "Section Break",
			"insert_after": "educore_results",
		},
		{
			"fieldname": "educore_documents",
			"label": "Documents",
			"fieldtype": "Table",
			"options": "Applicant Document",
			"insert_after": "educore_documents_section",
		},
	],
	"Student": [
		{
			"fieldname": "campus",
			"label": "Home Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"insert_after": "student_applicant",
			"in_standard_filter": 1,
			"description": "From the application; the campus responsible for the student's records.",
		},
		{
			"fieldname": "department",
			"label": "Faculty / Department",
			"fieldtype": "Link",
			"options": "Department",
			"read_only": 1,
			"insert_after": "campus",
			"in_standard_filter": 1,
			"description": "Of the student's current programme, from their latest enrolment.",
		},
	],
	# Each year's enrolment: on an offering, so campus and faculty users see their own students
	"Program Enrollment": [
		{
			"fieldname": "educore_programme_offering",
			"label": "Programme Offering",
			"fieldtype": "Link",
			"options": "Programme Offering",
			"insert_after": "program",
			"in_list_view": 1,
		},
		{
			"fieldname": "campus",
			"label": "Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"fetch_from": "educore_programme_offering.campus",
			"read_only": 1,
			"insert_after": "educore_programme_offering",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "educore_mode_of_study",
			"label": "Mode of Study",
			"fieldtype": "Data",
			"fetch_from": "educore_programme_offering.mode_of_study",
			"read_only": 1,
			"insert_after": "campus",
		},
		{
			"fieldname": "department",
			"label": "Faculty / Department",
			"fieldtype": "Link",
			"options": "Department",
			"fetch_from": "educore_programme_offering.department",
			"read_only": 1,
			"insert_after": "educore_mode_of_study",
		},
	],
	# Student fees: per offering, invoiced to the campus cost center (educore/finance/student_fees.py)
	"Fee Structure": [
		{
			"fieldname": "educore_programme_offering",
			"label": "Programme Offering",
			"fieldtype": "Link",
			"options": "Programme Offering",
			"insert_after": "program",
			"in_list_view": 1,
			"description": "Fees differ by campus and mode of study. Sets the programme and cost center.",
		},
		{
			"fieldname": "campus",
			"label": "Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"fetch_from": "educore_programme_offering.campus",
			"read_only": 1,
			"insert_after": "educore_programme_offering",
			"in_standard_filter": 1,
		},
	],
	"Sales Invoice": [
		{
			"fieldname": "campus",
			"label": "Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"read_only": 1,
			"insert_after": "student",
			"in_standard_filter": 1,
		},
		{
			"fieldname": "educore_program_enrollment",
			"label": "Program Enrollment",
			"fieldtype": "Link",
			"options": "Program Enrollment",
			"read_only": 1,
			"insert_after": "campus",
		},
		{
			"fieldname": "educore_fee_structure",
			"label": "Fee Structure",
			"fieldtype": "Link",
			"options": "Fee Structure",
			"read_only": 1,
			"insert_after": "educore_program_enrollment",
		},
	],
	"Payment Entry": [
		{
			"fieldname": "campus",
			"label": "Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"insert_after": "party_name",
			"in_standard_filter": 1,
			"description": "From the invoice paid: collections are reported per campus.",
		},
	],
	# Course groups: taught on a campus; campus users see their campus's groups
	"Student Group": [
		{
			"fieldname": "campus",
			"label": "Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"insert_after": "group_based_on",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
	],
	"Room": [
		{
			"fieldname": "campus",
			"label": "Campus",
			"fieldtype": "Link",
			"options": "Campus",
			"insert_after": "room_name",
			"in_list_view": 1,
			"in_standard_filter": 1,
		},
	],
}


#: (DocType, field, property, value, type): changes to upstream fields, as Property Setters
PROPERTY_SETTERS = (
	# an online application is a Draft until the applicant submits it (workflow "EduCore Admission Decision")
	("Student Applicant", "application_status", "options", "Draft\nApplied\nApproved\nRejected\nAdmitted", "Text"),
	("Student Applicant", "application_status", "default", "Draft", "Data"),
	# a draft has no offering yet; the first choice sets it, and submitting requires it
	("Student Applicant", "program", "reqd", "0", "Check"),
)


def sync():
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	create_custom_fields(CUSTOM_FIELDS, update=True)
	for doctype, field, prop, value, prop_type in PROPERTY_SETTERS:
		make_property_setter(doctype, field, prop, value, prop_type, validate_fields_for_doctype=False)
