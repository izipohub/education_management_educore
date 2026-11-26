"""Examination timetables: sessions, each class's paper, its rooms and invigilators.

An Examination Session is a period of examinations for a semester: the main examinations, or the supplementary and
special sitting after them. In it each campus's Examinations Officer schedules every class's paper (Examination
Paper): the date and hours, the rooms (Education's Room, educore.academics.timetable) and the invigilators. The
Registrar publishes the session; from then students see their papers on My studies and invigilators their duties on
My modules.

Who sits a paper: at the main examinations the class; at the supplementary sitting only the students writing a
supplementary or special examination in it (educore.academics.results). A paper is refused when:

- a student would sit two papers at once;
- the papers in a room at the same time have more students than it has seats (papers may share a hall);
- an invigilator would be in two rooms at once;
- it falls outside the session's days, or in a room on another campus.
"""

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_time, getdate, now_datetime

from educore.academics.timetable import EARLIEST, LATEST, _t, room_name

MAIN, SECOND = "Main", "Supplementary and special"
DRAFT, PUBLISHED = "Draft", "Published"


def validate_session(doc, method=None):
	doc.session_name = (doc.session_name or "").strip()
	if getdate(doc.ends_on) < getdate(doc.starts_on):
		frappe.throw(_("The last day is before the first"))
	year = frappe.db.get_value("Academic Year", doc.academic_year, ["year_start_date", "year_end_date"], as_dict=True)
	if year and year.year_start_date and not (getdate(year.year_start_date) <= getdate(doc.starts_on) and getdate(doc.ends_on) <= getdate(add_days(year.year_end_date, 60))):
		frappe.throw(_("The session is not in the {0} academic year").format(doc.academic_year))
	if doc.has_value_changed("starts_on") or doc.has_value_changed("ends_on"):
		outside = frappe.db.count(
			"Examination Paper", {"session": doc.name, "exam_date": ("not between", (doc.starts_on, doc.ends_on))}
		) if not doc.is_new() else 0
		if outside:
			frappe.throw(_("{0} papers are scheduled outside these days: move them first").format(outside))


def sitters(paper_or_group: str, session_kind: str) -> set[str]:
	"""Who writes the paper: the class, or at the supplementary sitting those writing a second examination"""
	group = paper_or_group
	if session_kind == MAIN:
		return set(frappe.get_all("Student Group Student", filters={"parent": group, "active": 1}, pluck="student"))
	from educore.academics import results

	sheet = frappe.db.get_value("Mark Sheet", {"student_group": group}, "name")
	if not sheet:
		return set()
	return {e.student for e in frappe.get_doc("Mark Sheet", sheet).entries if results.second_sitting(e)}


def _rooms(doc) -> list[str]:
	return [r.room for r in doc.rooms]


def _invigilators(doc) -> list[str]:
	return [r.user for r in doc.invigilators]


def _at_once(doc) -> list:
	"""Other papers on the same day whose hours overlap this one's (any session)"""
	names = frappe.db.sql(
		"""select name from `tabExamination Paper` where exam_date = %(date)s and name != %(name)s
		and start_time < %(end)s and end_time > %(start)s""",
		{"date": doc.exam_date, "name": doc.name or "", "start": doc.start_time, "end": doc.end_time},
		pluck=True,
	)
	return [frappe.get_doc("Examination Paper", n) for n in names]


def kind_of(session: str) -> str:
	return frappe.get_cached_value("Examination Session", session, "kind") or MAIN


def problems(doc) -> list[str]:
	"""What stops the paper being scheduled so, in plain words (empty: nothing)"""
	found = []
	mine = sitters(doc.student_group, kind_of(doc.session))
	rooms = _rooms(doc)
	seats_needed = {r: len(mine) for r in rooms}
	for other in _at_once(doc):
		hours = f"{_t(other.start_time)}–{_t(other.end_time)}"
		if other.student_group == doc.student_group:
			found.append(_("{0} already writes at {1}").format(doc.student_group, hours))
			continue
		shared = mine & sitters(other.student_group, kind_of(other.session))
		if shared:
			found.append(
				_("{0} students also write {1} at {2}").format(len(shared), other.student_group, hours)
				if len(shared) > 1
				else _("A student also writes {0} at {1}").format(other.student_group, hours)
			)
		for room in set(rooms) & set(_rooms(other)):
			# the other paper's students are split over its rooms; counted in full in each shared room, to be safe
			seats_needed[room] += len(sitters(other.student_group, kind_of(other.session)))
		for user in set(_invigilators(doc)) & set(_invigilators(other)):
			if set(rooms) != set(_rooms(other)):
				found.append(
					_("{0} invigilates {1} at {2} in another room").format(frappe.utils.get_fullname(user), other.student_group, hours)
				)
	total_seats = sum(cint(frappe.db.get_value("Room", r, "seating_capacity")) for r in rooms)
	shared_rooms = [r for r in rooms if seats_needed[r] > len(mine)]
	for room in shared_rooms:
		seats = cint(frappe.db.get_value("Room", room, "seating_capacity"))
		if seats_needed[room] > seats:
			found.append(_("{0} has {1} seats for {2} students writing at that time").format(room_name(room), seats, seats_needed[room]))
	if rooms and not shared_rooms and len(mine) > total_seats:
		found.append(_("The rooms have {0} seats for {1} students").format(total_seats, len(mine)))
	return list(dict.fromkeys(found))


