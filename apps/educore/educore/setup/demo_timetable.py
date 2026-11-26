"""EduCore Demo University's rooms and 2026 timetable (development only): rooms on each campus, and two weekly
times for every class in each semester it runs (computing courses practise in the computer laboratory), placed
where no room, lecturer or student clashes. Runs from demo_students.create after the course groups."""

import frappe

from educore.academics import timetable

#: (room, number, type, seats): every campus; the main campus has more
ROOMS = (
	("Lecture Room 1", "A101", "Lecture room", 60),
	("Lecture Room 2", "A102", "Lecture room", 40),
	("Computer Laboratory 1", "B201", "Computer laboratory", 30),
)
MAIN_CAMPUS_ROOMS = (
	("Science Laboratory", "C301", "Laboratory", 24),
	("Main Hall", "H001", "Hall", 200),
)
YEAR = "2026"
STARTS = ("08:00", "10:00", "12:00", "14:00", "16:00")


def create_rooms() -> int:
	made = 0
	for campus, main in frappe.get_all("Campus", fields=["name", "is_main_campus"], as_list=True):
		for room_name, number, kind, seats in ROOMS + (MAIN_CAMPUS_ROOMS if main else ()):
			if frappe.db.exists("Room", {"room_name": room_name, "campus": campus}):
				continue
			frappe.get_doc(
				{"doctype": "Room", "room_name": room_name, "room_number": number, "seating_capacity": str(seats), "campus": campus, "educore_room_type": kind}
			).insert(ignore_permissions=True)
			made += 1
	return made


def _place(group: str, semester: str, kind: str, rooms: list[str], taken_days: set[str]) -> bool:
	for day in timetable.DAYS[:5]:
		if day in taken_days:
			continue
		for start in STARTS:
			end = f"{int(start[:2]) + 2:02d}:00"
			for room in rooms:
				doc = frappe.get_doc(
					{"doctype": "Timetable Slot", "student_group": group, "semester": semester, "day": day, "start_time": start, "end_time": end, "room": room, "kind": kind}
				)
				try:
					doc.insert(ignore_permissions=True)
				except frappe.ValidationError:
					continue
				taken_days.add(day)
				return True
	return False


def create() -> int:
	from educore.api.v1.teaching_allocation import _semester_of

	create_rooms()
	placed = 0
	for g in frappe.get_all("Student Group", filters={"group_based_on": "Course", "academic_year": YEAR, "disabled": 0}, fields=["name", "course", "campus"], order_by="name"):
		if frappe.db.exists("Timetable Slot", {"student_group": g.name}):
			continue
		runs = _semester_of(g.course)
		lecture_rooms = frappe.get_all("Room", filters={"campus": g.campus, "educore_room_type": "Lecture room"}, pluck="name", order_by="room_name")
		labs = frappe.get_all("Room", filters={"campus": g.campus, "educore_room_type": "Computer laboratory"}, pluck="name")
		computing = (frappe.db.get_value("Course", g.course, "educore_course_code") or "").startswith("CMP")
		for semester in timetable.SEMESTERS:
			if runs not in (semester, "Year"):
				continue
			days: set[str] = set()
			placed += _place(g.name, semester, "Lecture", lecture_rooms, days)
			placed += _place(g.name, semester, "Practical" if computing and labs else "Tutorial", labs if computing and labs else lecture_rooms, days)
	return placed
