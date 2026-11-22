"""The academic calendar: Education's Academic Year and Academic Term.

    bench --site <site> execute educore.academics.calendar.ensure_academic_year --kwargs "{'year': 2027}"

A Namibian university year runs February to November in two semesters (the defaults below); pass other
dates for a university that differs. Adds what is missing; never moves the dates of an existing year or term.
"""

import frappe

#: (term, start MM-DD, end MM-DD)
DEFAULT_TERMS = (
	("Semester 1", "02-01", "06-30"),
	("Semester 2", "07-01", "11-30"),
)
DEFAULT_START, DEFAULT_END = "02-01", "11-30"


def ensure_academic_year(year: int, start: str = DEFAULT_START, end: str = DEFAULT_END, terms=DEFAULT_TERMS) -> str:
	name = str(year)
	if not frappe.db.exists("Academic Year", name):
		frappe.get_doc(
			{
				"doctype": "Academic Year",
				"academic_year_name": name,
				"year_start_date": f"{year}-{start}",
				"year_end_date": f"{year}-{end}",
			}
		).insert(ignore_permissions=True)
	for term_name, term_start, term_end in terms:
		if not frappe.db.exists("Academic Term", {"academic_year": name, "term_name": term_name}):
			frappe.get_doc(
				{
					"doctype": "Academic Term",
					"academic_year": name,
					"term_name": term_name,
					"term_start_date": f"{year}-{term_start}",
					"term_end_date": f"{year}-{term_end}",
				}
			).insert(ignore_permissions=True)
	return name


def term(year: int, term_name: str) -> str | None:
	return frappe.db.get_value("Academic Term", {"academic_year": str(year), "term_name": term_name})
