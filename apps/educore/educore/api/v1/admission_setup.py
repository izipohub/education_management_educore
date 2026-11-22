"""Admission setup, for the Vue app's screen where the university sets its own admission rules.

Everything a university decides about admissions (docs/architecture/online-applications.md, sections 6 and 7) is
set here by the Registrar (or ICT): the application rules, offers and fees (Admission Settings), the pathways
(Admission Pathway), the documents (Admission Document Type), each programme's entry requirements, and the points
scale. Only the fields listed in this module can be changed; every change is saved as the signed-in user, so
Frappe's version history records who changed what.
"""

import frappe
from frappe import _
from frappe.utils import cint, flt

SETUP_ROLES = ("Registrar", "System Manager")

#: Admission Settings fields this screen edits: field: type
SETTINGS_FIELDS = {
	"home_country": "link",
	"max_choices": "int",
	"approval_needs_verified_documents": "check",
	"approval_needs_fee": "check",
	"offer_response_days": "int",
	"offer_reminder_days": "int",
	"enrolment_needs_acceptance": "check",
	"notify_applicants": "check",
	"certification_max_age_months": "int",
	"max_file_size_mb": "int",
	"fee_namibian": "money",
	"fee_international": "money",
	"eft_bank_name": "text",
	"eft_account_name": "text",
	"eft_account_number": "text",
	"eft_branch_code": "text",
	"best_subjects": "int",
}
#: sensible bounds: field: (minimum, maximum)
LIMITS = {
	"max_choices": (1, 10),
	"offer_response_days": (1, 365),
	"offer_reminder_days": (0, 60),
	"certification_max_age_months": (0, 120),
	"max_file_size_mb": (1, 50),
	"best_subjects": (1, 12),
}

PATHWAY_FIELDS = ("level", "evidence", "min_age", "min_work_years", "referees_required", "sort_order", "active", "description")
DOCUMENT_FIELDS = ("required_for", "must_be_certified", "description", "active")
LEVELS = ("Undergraduate", "Postgraduate")
SCHOOL_LEVELS = ("NSSCO", "NSSCAS", "NSSCH")


def _require_setup_role():
	if not set(frappe.get_roles()) & set(SETUP_ROLES):
		frappe.throw(_("Only the Registrar can change the admission setup"), frappe.PermissionError)


def _options(doctype: str, field: str) -> list[str]:
	return [o for o in (frappe.get_meta(doctype).get_field(field).options or "").split("\n") if o]


# --- reading -------------------------------------------------------------------------------------------


@frappe.whitelist(methods=["GET"])
def setup() -> dict:
	_require_setup_role()
	settings = frappe.get_single("Admission Settings")
	return {
		"settings": {field: settings.get(field) for field in SETTINGS_FIELDS},
		"points_scale": [{"level": r.level, "grade": r.grade, "points": r.points} for r in settings.points_scale],
		"pathways": [_pathway(name) for name in frappe.get_all("Admission Pathway", pluck="name", order_by="sort_order asc, name asc")],
		"documents": frappe.get_all(
			"Admission Document Type",
			fields=["name", "required_for", "must_be_certified", "description", "active"],
			order_by="name asc",
		),
		"programmes": [_programme(name) for name in frappe.get_all(
			"Program", filters={"educore_programme_code": ("is", "set")}, pluck="name", order_by="program_name asc"
		)],
		"choices": {
			"countries": frappe.get_all("Country", pluck="name", order_by="name asc"),
			"subjects": frappe.get_all("School Subject", pluck="name", order_by="name asc"),
			"school_levels": list(SCHOOL_LEVELS),
			"evidence": _options("Admission Pathway", "evidence"),
			"required_for": _options("Admission Document Type", "required_for"),
			"applies_to": _options("Pathway Document", "applies_to"),
		},
	}


def _pathway(name: str) -> dict:
	doc = frappe.get_doc("Admission Pathway", name)
	return {
		"name": doc.name,
		**{field: doc.get(field) for field in PATHWAY_FIELDS},
		"documents": [{"document_type": d.document_type, "applies_to": d.applies_to, "required": bool(d.required)} for d in doc.documents],
		"applications": frappe.db.count("Student Applicant", {"educore_pathway": doc.name}),
	}


