"""Demo class attendance (development only): Namibia's 2026 public holidays as the university's holiday list, an 80%
minimum attendance, and a few weeks of registers for two classes, one student below the minimum.

Called from demo_students.create, after the classes exist. Re-running adds whatever is missing.
"""

import frappe
from frappe.utils import add_days, getdate

#: Namibia's public holidays in 2026 (Public Holidays Act; Easter Sunday is 5 April 2026)
HOLIDAYS_2026 = (
	("2026-01-01", "New Year's Day"),
	("2026-03-21", "Independence Day"),
	("2026-04-03", "Good Friday"),
	("2026-04-06", "Easter Monday"),
	("2026-05-01", "Workers' Day"),
	("2026-05-04", "Cassinga Day"),
	("2026-05-14", "Ascension Day"),
	("2026-05-25", "Africa Day"),
	("2026-05-28", "Genocide Remembrance Day"),
	("2026-08-26", "Heroes' Day"),
	("2026-12-10", "Human Rights Day"),
	("2026-12-25", "Christmas Day"),
	("2026-12-26", "Family Day"),
)
#: class: (first session, weeks, student name absent on these session numbers)
REGISTERS = {
	"ACC1511 KMP 2026": ("2026-02-09", 8, {"Petrus Kooper": (2, 4, 5, 7)}),
	"CMP1511 WHK 2026": ("2026-02-10", 8, {"Ndapewa Amukoto": (3,)}),
}


def create_holidays() -> str | None:
	company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company")
	if not company:
		return None
	name = "Namibia 2026"
	if not frappe.db.exists("Holiday List", name):
		frappe.get_doc(
			{
				"doctype": "Holiday List",
				"holiday_list_name": name,
				"from_date": "2026-01-01",
				"to_date": "2026-12-31",
				"holidays": [{"holiday_date": d, "description": what} for d, what in HOLIDAYS_2026],
			}
		).insert(ignore_permissions=True)
	if not frappe.db.get_value("Company", company, "default_holiday_list"):
		frappe.db.set_value("Company", company, "default_holiday_list", name)
	return name


def create() -> int:
	from educore.academics import attendance

	create_holidays()
	if not frappe.db.get_single_value("Examination Settings", "min_attendance"):
		frappe.db.set_single_value("Examination Settings", "min_attendance", 80)
	taken = 0
	for group, (start, weeks, absences) in REGISTERS.items():
		if not frappe.db.exists("Student Group", group) or frappe.db.exists("Student Attendance", {"student_group": group}):
			continue
		members = attendance.students(group)
		for week in range(1, weeks + 1):
			day = add_days(getdate(start), 7 * (week - 1))
			entries = [
				{
					"student": s.student,
					"status": attendance.ABSENT if week in absences.get(s.student_name, ()) else attendance.PRESENT,
				}
				for s in members
			]
			attendance.take(group, day, entries)
			taken += 1
	return taken
