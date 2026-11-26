"""Timetables: each class's weekly times in a semester, in a room on its campus.

A class is a course's Student Group on a campus for the year (educore.api.v1.teaching_allocation). The Timetable
Officer gives it its weekly times for a semester (Timetable Slot: day, hours, room, lecture, practical or tutorial); a
full-year course has times in both semesters. Rooms are Education's Room, with EduCore's campus and room type
(lecture room, laboratory, computer laboratory, hall), kept by the Timetable Officer and the Facilities Manager.

A time is refused when it puts anyone in two places at once in that semester: the room booked by another class, a
lecturer of the class teaching another class, or a student registered for both classes. A room with fewer seats than
the class has students is a warning, not a refusal (a class may meet in parts).
"""

import frappe
from frappe import _
from frappe.utils import cint, get_time

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday")
SEMESTERS = ("Semester 1", "Semester 2")
KINDS = ("Lecture", "Practical", "Tutorial")
ROOM_TYPES = ("Lecture room", "Laboratory", "Computer laboratory", "Hall")
EARLIEST, LATEST = "07:00", "21:00"


def _t(value) -> str:
	"""HH:MM"""
	return get_time(value).strftime("%H:%M")


def _overlapping(doc) -> list:
	"""Other slots on the same day and semester of the year whose hours overlap this one's"""
	return frappe.db.sql(
		"""select ts.name, ts.student_group, ts.room, ts.start_time, ts.end_time
		from `tabTimetable Slot` ts
		where ts.academic_year = %(year)s and ts.semester = %(semester)s and ts.day = %(day)s and ts.name != %(name)s
		and ts.start_time < %(end)s and ts.end_time > %(start)s""",
		{
			"year": doc.academic_year,
			"semester": doc.semester,
			"day": doc.day,
			"name": doc.name or "",
			"start": doc.start_time,
			"end": doc.end_time,
		},
		as_dict=True,
	)


def lecturers(group: str) -> list[str]:
	return frappe.get_all("Student Group Instructor", filters={"parent": group}, pluck="instructor")


def students(group: str) -> set[str]:
	return set(frappe.get_all("Student Group Student", filters={"parent": group, "active": 1}, pluck="student"))


def room_name(room: str | None) -> str:
	return (frappe.db.get_value("Room", room, "room_name") if room else None) or room or ""


def clashes(doc) -> list[str]:
	"""Who would be in two places at once, in plain words (empty: none)"""
	found = []
	others = _overlapping(doc)
	if not others:
		return found
	mine_lecturers = set(lecturers(doc.student_group))
	mine_students = students(doc.student_group)
	for other in others:
		hours = f"{_t(other.start_time)}–{_t(other.end_time)}"
		if other.room == doc.room:
			found.append(_("{0} is booked for {1} on {2}, {3}").format(room_name(doc.room), other.student_group, doc.day, hours))
		if other.student_group == doc.student_group:
			found.append(_("{0} already meets on {1}, {2}").format(doc.student_group, doc.day, hours))
			continue
		both = mine_lecturers & set(lecturers(other.student_group))
		for instructor in sorted(both):
			name = frappe.db.get_value("Instructor", instructor, "instructor_name") or instructor
			found.append(_("{0} teaches {1} on {2}, {3}").format(name, other.student_group, doc.day, hours))
		shared = mine_students & students(other.student_group)
		if shared:
			found.append(
				_("{0} students are also in {1} on {2}, {3}").format(len(shared), other.student_group, doc.day, hours)
				if len(shared) > 1
				else _("A student is also in {0} on {1}, {2}").format(other.student_group, doc.day, hours)
			)
	return list(dict.fromkeys(found))


def warnings(doc) -> list[str]:
	seats = cint(frappe.db.get_value("Room", doc.room, "seating_capacity"))
	size = len(students(doc.student_group))
	if seats and size > seats:
		return [_("{0} has {1} seats for {2} students").format(room_name(doc.room), seats, size)]
	return []


def validate_slot(doc, method=None):
	if doc.day not in DAYS:
		frappe.throw(_("Choose the day"))
	if doc.semester not in SEMESTERS:
		frappe.throw(_("Choose the semester"))
	if not doc.start_time or not doc.end_time or get_time(doc.end_time) <= get_time(doc.start_time):
		frappe.throw(_("The class ends after it starts"))
	if get_time(doc.start_time) < get_time(EARLIEST) or get_time(doc.end_time) > get_time(LATEST):
		frappe.throw(_("Classes are between {0} and {1}").format(EARLIEST, LATEST))
	group = frappe.db.get_value("Student Group", doc.student_group, ["campus", "academic_year", "course"], as_dict=True)
	if not group:
		frappe.throw(_("Unknown class {0}").format(doc.student_group))
	doc.campus, doc.academic_year, doc.course = group.campus, group.academic_year, group.course
	room_campus, disabled = frappe.db.get_value("Room", doc.room, ["campus", "educore_disabled"]) or (None, None)
	if room_campus != doc.campus:
		frappe.throw(_("{0} is not on {1}").format(room_name(doc.room), doc.campus))
	if disabled and doc.has_value_changed("room"):
		frappe.throw(_("{0} is not in use").format(room_name(doc.room)))
	found = clashes(doc)
	if found:
		frappe.throw(_("Two places at once:") + "<br>" + "<br>".join(f"• {c}" for c in found), title=_("Clash"))


# --- reading ---------------------------------------------------------------------------------------------


def current_semester(academic_year: str | None = None) -> tuple[str | None, str]:
	"""The academic year and semester today falls in (else the first semester of the latest year)"""
	today = frappe.utils.nowdate()
	term = frappe.db.get_value(
		"Academic Term",
		{"term_start_date": ("<=", today), "term_end_date": (">=", today), **({"academic_year": academic_year} if academic_year else {})},
		["academic_year", "term_name"],
		as_dict=True,
	)
	if term and term.term_name in SEMESTERS:
		return term.academic_year, term.term_name
	return academic_year, SEMESTERS[0]


def slots(filters: dict) -> list[dict]:
	rows = frappe.get_all(
		"Timetable Slot",
		filters=filters,
		fields=["name", "student_group", "course", "campus", "academic_year", "semester", "day", "start_time", "end_time", "room", "kind"],
		limit=0,
	)
	codes = {
		c.name: c
		for c in frappe.get_all(
			"Course", filters={"name": ("in", list({r.course for r in rows}) or [""])}, fields=["name", "educore_course_code", "course_name"]
		)
	}
	out = []
	for r in rows:
		names = frappe.get_all("Student Group Instructor", filters={"parent": r.student_group}, pluck="instructor_name")
		course = codes.get(r.course) or frappe._dict()
		out.append(
			{
				**r,
				"start_time": _t(r.start_time),
				"end_time": _t(r.end_time),
				"code": course.get("educore_course_code") or r.course,
				"course_name": course.get("course_name") or r.course,
				"lecturers": names,
				"room_name": room_name(r.room),
			}
		)
	return sorted(out, key=lambda s: (DAYS.index(s["day"]), s["start_time"], s["code"]))


def week_of_groups(groups: list[str], academic_year: str | None, semester: str) -> list[dict]:
	if not groups:
		return []
	return slots({"student_group": ("in", groups), "semester": semester, **({"academic_year": academic_year} if academic_year else {})})
