"""Class attendance: the lecturer's register for a class (Student Group) on a date, kept as Education's Student
Attendance (Present, Absent, Leave: shown as Excused), so Education's own reports count it too.

- A lecturer takes the register of the classes they teach, for a day that has come and falls in the class's academic
  year and is not a holiday; taking it again for the same day changes it (the earlier record is cancelled).
- A student's attendance in a class is the share of the sessions held that they were present at; excused absences are
  left out of both. Below the university's minimum (Examination Settings, min_attendance; 0: none) a student is
  flagged to the lecturer, the department and the student.
- Education refuses attendance whenever the company has no holiday list (ERPNext's default holiday list, which HR
  keeps). EduCore takes attendance without one, and still refuses a holiday on the list when there is one.
"""

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate, nowdate

from education.education.doctype.student_attendance.student_attendance import StudentAttendance as _Education

PRESENT, ABSENT, EXCUSED = "Present", "Absent", "Leave"
STATUSES = (PRESENT, ABSENT, EXCUSED)


class StudentAttendance(_Education):
	def validate_is_holiday(self):
		from erpnext.setup.doctype.holiday_list.holiday_list import is_holiday

		campus = frappe.db.get_value("Student Group", self.student_group, "campus") if self.student_group else None
		company = (frappe.db.get_value("Campus", campus, "company") if campus else None) or frappe.defaults.get_global_default("company")
		holidays = frappe.get_cached_value("Company", company, "default_holiday_list") if company else None
		if holidays and is_holiday(holidays, self.date):
			frappe.throw(_("{0} is a holiday: no class attendance").format(formatdate(self.date)))


def minimum() -> float:
	return flt(frappe.db.get_single_value("Examination Settings", "min_attendance"))


def _records(group: str, date=None) -> list:
	filters = {"student_group": group, "docstatus": 1}
	if date:
		filters["date"] = getdate(date)
	return frappe.get_all("Student Attendance", filters=filters, fields=["name", "student", "date", "status"], order_by="date asc")


def students(group: str) -> list:
	return frappe.get_all(
		"Student Group Student", filters={"parent": group, "active": 1}, fields=["student", "student_name"], order_by="student_name asc"
	)


def check_date(group: str, date) -> object:
	date = getdate(date)
	if date > getdate(nowdate()):
		frappe.throw(_("Attendance is taken on the day or after it, not before"))
	year = frappe.db.get_value("Student Group", group, "academic_year")
	start, end = frappe.db.get_value("Academic Year", year, ["year_start_date", "year_end_date"]) or (None, None)
	if start and end and not getdate(start) <= date <= getdate(end):
		frappe.throw(_("{0} is outside the {1} academic year").format(formatdate(date), year))
	return date


def take(group: str, date, entries: list[dict]) -> int:
	"""The register for the day: each student's status; a status already recorded and changed is replaced"""
	date = check_date(group, date)
	members = {s.student: s.student_name for s in students(group)}
	recorded = {r.student: r for r in _records(group, date)}
	changed = 0
	for entry in entries:
		student, status = entry.get("student"), entry.get("status")
		if student not in members:
			frappe.throw(_("{0} is not in this class").format(student))
		if status not in STATUSES:
			frappe.throw(_("Mark {0} present, absent or excused").format(members[student]))
		earlier = recorded.get(student)
		if earlier and earlier.status == status:
			continue
		if earlier:
			old = frappe.get_doc("Student Attendance", earlier.name)
			old.flags.ignore_permissions = True
			old.cancel()
		doc = frappe.get_doc(
			{"doctype": "Student Attendance", "student": student, "student_group": group, "date": date, "status": status}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.submit()
		changed += 1
	return changed


def summary(group: str) -> dict:
	"""Each student's attendance in the class so far, and the sessions held"""
	records = _records(group)
	by_student: dict[str, dict] = {}
	sessions: dict[str, dict] = {}
	for r in records:
		day = str(r.date)
		sessions.setdefault(day, {"date": day, PRESENT: 0, ABSENT: 0, EXCUSED: 0})[r.status] += 1
		by_student.setdefault(r.student, {PRESENT: 0, ABSENT: 0, EXCUSED: 0})[r.status] += 1
	least = minimum()
	rows = []
	for s in students(group):
		counts = by_student.get(s.student, {PRESENT: 0, ABSENT: 0, EXCUSED: 0})
		held = counts[PRESENT] + counts[ABSENT]
		rate = round(100 * counts[PRESENT] / held) if held else None
		rows.append(
			{
				"student": s.student,
				"student_name": s.student_name,
				"present": counts[PRESENT],
				"absent": counts[ABSENT],
				"excused": counts[EXCUSED],
				"rate": rate,
				"below": bool(least and rate is not None and rate < least),
			}
		)
	return {
		"minimum": least,
		"sessions": [
			{"date": d["date"], "present": d[PRESENT], "absent": d[ABSENT], "excused": d[EXCUSED]}
			for d in sorted(sessions.values(), key=lambda d: d["date"], reverse=True)
		],
		"students": rows,
	}


def of_student(student: str, academic_year: str | None = None) -> list[dict]:
	"""A student's attendance in each of their classes (the year's, or the latest year's)"""
	groups = frappe.db.sql(
		"""select g.name, g.course, g.academic_year from `tabStudent Group Student` s
		join `tabStudent Group` g on g.name = s.parent
		where s.student = %s and s.active = 1 and g.disabled = 0 order by g.academic_year desc, g.course asc""",
		student,
		as_dict=True,
	)
	if not groups:
		return []
	academic_year = academic_year or groups[0].academic_year
	least = minimum()
	out = []
	for g in groups:
		if g.academic_year != academic_year:
			continue
		counts = {PRESENT: 0, ABSENT: 0, EXCUSED: 0}
		for status in frappe.get_all("Student Attendance", filters={"student_group": g.name, "student": student, "docstatus": 1}, pluck="status"):
			counts[status] += 1
		held = counts[PRESENT] + counts[ABSENT]
		rate = round(100 * counts[PRESENT] / held) if held else None
		out.append(
			{
				"group": g.name,
				"course": frappe.db.get_value("Course", g.course, "course_name") or g.course,
				"code": frappe.db.get_value("Course", g.course, "educore_course_code"),
				"academic_year": g.academic_year,
				"present": counts[PRESENT],
				"absent": counts[ABSENT],
				"excused": counts[EXCUSED],
				"rate": rate,
				"below": bool(least and rate is not None and rate < least),
				"minimum": least,
			}
		)
	return out
