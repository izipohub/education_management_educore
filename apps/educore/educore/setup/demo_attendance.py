"""Demo class attendance (development only): Namibia's 2026 public holidays as the university's holiday list, an 80%
minimum attendance, and the first lessons' registers for two classes (on their timetable's days), one student below the
minimum.

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
#: class: (first day, lessons, student name absent at these lesson numbers)
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


def _sessions(group: str, start, count: int) -> list[tuple]:
	"""The module's first lessons from the start (a register each); weekly from the start without a timetable"""
	from educore.academics import attendance

	out = []
	day = getdate(start)
	for _ in range(200):
		if len(out) >= count:
			break
		that_day = attendance.lessons(group, day)
		if that_day:
			out += [(day, lesson["key"]) for lesson in that_day]
		day = add_days(day, 1)
	if not out and not frappe.db.exists("Timetable Slot", {"student_group": group}):
		out = [(add_days(getdate(start), 7 * w), None) for w in range(count)]
	return out[:count]


def create() -> int:
	from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

	from educore.academics import attendance

	holidays = create_holidays()
	if not frappe.db.get_single_value("Examination Settings", "min_attendance"):
		frappe.db.set_single_value("Examination Settings", "min_attendance", 80)
	taken = 0
	for group, (start, sessions, absences) in REGISTERS.items():
		if not frappe.db.exists("Student Group", group) or frappe.db.exists("Student Attendance", {"student_group": group}):
			continue
		members = attendance.students(group)
		number = 0
		for day, lesson in _sessions(group, start, sessions + 4):
			if number >= sessions:
				break
			if holidays and is_holiday(holidays, day):
				continue
			number += 1
			entries = [
				{"student": s.student, "status": attendance.ABSENT if number in absences.get(s.student_name, ()) else attendance.PRESENT}
				for s in members
			]
			attendance.take(group, day, entries, lesson)
			taken += 1
	return taken