def _programme(name: str) -> dict:
	doc = frappe.get_doc("Program", name)
	return {
		"name": doc.name,
		"code": doc.get("educore_programme_code"),
		"qualification": doc.get("educore_qualification_type"),
		"nqf_level": doc.get("educore_nqf_level"),
		"level": doc.get("educore_study_level") or "Undergraduate",
		"min_points": doc.get("educore_min_points"),
		"subject_requirements": [
			{"subject": r.subject, "level": r.level, "grade": r.grade} for r in doc.get("educore_subject_requirements") or []
		],
		"min_prior_nqf": doc.get("educore_min_prior_nqf"),
		"min_prior_average": doc.get("educore_min_prior_average"),
	}


# --- the rules -----------------------------------------------------------------------------------------


def _clean(field: str, kind: str, value):
	if kind == "check":
		return 1 if value in (True, 1, "1", "true") else 0
	if kind == "int":
		number = cint(value)
		low, high = LIMITS.get(field, (0, 100000))
		if not low <= number <= high:
			frappe.throw(_("{0} must be between {1} and {2}").format(_label(field), low, high))
		return number
	if kind == "money":
		amount = flt(value, 2)
		if amount < 0:
			frappe.throw(_("{0} cannot be negative").format(_label(field)))
		return amount
	if kind == "link":
		if not value or not frappe.db.exists("Country", value):
			frappe.throw(_("Choose a country from the list"))
		return value
	return (str(value).strip() or None) if value is not None else None


def _label(field: str) -> str:
	return _(frappe.get_meta("Admission Settings").get_label(field))


@frappe.whitelist(methods=["POST"])
def save_settings(data: dict | str) -> dict:
	"""The application rules, offers, fees and document limits; fields not sent are left as they are"""
	_require_setup_role()
	data = frappe.parse_json(data)
	settings = frappe.get_single("Admission Settings")
	for field, kind in SETTINGS_FIELDS.items():
		if field in data:
			settings.set(field, _clean(field, kind, data[field]))
	settings.save(ignore_permissions=True)
	return setup()


@frappe.whitelist(methods=["POST"])
def save_points_scale(rows: list | str) -> dict:
	"""The university's own scale: points per grade at each school level"""
	_require_setup_role()
	rows = frappe.parse_json(rows)
	settings = frappe.get_single("Admission Settings")
	seen = set()
	settings.points_scale = []
	for row in rows:
		level, grade = row.get("level"), str(row.get("grade") or "").strip()
		if level not in SCHOOL_LEVELS or not grade:
			frappe.throw(_("Each grade needs a level ({0}) and a grade").format(", ".join(SCHOOL_LEVELS)))
		if (level, grade.upper()) in seen:
			frappe.throw(_("{0} {1} is listed twice").format(level, grade))
		seen.add((level, grade.upper()))
		points = cint(row.get("points"))
		if points < 0:
			frappe.throw(_("Points cannot be negative"))
		settings.append("points_scale", {"level": level, "grade": grade, "points": points})
	settings.scale_is_placeholder = 0
	settings.save(ignore_permissions=True)
	return setup()


# --- pathways ------------------------------------------------------------------------------------------


def _set_documents(doc, rows: list, field: str = "documents"):
	allowed = set(_options("Pathway Document", "applies_to"))
	doc.set(field, [])
	seen = set()
	for row in rows or []:
		document, applies_to = row.get("document_type"), row.get("applies_to") or "Everyone"
		if not document:
			continue
		if not frappe.db.exists("Admission Document Type", document):
			frappe.throw(_("Unknown document {0}").format(document))
		if applies_to not in allowed:
			frappe.throw(_("Unknown group {0}").format(applies_to))
		if (document, applies_to) in seen:
			frappe.throw(_("{0} is listed twice").format(document))
		seen.add((document, applies_to))
		doc.append(field, {"document_type": document, "applies_to": applies_to, "required": 1 if row.get("required") else 0})


