"""Who pays becomes a funding route (educore.admissions.funding): the default routes, and each application's and
student's earlier answer moved onto one ("Sponsor or bursary" naming NSFAF or NTA becomes that route)."""

import frappe


def _route(payer: str | None, name: str | None) -> str | None:
	if payer != "Sponsor or bursary":
		return payer
	text = (name or "").upper()
	if "NSFAF" in text or "STUDENTS FINANCIAL ASSISTANCE" in text:
		return "NSFAF"
	if "NTA" in text.split() or "TRAINING AUTHORITY" in text:
		return "NTA"
	return "Other bursary or scholarship"


def execute():
	from educore.admissions import funding

	frappe.reload_doc("admissions", "doctype", "admission_country")
	frappe.reload_doc("admissions", "doctype", "funding_route")
	frappe.reload_doc("admissions", "doctype", "admission_settings")
	funding.ensure_defaults()
	for doctype in ("Student Applicant", "Student"):
		if not frappe.db.has_column(doctype, "educore_fee_payer"):
			continue
		for row in frappe.get_all(doctype, filters={"educore_fee_payer": "Sponsor or bursary"}, fields=["name", "educore_fee_payer", "educore_fee_payer_name"]):
			frappe.db.set_value(doctype, row.name, "educore_fee_payer", _route(row.educore_fee_payer, row.educore_fee_payer_name), update_modified=False)
