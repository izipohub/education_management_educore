"""Funding routes: how an applicant's studies are paid for, chosen on the application.

Each route (Funding Route, set up by the Registrar on Admission setup) says what is asked of applicants on it: who
pays (a name and contact, or nothing for the applicant themselves) and its documents (an employer's sponsorship
letter, an NSFAF award letter). The Bursar decides which routes pay the application fee (Fee settings): applicants
funded by a government fund such as NSFAF or NTA pay none, and their fee is "Not required", not waived.

A route may name the Sponsor that pays for students on it, so Finance sees which students named a sponsor and have no
sponsorship recorded yet (educore.api.v1.sponsors).

The application fee also follows the applicant's nationality: home, regional (the countries the university lists,
SADC by default) or international (educore.admissions.fees.fee_for).
"""

import frappe

#: route, kind, pays the application fee, asks who pays, shown to applicants, [(document, required)]
DEFAULT_ROUTES = (
	("Self", "Self", 1, 0, "You pay your own fees.", ()),
	("Parent or guardian", "Family", 1, 1, "A parent, guardian or relative pays your fees.", ()),
	(
		"Employer", "Employer", 1, 1, "Your employer pays your fees.",
		(("Employer sponsorship letter", 1),),
	),
	(
		"NSFAF", "Government fund", 0, 0,
		"The Namibia Students Financial Assistance Fund pays your fees. Apply to NSFAF as well; no application fee.",
		(("NSFAF award or application letter", 0),),
	),
	(
		"NTA", "Government fund", 0, 0, "A Namibia Training Authority bursary pays your fees. No application fee.",
		(("NTA bursary letter", 0),),
	),
	(
		"Other bursary or scholarship", "Bursary or scholarship", 1, 1, "A bursary or scholarship pays your fees.",
		(("Bursary or scholarship award letter", 0),),
	),
)

#: documents the default routes ask for: name, shown to applicants
DEFAULT_DOCUMENTS = {
	"Employer sponsorship letter": "On the employer's letterhead, confirming it pays your fees.",
	"NSFAF award or application letter": "Your NSFAF award letter, or proof that you applied to NSFAF.",
	"NTA bursary letter": "Your Namibia Training Authority bursary letter.",
	"Bursary or scholarship award letter": "The award letter from the bursary or scholarship.",
}

#: SADC member states, as Frappe names the countries (alternatives tried in order)
SADC = (
	("Angola",), ("Botswana",), ("Comoros",), ("Congo, The Democratic Republic of the", "Democratic Republic of the Congo"),
	("Eswatini", "Swaziland"), ("Lesotho",), ("Madagascar",), ("Malawi",), ("Mauritius",), ("Mozambique",),
	("Namibia",), ("Seychelles",), ("South Africa",), ("Tanzania", "Tanzania, United Republic of"), ("Zambia",),
	("Zimbabwe",),
)


def ensure_defaults():
	"""From every migrate: the default funding routes on a site that has none, and the regional (SADC) countries
	once"""
	if not frappe.db.table_exists("Funding Route"):
		return
	if not frappe.db.count("Funding Route"):
		for document, description in DEFAULT_DOCUMENTS.items():
			if not frappe.db.exists("Admission Document Type", document):
				frappe.get_doc(
					{
						"doctype": "Admission Document Type",
						"document_name": document,
						"required_for": "Optional",
						"description": description,
						"active": 1,
					}
				).insert(ignore_permissions=True)
		for order, (name, kind, pays, ask, description, documents) in enumerate(DEFAULT_ROUTES):
			frappe.get_doc(
				{
					"doctype": "Funding Route",
					"route_name": name,
					"kind": kind,
					"pays_application_fee": pays,
					"ask_who": ask,
					"description": description,
					"sort_order": order,
					"active": 1,
					"documents": [{"document_type": d, "applies_to": "Everyone", "required": r} for d, r in documents],
				}
			).insert(ignore_permissions=True)
	if not frappe.db.get_default("educore_regional_countries_set"):
		settings = frappe.get_single("Admission Settings")
		if not settings.regional_countries:
			home = settings.home_country or "Namibia"
			for names in SADC:
				country = next((n for n in names if frappe.db.exists("Country", n)), None)
				if country and country != home:
					settings.append("regional_countries", {"country": country})
			settings.save(ignore_permissions=True)
		frappe.db.set_default("educore_regional_countries_set", "1")


def active() -> list[dict]:
	"""The routes applicants choose from, with what each asks"""
	routes = frappe.get_all(
		"Funding Route",
		filters={"active": 1},
		fields=["name", "kind", "description", "pays_application_fee", "ask_who"],
		order_by="sort_order asc, name asc",
	)
	return [{**r, "pays_application_fee": bool(r.pays_application_fee), "ask_who": bool(r.ask_who)} for r in routes]


def route_of(doc):
	name = doc.get("educore_fee_payer")
	return frappe.get_cached_doc("Funding Route", name) if name and frappe.db.exists("Funding Route", name) else None


def fee_exempt(doc) -> bool:
	"""On a route that pays no application fee (NSFAF, NTA by default)"""
	route = route_of(doc)
	return bool(route) and not route.pays_application_fee


def region(doc) -> str:
	"""home, regional or international, for the application fee"""
	from educore.admissions import pathways

	if not pathways.is_international(doc):
		return "home"
	regional = {r.country for r in frappe.get_cached_doc("Admission Settings").regional_countries}
	return "regional" if doc.get("nationality") in regional else "international"
