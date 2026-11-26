"""Timetables (educore.academics.timetable, educore.api.v1.timetable): no room, lecturer or student in two places at
once; each campus its own; everyone's own week"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.academics import timetable
from educore.api.v1 import timetable as api

OFFICER_WHK = "timetable-officer.whk@educore.localhost"
OFFICER_OSH = "timetable-officer.osh@educore.localhost"
STUDENT = "student1.whk@educore.localhost"


def _slot(**values):
	return frappe.get_doc({"doctype": "Timetable Slot", "kind": "Lecture", **values})


class TestTimetable(IntegrationTestCase):
	def setUp(self):
		self.slot = frappe.db.get_value(
			"Timetable Slot", {"campus": "Windhoek Campus"}, ["name", "student_group", "semester", "day", "start_time", "end_time", "room"], as_dict=True
		)
		if not self.slot or not frappe.db.exists("User", OFFICER_WHK):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("timetable_test")
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="timetable_test")

	def _same_time(self, group: str, room: str):
		s = self.slot
		return _slot(student_group=group, semester=s.semester, day=s.day, start_time=s.start_time, end_time=s.end_time, room=room)

	def _other_groups(self) -> list[str]:
		return frappe.get_all(
			"Student Group",
			filters={"campus": "Windhoek Campus", "academic_year": "2026", "name": ("!=", self.slot.student_group), "group_based_on": "Course"},
			pluck="name",
		)

	def _free_room(self) -> str:
		return frappe.get_all("Room", filters={"campus": "Windhoek Campus", "name": ("!=", self.slot.room)}, pluck="name")[0]

	def test_a_room_is_not_booked_twice(self):
		group = next(g for g in self._other_groups() if not (timetable.students(g) & timetable.students(self.slot.student_group)))
		with self.assertRaises(frappe.ValidationError) as caught:
			self._same_time(group, self.slot.room).insert()
		self.assertIn("is booked for", str(caught.exception))

	def test_a_student_is_not_in_two_classes_at_once(self):
		mine = timetable.students(self.slot.student_group)
		group = next((g for g in self._other_groups() if timetable.students(g) & mine), None)
		if not group:
			self.skipTest("no two classes share a student")
		with self.assertRaises(frappe.ValidationError) as caught:
			self._same_time(group, self._free_room()).insert()
		self.assertIn("also in", str(caught.exception))

	def test_a_lecturer_does_not_teach_two_classes_at_once(self):
		group = next(g for g in self._other_groups() if not (timetable.students(g) & timetable.students(self.slot.student_group)))
		instructor = (timetable.lecturers(self.slot.student_group) or [None])[0]
		if not instructor:
			self.skipTest("the class has no lecturer")
		doc = frappe.get_doc("Student Group", group)
		doc.set("instructors", [{"instructor": instructor}])
		doc.save(ignore_permissions=True)
		with self.assertRaises(frappe.ValidationError) as caught:
			self._same_time(group, self._free_room()).insert()
		self.assertIn("teaches", str(caught.exception))

	def test_the_hours_and_the_room_must_make_sense(self):
		s = self.slot
		other_campus_room = frappe.get_all("Room", filters={"campus": ("!=", "Windhoek Campus")}, pluck="name")[0]
		bad = [
			dict(start_time="10:00", end_time="09:00", room=s.room),
			dict(start_time="06:00", end_time="08:00", room=s.room),
			dict(start_time="19:00", end_time="20:00", room=other_campus_room),
		]
		for values in bad:
			self.assertRaises(frappe.ValidationError, _slot(student_group=s.student_group, semester=s.semester, day="Saturday", **values).insert)

	def test_the_officer_places_a_class_on_their_campus_and_is_warned_of_a_small_room(self):
		s = self.slot
		group = frappe.get_doc("Student Group", s.student_group)
		if len(timetable.students(s.student_group)) < 2:  # a class of two at least, so one seat is too few
			extra = frappe.get_all("Student", filters={"name": ("not in", list(timetable.students(s.student_group)) or [""])}, fields=["name", "student_name"], limit=1)[0]
			group.append("students", {"student": extra.name, "student_name": extra.student_name, "active": 1})
			group.flags.ignore_validate = True
			group.save(ignore_permissions=True)
		frappe.set_user(OFFICER_WHK)
		small = api.save_room({"room_name": "Seminar Room", "room_type": "Lecture room", "seating_capacity": 1, "campus": "Windhoek Campus"})
		room = next(r["name"] for r in small if r["room_name"] == "Seminar Room")
		result = api.save_slot({"student_group": s.student_group, "semester": s.semester, "day": "Saturday", "start_time": "09:00", "end_time": "10:00", "room": room})
		self.assertTrue(any("Seminar Room has 1 seats" in w for w in result["warnings"]))
		self.assertTrue(any(x["day"] == "Saturday" for x in result["page"]["slots"]))

		frappe.set_user(OFFICER_OSH)
		self.assertNotIn("Windhoek Campus", api.page()["campuses"])
		self.assertRaises(
			frappe.PermissionError, api.save_slot, {"student_group": s.student_group, "semester": s.semester, "day": "Saturday", "start_time": "11:00", "end_time": "12:00", "room": room}
		)
		frappe.set_user("registrar@educore.localhost")
		self.assertTrue(api.page()["slots"] is not None)
		self.assertRaises(frappe.PermissionError, api.delete_slot, s.name)

	def test_a_student_sees_their_own_week(self):
		frappe.set_user(STUDENT)
		week = api.mine()
		student = frappe.db.get_value("Student", {"user": STUDENT})
		groups = set(frappe.get_all("Student Group Student", filters={"student": student}, pluck="parent"))
		self.assertTrue(all(s["student_group"] in groups for s in week["slots"]))
		self.assertEqual(week["semester"], timetable.current_semester()[1])
