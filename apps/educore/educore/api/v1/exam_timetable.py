"""Examination timetables (educore.academics.exam_timetable): the Examinations Officer schedules each class's paper in
a session (date, hours, rooms, invigilators); the Registrar publishes the session; students then see their papers and
invigilators their duties."""

import frappe
from frappe import _
from frappe.utils import cint, getdate

from educore.academics import exam_timetable as et
from educore.academics.timetable import SEMESTERS
from educore.access.scope import campuses

EDIT_ROLES = ("Examinations Officer", "System Manager")
PUBLISH_ROLES = ("Registrar", "System Manager")
READ_ROLES = (*EDIT_ROLES, *PUBLISH_ROLES, "Registry Officer", "Head of Department", "Dean", "Faculty Officer", "Campus Director", "Timetable Officer")


def _has(roles) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _require(roles, message=None):
	if not _has(roles):
		frappe.throw(message or _("Examination timetables are the Examinations Officer's"), frappe.PermissionError)


def _in_scope(campus: str | None):
	if campus not in campuses():
		frappe.throw(_("Not permitted on {0}").format(campus), frappe.PermissionError)


def _sessions(year: str) -> list[dict]:
	rows = frappe.get_all(
		"Examination Session",
		filters={"academic_year": year},
		fields=["name", "academic_year", "semester", "kind", "starts_on", "ends_on", "status"],
		order_by="starts_on asc",
	)
	return [{**r, "starts_on": str(r.starts_on), "ends_on": str(r.ends_on), "papers": frappe.db.count("Examination Paper", {"session": r.name})} for r in rows]


def _to_schedule(session: dict, campus: str, scheduled: set[str]) -> list[dict]:
	"""The campus's classes examined in the session that have no paper yet; a full-year course at the end of the year"""
	from educore.api.v1.teaching_allocation import _semester_of

	rows = []
	for g in frappe.get_all(
		"Student Group",
		filters={"group_based_on": "Course", "campus": campus, "academic_year": session["academic_year"], "disabled": 0},
		fields=["name", "course"],
		order_by="name asc",
	):
		if g.name in scheduled:
			continue
		runs = _semester_of(g.course)
		if runs != session["semester"] and not (runs == "Year" and session["semester"] == SEMESTERS[-1]):
			continue
		sitting = len(et.sitters(g.name, session["kind"]))
		if not sitting:
			continue
		code, course_name = frappe.db.get_value("Course", g.course, ["educore_course_code", "course_name"])
		rows.append({"group": g.name, "code": code or g.course, "course_name": course_name, "sitting": sitting})
	return rows


def _rooms(campus: str) -> list[dict]:
	return [
		{"name": r.name, "room_name": r.room_name, "seating_capacity": cint(r.seating_capacity)}
		for r in frappe.get_all(
			"Room", filters={"campus": campus, "educore_disabled": 0}, fields=["name", "room_name", "seating_capacity"], order_by="room_name asc"
		)
	]


def _invigilators(campus: str) -> list[dict]:
	"""Who may invigilate: the lecturers on the campus"""
	from educore.academics.lecturers import user_of

	names = frappe.get_all("Unit Campus", filters={"parenttype": "Instructor", "campus": campus}, pluck="parent")
	out = {}
	for i in frappe.get_all("Instructor", filters={"name": ("in", names or [""]), "status": ("!=", "Left")}, fields=["name", "instructor_name"]):
		user = user_of(i.name)
		if user:
			out[user] = {"user": user, "full_name": i.instructor_name}
	return sorted(out.values(), key=lambda r: r["full_name"])


