"""EduCore Demo University: a fictional university for development, with three campuses, four faculties
and the main administrative divisions.

    bench --site educore.localhost execute educore.setup.demo.create_demo_university

Only on a *.localhost development site. Running it again adds whatever is missing and changes nothing else.
"""

import frappe

from educore.setup.university import setup_university

COMPANY = "EduCore Demo University"
ABBR = "EDU"

CAMPUSES = [
	# name, code, main, town, region
	("Windhoek Campus", "WHK", 1, "Windhoek", "Khomas"),
	("Oshakati Campus", "OSH", 0, "Oshakati", "Oshana"),
	("Keetmanshoop Campus", "KMP", 0, "Keetmanshoop", "ǁKaras"),
]
ALL_CAMPUSES = [code for _, code, *_ in CAMPUSES]

#: (name, type, code, campuses, children: [(name, type, code, campuses)])
UNITS = [
	(
		"Faculty of Science and Technology",
		"Faculty",
		"FST",
		["WHK", "OSH"],
		[
			("Department of Computing", "Academic Department", "COMP", ["WHK", "OSH"]),
			("Department of Mathematics and Statistics", "Academic Department", "MATH", ["WHK"]),
		],
	),
	(
		"Faculty of Commerce and Management",
		"Faculty",
		"FCM",
		ALL_CAMPUSES,
		[
			("Department of Accounting and Finance", "Academic Department", "ACCF", ALL_CAMPUSES),
			("Department of Management", "Academic Department", "MGMT", ["WHK", "KMP"]),
		],
	),
	(
		"Faculty of Education",
		"Faculty",
		"FED",
		["WHK", "OSH"],
		[("Department of Education Foundations", "Academic Department", "EDFN", ["WHK", "OSH"])],
	),
	(
		"Faculty of Health Sciences",
		"Faculty",
		"FHS",
		["WHK"],
		[("School of Nursing", "School", "NURS", ["WHK"])],
	),
	(
		"Academic Affairs",
		"Administrative Division",
		"ACAD",
		ALL_CAMPUSES,
		[
			("Registry", "Support Unit", "REG", ALL_CAMPUSES),
			("Examinations", "Support Unit", "EXAM", ALL_CAMPUSES),
		],
	),
	(
		"Finance and Administration",
		"Administrative Division",
		"FINA",
		ALL_CAMPUSES,
		[
			("Finance", "Support Unit", "FIN", ALL_CAMPUSES),
			("Human Resources", "Support Unit", "HR", ALL_CAMPUSES),
			("Procurement", "Support Unit", "PROC", ["WHK"]),
			("Facilities", "Support Unit", "FAC", ALL_CAMPUSES),
		],
	),
	(
		"Information and Communication Technology",
		"Administrative Division",
		"ICT",
		ALL_CAMPUSES,
		[],
	),
]


def create_demo_university():
	if not (frappe.local.site or "").endswith(".localhost"):
		frappe.throw(f"The demo university is only for a *.localhost development site, not {frappe.local.site}")

	company = setup_university(COMPANY, ABBR, fy_start_date="2026-01-01", fy_end_date="2026-12-31")
	campus_by_code = {}
	for name, code, main, city, region in CAMPUSES:
		existing = frappe.db.get_value("Campus", {"campus_code": code})
		if not existing:
			existing = (
				frappe.get_doc(
					{
						"doctype": "Campus",
						"campus_name": name,
						"campus_code": code,
						"is_main_campus": main,
						"company": company,
						"city": city,
						"region": region,
					}
				)
				.insert(ignore_permissions=True)
				.name
			)
		campus_by_code[code] = existing

	root = frappe.db.get_value("Department", {"is_group": 1, "parent_department": ("in", ("", None))})
	for name, unit_type, code, campuses, children in UNITS:
		parent = _ensure_unit(company, name, unit_type, code, campuses, root, campus_by_code)
		for child_name, child_type, child_code, child_campuses in children:
			_ensure_unit(company, child_name, child_type, child_code, child_campuses, parent, campus_by_code)

	from educore.setup.demo_catalogue import create_catalogue

	catalogue = create_catalogue()

	from educore.academics.calendar import ensure_academic_year
	from educore.setup.demo_finance import create_fee_structures

	ensure_academic_year(2026)
	ensure_academic_year(2027)
	create_fee_structures()

	from educore.setup.demo_admissions import create_admissions_setup

	create_admissions_setup()
	frappe.db.commit()
	print(
		f"{company}: {len(CAMPUSES)} campuses, {sum(1 + len(u[4]) for u in UNITS)} units, "
		f"{catalogue['programmes']} programmes, {catalogue['courses']} courses, {catalogue['offerings']} offerings"
	)


def _ensure_unit(company, name, unit_type, code, campuses, parent, campus_by_code) -> str:
	existing = frappe.db.get_value("Department", {"educore_unit_code": code})
	if existing:
		return existing
	return (
		frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": name,
				"company": company,
				"parent_department": parent,
				"educore_unit_type": unit_type,
				"educore_unit_code": code,
				"educore_campuses": [{"campus": campus_by_code[c]} for c in campuses],
			}
		)
		.insert(ignore_permissions=True)
		.name
	)
