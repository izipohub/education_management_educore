"""Class attendance (educore.academics.attendance): the lecturer's register for the classes they teach, and each
student's attendance so far. Who the lecturer is comes only from the session (educore.api.v1.teaching)."""

import frappe
from frappe import _
from frappe.utils import nowdate

from educore.academics import attendance


def _require_teaches(group: str):
	from educore.api.v1.examinations import _teaches

	if not _teaches(group):
		frappe.throw(_("You do not teach this class"), frappe.PermissionError)


def _class(group: str) -> dict:
	g = frappe.db.get_value("Student Group", group, ["name", "course", "campus", "academic_year"], as_dict=True)
	course = frappe.db.get_value("Course", g.course, ["course_name", "educore_course_code"], as_dict=True) or {}
	return {**g, "course_name": course.get("course_name") or g.course, "code": course.get("educore_course_code")}


@frappe.whitelist(methods=["GET"])
def register(group: str, date: str | None = None, lesson: str | None = None) -> dict:
	"""The module's register for a lesson on a day (today by default; the first lesson unless one is chosen), or for
	the day when it has no timetable: each student's status, if taken; the lessons that day; the lessons so far"""
	_require_teaches(group)
	if not date:
		# the latest lesson up to today, else today
		date = str(attendance.latest_lesson_day(group) or nowdate())
	date = str(attendance.check_date(group, date))
	that_day = attendance.lessons(group, date)
	if that_day and lesson not in {x["key"] for x in that_day}:
		lesson = that_day[0]["key"]
	chosen = next((x for x in that_day if x["key"] == lesson), None)
	filters = {"student_group": group, "date": date, "docstatus": 1}
	if chosen:
		filters["course_schedule"] = chosen["schedule"] or "-"
	else:
		filters["course_schedule"] = ("is", "not set")
	taken = {r.student: r.status for r in frappe.get_all("Student Attendance", filters=filters, fields=["student", "status"])}
	return {
		"class": _class(group),
		"date": date,
		"lessons": that_day,
		# the module meets on these days in that semester; another day has no register
		"lesson_days": attendance.lesson_days(group, date),
		"timetabled": attendance.timetabled(group),
		"lesson": chosen["key"] if chosen else None,
		"taken": bool(taken),
		"entries": [{"student": s.student, "student_name": s.student_name, "status": taken.get(s.student)} for s in attendance.students(group)],
		**attendance.summary(group),
	}


@frappe.whitelist(methods=["POST"])
def take(group: str, date: str, entries: list | str, lesson: str | None = None) -> dict:
	_require_teaches(group)
	entries = frappe.parse_json(entries) or []
	missing = [e.get("student") for e in entries if not e.get("status")]
	if missing or not entries:
		frappe.throw(_("Mark every student present, absent or excused"))
	attendance.take(group, date, entries, lesson)
	return register(group, date, lesson)