def validate_paper(doc, method=None):
	session = frappe.db.get_value("Examination Session", doc.session, ["starts_on", "ends_on", "academic_year", "semester", "kind"], as_dict=True)
	if not session:
		frappe.throw(_("Unknown session {0}").format(doc.session))
	group = frappe.db.get_value("Student Group", doc.student_group, ["campus", "course", "academic_year"], as_dict=True)
	if not group:
		frappe.throw(_("Unknown class {0}").format(doc.student_group))
	if group.academic_year != session.academic_year:
		frappe.throw(_("{0} is not a class of {1}").format(doc.student_group, session.academic_year))
	doc.campus, doc.course = group.campus, group.course
	if frappe.db.exists("Examination Paper", {"session": doc.session, "student_group": doc.student_group, "name": ("!=", doc.name or "")}):
		frappe.throw(_("{0} has a paper in this session already").format(doc.student_group))
	if not (getdate(session.starts_on) <= getdate(doc.exam_date) <= getdate(session.ends_on)):
		frappe.throw(_("The session runs from {0} to {1}").format(frappe.utils.formatdate(session.starts_on), frappe.utils.formatdate(session.ends_on)))
	if getdate(doc.exam_date).weekday() == 6:
		frappe.throw(_("No examinations on a Sunday"))
	if not doc.start_time or not doc.end_time or get_time(doc.end_time) <= get_time(doc.start_time):
		frappe.throw(_("The paper ends after it starts"))
	if get_time(doc.start_time) < get_time(EARLIEST) or get_time(doc.end_time) > get_time(LATEST):
		frappe.throw(_("Papers are between {0} and {1}").format(EARLIEST, LATEST))
	if not doc.rooms:
		frappe.throw(_("Choose the room"))
	for r in doc.rooms:
		if frappe.db.get_value("Room", r.room, "campus") != doc.campus:
			frappe.throw(_("{0} is not on {1}").format(room_name(r.room), doc.campus))
	seen = set()
	doc.invigilators = [r for r in doc.invigilators if not (r.user in seen or seen.add(r.user))]
	found = problems(doc)
	if found:
		frappe.throw(_("Not possible:") + "<br>" + "<br>".join(f"• {p}" for p in found), title=_("Clash"))


def publish(session: str):
	doc = frappe.get_doc("Examination Session", session)
	if not frappe.db.exists("Examination Paper", {"session": session}):
		frappe.throw(_("No papers are scheduled in {0} yet").format(session))
	doc.db_set({"status": PUBLISHED, "published_on": now_datetime()})


# --- reading ---------------------------------------------------------------------------------------------


def papers(filters: dict) -> list[dict]:
	out = []
	for name in frappe.get_all("Examination Paper", filters=filters, pluck="name", limit=0):
		p = frappe.get_doc("Examination Paper", name)
		code, course_name = frappe.db.get_value("Course", p.course, ["educore_course_code", "course_name"]) or (p.course, p.course)
		out.append(
			{
				"name": p.name,
				"session": p.session,
				"student_group": p.student_group,
				"code": code or p.course,
				"course_name": course_name,
				"campus": p.campus,
				"exam_date": str(p.exam_date),
				"start_time": _t(p.start_time),
				"end_time": _t(p.end_time),
				"rooms": [{"room": r.room, "room_name": room_name(r.room)} for r in p.rooms],
				"invigilators": [{"user": r.user, "full_name": r.full_name or frappe.utils.get_fullname(r.user)} for r in p.invigilators],
				"sitting": len(sitters(p.student_group, kind_of(p.session))),
			}
		)
	return sorted(out, key=lambda p: (p["exam_date"], p["start_time"], p["code"]))


def published_sessions() -> list[dict]:
	"""The published sessions of the latest year that has any (a student or invigilator sees the year's, written or to come)"""
	year = frappe.db.get_value("Examination Session", {"status": PUBLISHED}, "academic_year", order_by="starts_on desc")
	return frappe.get_all(
		"Examination Session", filters={"status": PUBLISHED, "academic_year": year}, fields=["name", "kind"]
	) if year else []


def _written(p: dict) -> dict:
	p["written"] = getdate(p["exam_date"]) < getdate()
	return p


def of_student(student: str) -> list[dict]:
	"""The student's papers in the published sessions"""
	groups = list(set(frappe.get_all("Student Group Student", filters={"student": student, "active": 1}, pluck="parent")))
	out = []
	for s in published_sessions():
		for p in papers({"session": s.name, "student_group": ("in", groups or [""])}):
			if student in sitters(p["student_group"], s.kind):
				out.append(_written(p))
	return sorted(out, key=lambda p: (p["exam_date"], p["start_time"]))


def duties_of(user: str) -> list[dict]:
	"""The papers this member of staff invigilates in the published sessions"""
	sessions = [s.name for s in published_sessions()]
	names = frappe.get_all("Examination Invigilator", filters={"user": user, "parenttype": "Examination Paper"}, pluck="parent")
	if not names or not sessions:
		return []
	return [_written(p) for p in papers({"name": ("in", names), "session": ("in", sessions)})]
