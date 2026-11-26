"""EduCore Demo University's Semester 2 2026 examinations (development only): a published session with a paper for
every class examined in it, in each campus's largest rooms, invigilated by the class's lecturer, placed where no
student, room or invigilator clashes. Runs from demo_students.create after the timetable."""

import frappe
from frappe.utils import add_days, getdate

from educore.academics import exam_timetable as et
from educore.academics.lecturers import user_of

SESSION = "Semester 2 examinations 2026"
STARTS, ENDS = "2026-11-23", "2026-12-11"
TIMES = (("08:30", "11:30"), ("14:00", "17:00"))


def _days() -> list[str]:
	day, out = getdate(STARTS), []
	while day <= getdate(ENDS):
		if day.weekday() < 5:
			out.append(str(day))
		day = add_days(day, 1)
	return out


def _place(session: str, group: str, rooms: list[str], invigilators: list[str]) -> bool:
	for day in _days():
		for start, end in TIMES:
			for room in rooms:
				doc = frappe.get_doc(
					{
						"doctype": "Examination Paper",
						"session": session,
						"student_group": group,
						"exam_date": day,
						"start_time": start,
						"end_time": end,
						"rooms": [{"room": room}],
						"invigilators": [{"user": u, "full_name": frappe.utils.get_fullname(u)} for u in invigilators],
					}
				)
				try:
					doc.insert(ignore_permissions=True)
				except frappe.ValidationError:
					continue
				return True
	return False


def create() -> int:
	from educore.api.v1.exam_timetable import _to_schedule

	if frappe.db.exists("Examination Session", SESSION):
		return 0
	frappe.get_doc(
		{
			"doctype": "Examination Session",
			"session_name": SESSION,
			"academic_year": "2026",
			"semester": "Semester 2",
			"kind": et.MAIN,
			"starts_on": STARTS,
			"ends_on": ENDS,
		}
	).insert(ignore_permissions=True)
	session = {"academic_year": "2026", "semester": "Semester 2", "kind": et.MAIN}
	placed = 0
	for campus in frappe.get_all("Campus", pluck="name", order_by="name"):
		# the largest rooms first: a hall seats several papers at once
		rooms = [
			r.name
			for r in sorted(
				frappe.get_all("Room", filters={"campus": campus, "educore_disabled": 0}, fields=["name", "seating_capacity"]),
				key=lambda r: -int(r.seating_capacity or 0),
			)
		][:2]
		for c in _to_schedule(session, campus, set()):
			lecturers = frappe.get_all("Student Group Instructor", filters={"parent": c["group"]}, pluck="instructor")
			users = [u for u in (user_of(i) for i in lecturers[:1]) if u]
			placed += _place(SESSION, c["group"], rooms, users)
	if placed:
		et.publish(SESSION)
	return placed
