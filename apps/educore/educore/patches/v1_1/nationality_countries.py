"""Nationality is chosen from the country list (the application fee follows it: home, regional, international); the
nationalities typed in before are moved onto their country where the word is a known one."""

import frappe

#: nationality as people wrote it → the country, as Frappe names it
DEMONYMS = {
	"namibian": "Namibia", "angolan": "Angola", "motswana": "Botswana", "batswana": "Botswana", "botswanan": "Botswana",
	"zambian": "Zambia", "zimbabwean": "Zimbabwe", "south african": "South Africa", "mosotho": "Lesotho", "basotho": "Lesotho",
	"swazi": "Eswatini", "malawian": "Malawi", "mozambican": "Mozambique", "tanzanian": "Tanzania", "congolese": "Congo",
	"kenyan": "Kenya", "nigerian": "Nigeria", "ghanaian": "Ghana", "german": "Germany", "cuban": "Cuba",
	"chinese": "China", "indian": "India", "british": "United Kingdom", "american": "United States",
}


def _country(value: str | None) -> str | None:
	if not value or frappe.db.exists("Country", value):
		return None
	country = DEMONYMS.get(value.strip().lower())
	if country and not frappe.db.exists("Country", country):
		country = {"Eswatini": "Swaziland", "Tanzania": "Tanzania, United Republic of"}.get(country, country)
	return country if country and frappe.db.exists("Country", country) else None


def execute():
	for doctype in ("Student Applicant", "Student"):
		for row in frappe.get_all(doctype, filters={"nationality": ("is", "set")}, fields=["name", "nationality"]):
			country = _country(row.nationality)
			if country:
				frappe.db.set_value(doctype, row.name, "nationality", country, update_modified=False)