@frappe.whitelist(methods=["POST"])
def save_pathway(data: dict | str, name: str | None = None) -> dict:
	"""Change a pathway, or add one (name empty: data.pathway_name is the new pathway's name)"""
	_require_setup_role()
	data = frappe.parse_json(data)
	if name:
		doc = frappe.get_doc("Admission Pathway", name)
	else:
		new_name = (data.get("pathway_name") or "").strip()
		if not new_name:
			frappe.throw(_("Give the new pathway a name"))
		if frappe.db.exists("Admission Pathway", new_name):
			frappe.throw(_("There is already a pathway called {0}").format(new_name))
		doc = frappe.new_doc("Admission Pathway")
		doc.pathway_name = new_name
	if "level" in data and data["level"] not in LEVELS:
		frappe.throw(_("Level is Undergraduate or Postgraduate"))
	if "evidence" in data and data["evidence"] not in _options("Admission Pathway", "evidence"):
		frappe.throw(_("Choose what the pathway is judged on from the list"))
	for field in PATHWAY_FIELDS:
		if field in data:
			value = data[field]
			if field == "min_work_years":
				value = flt(value, 1)
				if value < 0:
					frappe.throw(_("Years of work cannot be negative"))
			elif field in ("min_age", "referees_required", "sort_order"):
				value = cint(value)
				if value < 0:
					frappe.throw(_("{0} cannot be negative").format(field.replace("_", " ")))
			elif field == "active":
				value = 1 if value else 0
			elif field == "description":
				value = (value or "").strip() or None
			doc.set(field, value)
	if "documents" in data:
		_set_documents(doc, data["documents"])
	doc.save(ignore_permissions=True)
	return setup()


# --- documents -----------------------------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def save_document_type(data: dict | str, name: str | None = None) -> dict:
	_require_setup_role()
	data = frappe.parse_json(data)
	if name:
		doc = frappe.get_doc("Admission Document Type", name)
	else:
		new_name = (data.get("document_name") or "").strip()
		if not new_name:
			frappe.throw(_("Give the document a name"))
		if frappe.db.exists("Admission Document Type", new_name):
			frappe.throw(_("There is already a document called {0}").format(new_name))
		doc = frappe.new_doc("Admission Document Type")
		doc.document_name = new_name
	if "required_for" in data and data["required_for"] not in _options("Admission Document Type", "required_for"):
		frappe.throw(_("Choose who the document is asked of from the list"))
	for field in DOCUMENT_FIELDS:
		if field in data:
			value = data[field]
			if field in ("must_be_certified", "active"):
				value = 1 if value else 0
			elif field == "description":
				value = (value or "").strip() or None
			doc.set(field, value)
	doc.save(ignore_permissions=True)
	return setup()


# --- programmes ----------------------------------------------------------------------------------------


@frappe.whitelist(methods=["POST"])
def save_programme(name: str, data: dict | str) -> dict:
	"""A programme's level of study and entry requirements"""
	_require_setup_role()
	data = frappe.parse_json(data)
	doc = frappe.get_doc("Program", name)
	if "level" in data:
		if data["level"] not in LEVELS:
			frappe.throw(_("Level is Undergraduate or Postgraduate"))
		doc.educore_study_level = data["level"]
	if "min_points" in data:
		doc.educore_min_points = max(cint(data["min_points"]), 0) or None
	if "min_prior_nqf" in data:
		nqf = cint(data["min_prior_nqf"])
		if nqf and not 1 <= nqf <= 10:
			frappe.throw(_("The NQF level is between 1 and 10"))
		doc.educore_min_prior_nqf = nqf or None
	if "min_prior_average" in data:
		average = flt(data["min_prior_average"], 1)
		if not 0 <= average <= 100:
			frappe.throw(_("The average is a percentage between 0 and 100"))
		doc.educore_min_prior_average = average or None
	if "subject_requirements" in data:
		scale = {(r.level, str(r.grade).upper()) for r in frappe.get_single("Admission Settings").points_scale}
		doc.set("educore_subject_requirements", [])
		for row in data["subject_requirements"] or []:
			subject, level, grade = row.get("subject"), row.get("level"), str(row.get("grade") or "").strip()
			if not subject:
				continue
			if not frappe.db.exists("School Subject", subject):
				frappe.throw(_("Unknown subject {0}").format(subject))
			if (level, grade.upper()) not in scale:
				frappe.throw(_("{0} {1} is not on the points scale").format(level, grade))
			doc.append("educore_subject_requirements", {"subject": subject, "level": level, "grade": grade})
	doc.save(ignore_permissions=True)
	return setup()
