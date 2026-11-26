"""Timetables, for the Timetable Officer and everyone who reads them: each campus's week in a semester, the classes
still to place, the campus's rooms; and each lecturer's and student's own week (educore.academics.timetable)."""

import frappe
from frappe import _
from frappe.utils import cint

from educore.academics import timetable
from educore.access.scope import campuses

#: who sets the timetable
EDIT_ROLES = ("Timetable Officer", "System Manager")
#: who keeps the rooms
ROOM_ROLES = ("Timetable Officer", "Facilities Manager", "System Manager")
READ_ROLES = (
	*EDIT_ROLES, "Facilities Manager", "Head of Department", "Dean", "Faculty Officer", "Registrar", "Registry Officer",
	"Campus Director", "Examinations Officer", "Executive Management",
)


def _has(roles) -> bool:
	return bool(set(frappe.get_roles()) & set(roles))


def _require(roles, what: str = ""):
	if not _has(roles):
		frappe.throw(what or _("Timetables are the Timetable Officer's"), frappe.PermissionError)


def _in_scope(campus: str | None):
	if campus not in campuses():
		frappe.throw(_("Not permitted on {0}").format(campus), frappe.PermissionError)


def _rooms(campus: str) -> list[dict]:
	return [
		{**r, "seating_capacity": cint(r.seating_capacity), "disabled": bool(r.educore_disabled)}
		for r in frappe.get_all(
			"Room",
			filters={"campus": campus},
			fields=["name", "room_name", "room_number", "seating_capacity", "educore_room_type as room_type", "educore_disabled"],
			order_by="room_name asc",
		)
	]


def _classes(campus: str, academic_year: str, semester: str, placed: list[dict]) -> list[dict]:
	"""The campus's classes that run in the semester (or all year), with how many weekly hours they have"""
	from educore.api.v1.teaching_allocation import _semester_of

	hours: dict[str, float] = {}
	for s in placed:
		h, m = map(int, s["start_time"].split(":"))
		h2, m2 = map(int, s["end_time"].split(":"))
		hours[s["student_group"]] = hours.get(s["student_group"], 0) + ((h2 * 60 + m2) - (h * 60 + m)) / 60
	rows = []
	for g in frappe.get_all(
		"Student Group",
		filters={"group_based_on": "Course", "campus": campus, "academic_year": academic_year, "disabled": 0},
		fields=["name", "course"],
		order_by="name asc",
	):
		when = _semester_of(g.course)
		if when not in (semester, "Year"):
			continue
		code, course_name = frappe.db.get_value("Course", g.course, ["educore_course_code", "course_name"])
		rows.append(
			{
				"group": g.name,
				"code": code or g.course,
				"course_name": course_name,
				"runs": when,
				"students": len(timetable.students(g.name)),
				"lecturers": frappe.get_all("Student Group Instructor", filters={"parent": g.name}, pluck="instructor_name"),
				"hours": round(hours.get(g.name, 0), 2),
			}
		)
	return rows


@frappe.whitelist(methods=["GET"])
def page(campus: str | None = None, academic_year: str | None = None, semester: str | None = None) -> dict:
	_require(READ_ROLES)
	from educore.api.v1.teaching_allocation import _years

	mine = sorted(campuses())
	campus = campus if campus in mine else (mine[0] if mine else None)
	years = _years()
	current_year, current_semester = timetable.current_semester()
	academic_year = academic_year or (current_year if current_year in years else (years[0] if years else None))
	semester = semester if semester in timetable.SEMESTERS else current_semester
	placed = timetable.slots({"campus": campus, "academic_year": academic_year, "semester": semester}) if campus and academic_year else []
	return {
		"campus": campus,
		"campuses": mine,
		"academic_year": academic_year,
		"academic_years": years,
		"semester": semester,
		"semesters": timetable.SEMESTERS,
		"days": timetable.DAYS,
		"kinds": timetable.KINDS,
		"room_types": timetable.ROOM_TYPES,
		"slots": placed,
		"classes": _classes(campus, academic_year, semester, placed) if campus and academic_year else [],
		"rooms": _rooms(campus) if campus else [],
		"can_edit": _has(EDIT_ROLES),
		"can_edit_rooms": _has(ROOM_ROLES),
	}


@frappe.whitelist(methods=["POST"])
def save_slot(slot: dict | str) -> dict:
	"""A class's weekly time, new or changed; refused on a clash; with a warning when the room is too small"""
	_require(EDIT_ROLES)
	data = frappe.parse_json(slot)
	campus = frappe.db.get_value("Student Group", data.get("student_group"), "campus")
	_in_scope(campus)
	doc = frappe.get_doc("Timetable Slot", data["name"]) if data.get("name") else frappe.new_doc("Timetable Slot")
	for field in ("student_group", "semester", "day", "start_time", "end_time", "room", "kind"):
		if field in data:
			doc.set(field, data[field])
	doc.save(ignore_permissions=True)
	return {"page": page(doc.campus, doc.academic_year, doc.semester), "warnings": timetable.warnings(doc)}


@frappe.whitelist(methods=["POST"])
def delete_slot(name: str) -> dict:
	_require(EDIT_ROLES)
	doc = frappe.get_doc("Timetable Slot", name)
	_in_scope(doc.campus)
	frappe.delete_doc("Timetable Slot", name, ignore_permissions=True)
	return page(doc.campus, doc.academic_year, doc.semester)


@frappe.whitelist(methods=["POST"])
def save_room(room: dict | str) -> list[dict]:
	"""A room on a campus: its name, number, type and seats; a room no longer used is marked so, never deleted"""
	_require(ROOM_ROLES, _("Rooms are kept by the Timetable Officer and the Facilities Manager"))
	data = frappe.parse_json(room)
	doc = frappe.get_doc("Room", data["name"]) if data.get("name") else frappe.new_doc("Room")
	campus = data.get("campus") or doc.get("campus")
	_in_scope(campus)
	name = (data.get("room_name") or "").strip()
	if not name:
		frappe.throw(_("Give the room a name"))
	if data.get("room_type") not in timetable.ROOM_TYPES:
		frappe.throw(_("Choose the type of room"))
	if cint(data.get("seating_capacity")) < 1:
		frappe.throw(_("Enter the number of seats"))
	if frappe.db.exists("Room", {"room_name": name, "campus": campus, "name": ("!=", doc.name or "")}):
		frappe.throw(_("{0} has a room called {1} already").format(campus, name))
	doc.update(
		{
			"room_name": name,
			"room_number": (data.get("room_number") or "").strip() or None,
			"seating_capacity": str(cint(data.get("seating_capacity"))),
			"campus": campus,
			"educore_room_type": data["room_type"],
			"educore_disabled": 1 if data.get("disabled") else 0,
		}
	)
	doc.save(ignore_permissions=True)
	return _rooms(campus)


@frappe.whitelist(methods=["GET"])
def mine() -> dict:
	"""The signed-in lecturer's or student's week this semester"""
	from educore.academics.lecturers import instructors_of

	user = frappe.session.user
	year, semester = timetable.current_semester()
	groups: set[str] = set()
	student = frappe.db.get_value("Student", {"user": user})
	if student:
		groups |= set(frappe.get_all("Student Group Student", filters={"student": student, "active": 1}, pluck="parent"))
	instructors = instructors_of(user)
	if instructors:
		groups |= set(frappe.get_all("Student Group Instructor", filters={"instructor": ("in", instructors)}, pluck="parent"))
	return {"academic_year": year, "semester": semester, "slots": timetable.week_of_groups(sorted(groups), year, semester)}
