"""Class attendance: the lecturer's register for each lesson of a module (Student Group), kept as Education's
Student Attendance (Present, Absent, Leave: shown as Excused), so Education's own reports count it too.

- A lesson is one meeting of the module: on a day, at the times of one of its timetable slots
  (educore.academics.timetable), kept as Education's Course Schedule (made when its register is first taken), which
  each attendance record links to. A module meeting twice on a day has two registers. A module with no timetable has
  one register a day.

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


def _records(group: str, date=None, schedule: str | None = None, by_day: bool = False) -> list:
	"""Attendance records of the module: all, a day's, one lesson's (schedule), or a day's register without a lesson"""
	filters = {"student_group": group, "docstatus": 1}
	if date:
		filters["date"] = getdate(date)
	if schedule:
		filters["course_schedule"] = schedule
	elif by_day:
		filters["course_schedule"] = ("is", "not set")
	return frappe.get_all(
		"Student Attendance", filters=filters, fields=["name", "student", "date", "status", "course_schedule"], order_by="date asc"
	)


# --- lessons ---------------------------------------------------------------------------------------------


def _semester_on(date) -> str | None:
	return frappe.db.get_value("Academic Term", {"term_start_date": ("<=", date), "term_end_date": (">=", date)}, "term_name")


def lessons(group: str, date) -> list[dict]:
	"""The module's lessons on a day: its timetable slots for that weekday in that day's semester"""
	from educore.academics.timetable import _t, room_name

	date = getdate(date)
	semester = _semester_on(date)
	if not semester:
		return []
	slots = frappe.get_all(
		"Timetable Slot",
		filters={"student_group": group, "semester": semester, "day": date.strftime("%A")},
		fields=["name", "start_time", "end_time", "room", "kind"],
		order_by="start_time asc",
	)
	out = []
	for s in slots:
		schedule = frappe.db.get_value("Course Schedule", {"student_group": group, "schedule_date": date, "from_time": s.start_time})
		out.append(
			{
				"key": s.name,
				"start_time": _t(s.start_time),
				"end_time": _t(s.end_time),
				"room_name": room_name(s.room),
				"kind": s.kind,
				"schedule": schedule,
				"taken": bool(schedule and frappe.db.exists("Student Attendance", {"course_schedule": schedule, "docstatus": 1})),
			}
		)
	return out


def lesson_days(group: str, date) -> list[str]:
	"""The weekdays the module meets in that day's semester (none: no timetable)"""
	from educore.academics.timetable import DAYS

	semester = _semester_on(getdate(date))
	days = set(frappe.get_all("Timetable Slot", filters={"student_group": group, "semester": semester}, pluck="day")) if semester else set()
	return [d for d in DAYS if d in days]


def timetabled(group: str) -> bool:
	"""The module has a timetable: its registers are per lesson (otherwise a register a day)"""
	return bool(frappe.db.exists("Timetable Slot", {"student_group": group}))


def latest_lesson_day(group: str, until=None):
	"""The latest day up to today (or until) with a lesson of the module, within the semesters it is timetabled in"""
	until = getdate(until or nowdate())
	year = frappe.db.get_value("Student Group", group, "academic_year")
	semesters = set(frappe.get_all("Timetable Slot", filters={"student_group": group}, pluck="semester"))
	best = None
	for term in frappe.get_all("Academic Term", filters={"academic_year": year, "term_name": ("in", list(semesters) or [""])}, fields=["term_start_date", "term_end_date"]):
		day = min(until, getdate(term.term_end_date))
		for _ in range(7):
			if day < getdate(term.term_start_date):
				break
			if lessons(group, day):
				best = max(best, day) if best else day
				break
			day = frappe.utils.add_days(day, -1)
	return best


def lesson_schedule(group: str, date, slot: str) -> str:
	"""The lesson's Course Schedule, made the first time its register is taken"""
	date = getdate(date)
	s = frappe.db.get_value("Timetable Slot", slot, ["student_group", "start_time", "end_time", "room", "day"], as_dict=True)
	if not s or s.student_group != group or s.day != date.strftime("%A"):
		frappe.throw(_("This module has no lesson then"))
	existing = frappe.db.get_value("Course Schedule", {"student_group": group, "schedule_date": date, "from_time": s.start_time})
	if existing:
		return existing
	instructor = (frappe.get_all("Student Group Instructor", filters={"parent": group}, pluck="instructor") or [None])[0]
	if not instructor:
		frappe.throw(_("The module has no lecturer: the head of department allocates one first"))
	doc = frappe.get_doc(
		{
			"doctype": "Course Schedule",
			"student_group": group,
			"course": frappe.db.get_value("Student Group", group, "course"),
			"instructor": instructor,
			"schedule_date": date,
			"from_time": s.start_time,
			"to_time": s.end_time,
			"room": s.room,
		}
	)
	# the timetable already keeps rooms, lecturers and students from clashing (educore.academics.timetable)
	doc.validate_overlap = lambda: None
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


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


def take(group: str, date, entries: list[dict], lesson: str | None = None) -> int:
	"""The register for a lesson (a timetable slot on the day), or for the day when the module has no timetable:
	each student's status; a status already recorded and changed is replaced"""
	date = check_date(group, date)
	if not lesson and lessons(group, date):
		frappe.throw(_("Choose the lesson"))
	if not lesson and timetabled(group):
		days = lesson_days(group, date)
		frappe.throw(
			_("The module has no lesson on {0}: it meets on {1}").format(formatdate(date), ", ".join(days))
			if days
			else _("The module has no lessons in the semester of {0}").format(formatdate(date))
		)
	schedule = lesson_schedule(group, date, lesson) if lesson else None
	members = {s.student: s.student_name for s in students(group)}
	recorded = {r.student: r for r in _records(group, date, schedule=schedule, by_day=not schedule)}
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
			{"doctype": "Student Attendance", "student": student, "student_group": group, "date": date, "status": status, "course_schedule": schedule}
		)
		doc.flags.ignore_permissions = True
		doc.insert()
		doc.submit()
		changed += 1
	return changed


def summary(group: str) -> dict:
	"""Each student's attendance in the module so far, and the lessons held (a register a day where there was no
	timetable)"""
	from educore.academics.timetable import _t

	records = _records(group)
	times = {
		c.name: _t(c.from_time)
		for c in frappe.get_all(
			"Course Schedule", filters={"name": ("in", list({r.course_schedule for r in records if r.course_schedule}) or [""])}, fields=["name", "from_time"]
		)
	}
	by_student: dict[str, dict] = {}
	sessions: dict[str, dict] = {}
	for r in records:
		day = str(r.date)
		start = times.get(r.course_schedule) if r.course_schedule else None
		key = f"{day} {start or ''}"
		sessions.setdefault(key, {"date": day, "start_time": start, PRESENT: 0, ABSENT: 0, EXCUSED: 0})[r.status] += 1
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
			{"date": d["date"], "start_time": d["start_time"], "present": d[PRESENT], "absent": d[ABSENT], "excused": d[EXCUSED]}
			for d in sorted(sessions.values(), key=lambda d: (d["date"], d["start_time"] or ""), reverse=True)
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
