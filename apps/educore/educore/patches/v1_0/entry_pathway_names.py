"""Entry pathways named as Namibian universities name them (docs/architecture/terminology.md): Mature Age Entry,
Credit transfer, Re-admission; Recognition of Prior Learning added. Applications keep their pathway (renaming
updates every link). Mature Age Entry's age and work rules move to UNAM's (25, five years) only where the site still
has EduCore's earlier default."""

import frappe

from educore.admissions import pathways

RENAMES = {
	"Mature age entry": "Mature Age Entry",
	"Advanced standing / transfer": "Credit transfer",
	"Resumption of studies": "Re-admission",
}


def _exactly(name: str) -> bool:
	"""The name as written, capitals included (the database compares names without regard to case)"""
	return bool(frappe.db.sql("select 1 from `tabAdmission Pathway` where binary name = %s", name))


def _rename_case(old: str, new: str):
	"""Only the capitals change: Frappe's rename sees the same record, so the name and its links are set directly"""
	frappe.db.sql("update `tabAdmission Pathway` set name = %s, pathway_name = %s where binary name = %s", (new, new, old))
	frappe.db.sql("update `tabPathway Document` set parent = %s where binary parent = %s", (new, old))
	frappe.db.sql("update `tabStudent Applicant` set educore_pathway = %s where binary educore_pathway = %s", (new, old))
	frappe.clear_document_cache("Admission Pathway", old)


def execute():
	if not frappe.db.count("Admission Pathway"):
		return  # a new site: ensure_defaults creates them with these names
	for old, new in RENAMES.items():
		if not _exactly(old):
			continue
		if old.lower() == new.lower():
			_rename_case(old, new)
		elif not frappe.db.exists("Admission Pathway", new):
			frappe.rename_doc("Admission Pathway", old, new, force=True)
			frappe.db.set_value("Admission Pathway", new, "pathway_name", new)

	mature = "Mature Age Entry"
	if frappe.db.exists("Admission Pathway", mature):
		spec = pathways.DEFAULT_PATHWAYS[mature]
		values = {"description": spec["description"]}
		if frappe.db.get_value("Admission Pathway", mature, "min_age") == 23:
			values["min_age"] = spec["min_age"]
		if not frappe.db.get_value("Admission Pathway", mature, "min_work_years"):
			values["min_work_years"] = spec["min_work_years"]
		frappe.db.set_value("Admission Pathway", mature, values)

	for name, spec in pathways.DEFAULT_PATHWAYS.items():
		if name in RENAMES.values() and name != mature and frappe.db.exists("Admission Pathway", name):
			frappe.db.set_value("Admission Pathway", name, "description", spec["description"])

	rpl = "Recognition of Prior Learning"
	if not frappe.db.exists("Admission Pathway", rpl):
		for document, (guidance, certified) in pathways.DEFAULT_DOCUMENTS.items():
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
		spec = pathways.DEFAULT_PATHWAYS[rpl]
		frappe.get_doc(
			{
				"doctype": "Admission Pathway",
				"pathway_name": rpl,
				"level": spec["level"],
				"evidence": spec["evidence"],
				"sort_order": spec["sort_order"],
				"description": spec["description"],
				"documents": [{"document_type": d, "applies_to": a, "required": r} for d, a, r in spec["documents"]],
			}
		).insert(ignore_permissions=True)
