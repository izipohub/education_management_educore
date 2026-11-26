"""Examination timetables (educore.academics.exam_timetable, educore.api.v1.exam_timetable): papers, clashes, publishing"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.academics import exam_timetable as et
from educore.api.v1 import exam_timetable as api

CAMPUS = "Windhoek Campus"
SESSION = "Test examinations"
DAY = "2027-01-06"  # a Wednesday, after the demo's session


def _groups_sharing_a_student() -> tuple[str, str, str] | None:
	row = frappe.db.sql(
		"""select a.parent, b.parent, a.student from `tabStudent Group Student` a
		join `tabStudent Group Student` b on b.student = a.student and b.parent > a.parent and b.active = 1
		join `tabStudent Group` ga on ga.name = a.parent join `tabStudent Group` gb on gb.name = b.parent
		where a.active = 1 and ga.group_based_on = 'Course' and gb.group_based_on = 'Course' and ga.academic_year = '2026'
		and gb.academic_year = '2026' and ga.campus = %(c)s and gb.campus = %(c)s limit 1""",
		{"c": CAMPUS},
	)
	return row[0] if row else None


class TestExamTimetable(IntegrationTestCase):
	def setUp(self):
		self.shared = _groups_sharing_a_student()
		self.rooms = frappe.get_all("Room", filters={"campus": CAMPUS}, pluck="name", order_by="room_name")
		if not self.shared or len(self.rooms) < 2:
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("exam_tt_test")
		frappe.set_user("Administrator")
		frappe.get_doc(
			{
				"doctype": "Examination Session",
				"session_name": SESSION,
				"academic_year": "2026",
				"semester": "Semester 2",
				"kind": et.MAIN,
				"starts_on": "2027-01-04",
				"ends_on": "2027-01-15",
			}
		).insert(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="exam_tt_test")

	def _paper(self, group, room=None, start="09:00", end="12:00", day=DAY, invigilators=()):
		return frappe.get_doc(
			{
				"doctype": "Examination Paper",
				"session": SESSION,
				"student_group": group,
				"exam_date": day,
				"start_time": start,
				"end_time": end,
				"rooms": [{"room": room or self.rooms[0]}],
				"invigilators": [{"user": u} for u in invigilators],
			}
		)

	def test_a_student_cannot_sit_two_papers_at_once(self):
		a, b, _student = self.shared
		self._paper(a).insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, self._paper(b, self.rooms[1]).insert, ignore_permissions=True)
		self._paper(b, self.rooms[1], "13:00", "16:00").insert(ignore_permissions=True)  # the afternoon is free
		self.assertRaises(frappe.ValidationError, self._paper(a, day="2027-01-07").insert, ignore_permissions=True)  # one paper a class

	def test_the_rooms_seat_everyone_writing_at_that_time(self):
		a, _b, _student = self.shared
		frappe.db.set_value("Room", self.rooms[0], "seating_capacity", "0")
		self.assertRaises(frappe.ValidationError, self._paper(a).insert, ignore_permissions=True)

	def test_the_session_days_the_campus_and_the_hours(self):
		a, _b, _student = self.shared
		self.assertRaises(frappe.ValidationError, self._paper(a, day="2027-02-01").insert, ignore_permissions=True)  # after the session
		self.assertRaises(frappe.ValidationError, self._paper(a, day="2027-01-10").insert, ignore_permissions=True)  # a Sunday
		self.assertRaises(frappe.ValidationError, self._paper(a, start="12:00", end="09:00").insert, ignore_permissions=True)
		elsewhere = frappe.db.get_value("Room", {"campus": ("!=", CAMPUS)}, "name")
		self.assertRaises(frappe.ValidationError, self._paper(a, elsewhere).insert, ignore_permissions=True)

	def test_an_invigilator_is_in_one_room_at_a_time(self):
		a, b, _student = self.shared
		other = frappe.db.get_value(
			"Student Group", {"campus": CAMPUS, "academic_year": "2026", "group_based_on": "Course", "name": ("not in", [a, b])}, "name"
		)
		self._paper(a, invigilators=["Administrator"]).insert(ignore_permissions=True)
		clash = self._paper(other, self.rooms[1], invigilators=["Administrator"])
		self.assertIn("invigilates", " ".join(et.problems(clash)))
		self._paper(other, self.rooms[0], invigilators=["Administrator"]).insert(ignore_permissions=True)  # the same hall

	def test_published_the_student_sees_their_paper_and_the_invigilator_the_duty(self):
		a, _b, student = self.shared
		lecturer = "lecturer.comp.whk@educore.localhost"
		self._paper(a, invigilators=[lecturer]).insert(ignore_permissions=True)
		frappe.db.set_value("Examination Session", {"status": et.PUBLISHED}, "status", et.DRAFT)  # only this session published
		self.assertNotIn(a, [p["student_group"] for p in et.of_student(student)])
		frappe.set_user(lecturer)
		self.assertRaises(frappe.PermissionError, api.publish, SESSION)
		frappe.set_user("Administrator")
		api.publish(SESSION)
		self.assertIn(a, [p["student_group"] for p in et.of_student(student)])
		self.assertEqual([p["student_group"] for p in et.duties_of(lecturer)], [a])

	def test_only_the_examinations_officer_schedules(self):
		a, _b, _student = self.shared
		frappe.set_user("lecturer.comp.whk@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.save_paper, {"session": SESSION, "student_group": a})
