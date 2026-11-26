"""Class attendance (educore.academics.attendance, educore.api.v1.attendance)"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from educore.academics import attendance
from educore.api.v1 import attendance as api
from educore.api.v1 import student as student_api
from educore.api.v1 import teaching_allocation

GROUP = "ACC1511 KMP 2026"
LECTURER = "lecturer.accf.kmp@educore.localhost"


def _lesson_day() -> tuple[str, str | None]:
	"""A past day of semester 1 2026 with a lesson of the module and no register yet (the day and the lesson)"""
	from frappe.utils import getdate

	day = getdate("2026-03-02")
	for _ in range(90):
		that_day = attendance.lessons(GROUP, day)
		if that_day and not that_day[0]["taken"] and str(day) not in ("2026-03-21", "2026-04-03", "2026-04-06", "2026-05-01", "2026-05-04", "2026-05-14", "2026-05-25", "2026-05-28"):
			return str(day), that_day[0]["key"]
		day = add_days(day, 1)
	return "2026-03-31", None


class TestAttendance(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Group", GROUP) or not frappe.db.exists("User", LECTURER):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("attendance_test")
		global DAY, LESSON
		DAY, LESSON = _lesson_day()
		frappe.set_user(LECTURER)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="attendance_test")
		frappe.clear_cache(doctype="Company")

	def _entries(self, status="Present", **overrides):
		page = api.register(GROUP, DAY, LESSON)
		return [{"student": e["student"], "status": overrides.get(e["student_name"], status)} for e in page["entries"]]

	def test_the_lecturer_takes_the_register_and_can_correct_it(self):
		page = api.take(GROUP, DAY, self._entries(**{"Anna Beukes": "Absent"}), LESSON)
		self.assertTrue(page["taken"])
		status = {e["student_name"]: e["status"] for e in page["entries"]}
		self.assertEqual(status["Anna Beukes"], "Absent")
		page = api.take(GROUP, DAY, self._entries(), LESSON)  # Anna was there after all
		self.assertEqual({e["student_name"]: e["status"] for e in page["entries"]}["Anna Beukes"], "Present")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.count("Student Attendance", {"student_group": GROUP, "date": DAY, "docstatus": 1}), len(page["entries"]))

	def test_a_register_per_lesson(self):
		"""Two lessons on a day: two registers, each its own Course Schedule; no register on a day without a lesson"""
		if not LESSON:
			self.skipTest("the module has no timetable")
		frappe.set_user("Administrator")
		first = frappe.get_doc("Timetable Slot", LESSON)
		later = frappe.get_doc(
			{"doctype": "Timetable Slot", "student_group": GROUP, "semester": first.semester, "day": first.day, "start_time": "18:00", "end_time": "19:00", "room": first.room, "kind": "Tutorial"}
		)
		later.insert()
		frappe.set_user(LECTURER)
		page = api.register(GROUP, DAY)
		self.assertEqual(len(page["lessons"]), 2)
		api.take(GROUP, DAY, self._entries(**{"Anna Beukes": "Absent"}), LESSON)
		page = api.take(GROUP, DAY, [{"student": e["student"], "status": "Present"} for e in page["entries"]], later.name)
		self.assertEqual({e["student_name"]: e["status"] for e in page["entries"]}["Anna Beukes"], "Present")
		self.assertEqual({e["student_name"]: e["status"] for e in api.register(GROUP, DAY, LESSON)["entries"]}["Anna Beukes"], "Absent")
		frappe.set_user("Administrator")
		self.assertEqual(len({r for r in frappe.get_all("Student Attendance", filters={"student_group": GROUP, "date": DAY, "docstatus": 1}, pluck="course_schedule")}), 2)
		frappe.set_user(LECTURER)
		other_day = next(add_days(DAY, n) for n in range(1, 7) if not attendance.lessons(GROUP, add_days(DAY, n)))
		self.assertRaises(frappe.ValidationError, api.take, GROUP, other_day, self._entries())

	def test_excused_absences_do_not_count_and_low_attendance_is_flagged(self):
		before = {s["student_name"]: s for s in attendance.summary(GROUP)["students"]}
		api.take(GROUP, DAY, self._entries(**{"Petrus Kooper": "Leave"}), LESSON)
		after = {s["student_name"]: s for s in attendance.summary(GROUP)["students"]}
		self.assertEqual(after["Petrus Kooper"]["rate"], before["Petrus Kooper"]["rate"])
		self.assertEqual(after["Petrus Kooper"]["excused"], before["Petrus Kooper"]["excused"] + 1)
		if attendance.minimum():
			self.assertTrue(after["Petrus Kooper"]["below"])  # 4 of 8 in the demo
			self.assertFalse(after["Anna Beukes"]["below"])

	def test_no_register_ahead_of_the_day_on_a_holiday_or_for_another_lecturers_class(self):
		self.assertRaises(frappe.ValidationError, api.take, GROUP, add_days(nowdate(), 1), self._entries())
		frappe.set_user("Administrator")
		if frappe.db.get_value("Company", frappe.db.get_value("Campus", {"is_main_campus": 1}, "company"), "default_holiday_list"):
			frappe.set_user(LECTURER)
			self.assertRaises(frappe.ValidationError, api.take, GROUP, "2026-03-21", self._entries())  # Independence Day
		frappe.set_user("lecturer.comp.whk@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.register, GROUP)

	def test_attendance_is_taken_without_a_holiday_list(self):
		frappe.set_user("Administrator")
		company = frappe.db.get_value("Campus", {"is_main_campus": 1}, "company")
		frappe.db.set_value("Company", company, "default_holiday_list", None)
		frappe.clear_cache(doctype="Company")
		frappe.set_user(LECTURER)
		self.assertTrue(api.take(GROUP, DAY, self._entries(), LESSON)["taken"])

	def test_the_department_and_the_student_see_it(self):
		api.take(GROUP, DAY, self._entries(), LESSON)
		frappe.set_user("head-of-department.accf@educore.localhost")
		detail = teaching_allocation.class_detail(GROUP)
		self.assertTrue(detail["attendance"]["sessions"])
		frappe.set_user("student2.kmp@educore.localhost")  # Petrus Kooper
		mine = {a["group"]: a for a in student_api.overview()["attendance"]}
		self.assertIn(GROUP, mine)
		self.assertIsNotNone(mine[GROUP]["rate"])