@frappe.whitelist(methods=["GET"])
def page(academic_year: str | None = None, session: str | None = None, campus: str | None = None) -> dict:
	_require(READ_ROLES)
	from educore.api.v1.teaching_allocation import _years

	years = _years()
	if session and frappe.db.exists("Examination Session", session):
		academic_year = frappe.db.get_value("Examination Session", session, "academic_year")
	academic_year = academic_year if academic_year in years else (years[0] if years else None)
	sessions = _sessions(academic_year) if academic_year else []
	chosen = next((s for s in sessions if s["name"] == session), None)
	if not chosen and sessions:
		# the first session not yet over, else the last
		today = getdate()
		chosen = next((s for s in sessions if getdate(s["ends_on"]) >= today), sessions[-1])
	mine = sorted(campuses())
	campus = campus if campus in mine else (mine[0] if mine else None)
	papers = et.papers({"session": chosen["name"], "campus": campus}) if chosen and campus else []
	return {
		"academic_year": academic_year,
		"academic_years": years,
		"sessions": sessions,
		"session": chosen,
		"campus": campus,
		"campuses": mine,
		"papers": papers,
		"to_schedule": _to_schedule(chosen, campus, {p["student_group"] for p in papers}) if chosen and campus else [],
		"rooms": _rooms(campus) if campus else [],
		"invigilators": _invigilators(campus) if campus else [],
		"semesters": SEMESTERS,
		"kinds": (et.MAIN, et.SECOND),
		"can_edit": _has(EDIT_ROLES),
		"can_publish": _has(PUBLISH_ROLES),
	}


@frappe.whitelist(methods=["POST"])
def save_session(session: dict | str) -> dict:
	_require(EDIT_ROLES)
	data = frappe.parse_json(session)
	doc = frappe.get_doc("Examination Session", data["name"]) if data.get("name") else frappe.new_doc("Examination Session")
	fields = ("starts_on", "ends_on") if not doc.is_new() else ("session_name", "academic_year", "semester", "kind", "starts_on", "ends_on")
	for field in fields:
		if field in data:
			doc.set(field, data[field])
	doc.save(ignore_permissions=True)
	return page(doc.academic_year, doc.name, data.get("campus"))


@frappe.whitelist(methods=["POST"])
def save_paper(paper: dict | str) -> dict:
	"""A class's paper, new or moved; refused on a clash"""
	_require(EDIT_ROLES)
	data = frappe.parse_json(paper)
	doc = frappe.get_doc("Examination Paper", data["name"]) if data.get("name") else frappe.new_doc("Examination Paper")
	if doc.is_new():
		doc.session, doc.student_group = data.get("session"), data.get("student_group")
	_in_scope(frappe.db.get_value("Student Group", doc.student_group, "campus"))
	for field in ("exam_date", "start_time", "end_time"):
		if field in data:
			doc.set(field, data[field])
	if "rooms" in data:
		doc.set("rooms", [{"room": r} for r in data["rooms"] or []])
	if "invigilators" in data:
		doc.set("invigilators", [{"user": u, "full_name": frappe.utils.get_fullname(u)} for u in data["invigilators"] or []])
	doc.save(ignore_permissions=True)
	return page(None, doc.session, doc.campus)


@frappe.whitelist(methods=["POST"])
def delete_paper(name: str) -> dict:
	_require(EDIT_ROLES)
	doc = frappe.get_doc("Examination Paper", name)
	_in_scope(doc.campus)
	frappe.delete_doc("Examination Paper", name, ignore_permissions=True)
	return page(None, doc.session, doc.campus)


@frappe.whitelist(methods=["POST"])
def publish(session: str, campus: str | None = None) -> dict:
	"""The Registrar publishes the session: students see their papers, invigilators their duties"""
	_require(PUBLISH_ROLES, _("The Registrar publishes the examination timetable"))
	et.publish(session)
	return page(None, session, campus)


@frappe.whitelist(methods=["GET"])
def mine() -> dict:
	"""The signed-in student's papers and the signed-in member of staff's invigilation, in published sessions"""
	student = frappe.db.get_value("Student", {"user": frappe.session.user})
	return {
		"papers": et.of_student(student) if student else [],
		"duties": et.duties_of(frappe.session.user),
	}

