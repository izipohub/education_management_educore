"""Lecturer workload (educore.academics.workload, educore.api.v1.academic_staff.workload): modules, students, contact
hours a week from the timetable and invigilation, against the university's rule"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.academics import workload
from educore.academics.lecturers import instructors_of
from educore.api.v1 import academic_staff as api
from educore.api.v1 import teaching_allocation

REGISTRAR = "registrar@educore.localhost"
HOD_ACCF = "head-of-department.accf@educore.localhost"
HOD_COMP = "hod-lecturer.comp@educore.localhost"
COMP_WHK = "lecturer.comp.whk@educore.localhost"
YEAR, SEMESTER = "2026", "Semester 2"


def _instructor(user: str) -> str:
	return instructors_of(user)[0]


def _slot_hours(groups: list[str]) -> float:
	rows = frappe.get_all("Timetable Slot", filters={"student_group": ("in", groups or [""]), "semester": SEMESTER}, fields=["start_time", "end_time"])
	return sum((r.end_time - r.start_time).total_seconds() / 3600 for r in rows)


class TestWorkload(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", COMP_WHK) or not frappe.db.count("Timetable Slot"):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("workload_test")
		frappe.set_user("Administrator")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="workload_test")
		frappe.clear_document_cache(workload.SETTINGS, workload.SETTINGS)

	def _load(self, user: str) -> dict:
		name = _instructor(user)
		return workload.for_lecturers(YEAR, SEMESTER, [name])[name]

	def test_contact_hours_come_from_the_timetable_and_a_shared_class_counts_for_both(self):
		mine, colleague = self._load(HOD_COMP), self._load(COMP_WHK)
		groups = [m["group"] for m in mine["modules"]]
		self.assertTrue(groups)
		self.assertAlmostEqual(mine["hours"], _slot_hours(groups))
		shared = set(groups) & {m["group"] for m in colleague["modules"]}
		self.assertTrue(shared, "the demo's COMP classes are co-taught")
		module = next(m for m in mine["modules"] if m["group"] in shared)
		self.assertIn(frappe.db.get_value("Instructor", _instructor(COMP_WHK), "instructor_name"), module["with"])
		self.assertAlmostEqual(next(m for m in colleague["modules"] if m["group"] == module["group"])["hours"], module["hours"])

	def test_invigilation_is_the_hours_of_the_papers_invigilated_that_semester(self):
		expected = frappe.db.sql(
			"""select coalesce(sum(time_to_sec(timediff(p.end_time, p.start_time))), 0) / 3600
			from `tabExamination Invigilator` i join `tabExamination Paper` p on p.name = i.parent
			join `tabExamination Session` s on s.name = p.session
			where i.user = %s and s.academic_year = %s and s.semester = %s""",
			(COMP_WHK, YEAR, SEMESTER),
		)[0][0]
		self.assertAlmostEqual(self._load(COMP_WHK)["invigilation"], float(expected))
		self.assertEqual(workload.for_lecturers(YEAR, "Semester 1", [_instructor(COMP_WHK)])[_instructor(COMP_WHK)]["invigilation"], 0)

	def test_the_status_follows_the_universitys_rule(self):
		hours = self._load(COMP_WHK)["hours"]
		self.assertGreater(hours, 0)
		frappe.db.set_single_value(workload.SETTINGS, {"min_hours": 0, "max_hours": hours - 1})
		self.assertEqual(self._load(COMP_WHK)["status"], workload.OVER)
		frappe.db.set_single_value(workload.SETTINGS, {"min_hours": hours + 1, "max_hours": hours + 5})
		self.assertEqual(self._load(COMP_WHK)["status"], workload.LIGHT)
		frappe.db.set_single_value(workload.SETTINGS, {"min_hours": hours, "max_hours": hours})
		self.assertEqual(self._load(COMP_WHK)["status"], workload.WITHIN)

	def test_a_lecturer_with_no_modules_in_the_semester_is_not_allocated(self):
		idle = next(
			i for i in frappe.get_all("Instructor", filters={"status": "Active"}, pluck="name")
			if not workload.for_lecturers(YEAR, SEMESTER, [i])[i]["modules"]
		)
		self.assertEqual(workload.for_lecturers(YEAR, SEMESTER, [idle])[idle]["status"], workload.NONE)

	def test_the_head_of_department_sees_their_own_lecturers_only(self):
		frappe.set_user(HOD_ACCF)
		page = api.workload(YEAR, SEMESTER)
		names = {r["instructor_name"] for r in page["rows"]}
		self.assertIn("Lecturer ACCF Keetmanshoop", names)
		self.assertNotIn("Lecturer COMP Windhoek", names)
		self.assertFalse(page["can_edit_rule"])

	def test_only_the_registrar_sets_the_rule_and_it_must_make_sense(self):
		frappe.set_user(HOD_ACCF)
		with self.assertRaises(frappe.PermissionError):
			api.save_workload_rule(4, 12)
		frappe.set_user(REGISTRAR)
		with self.assertRaises(frappe.ValidationError):
			api.save_workload_rule(12, 4)
		self.assertEqual(api.save_workload_rule(4, 12), {"min_hours": 4, "max_hours": 12})
		self.assertTrue(api.workload(YEAR, SEMESTER)["can_edit_rule"])

	def test_the_lecturers_page_and_the_allocation_show_the_hours(self):
		name = _instructor(COMP_WHK)
		hours = self._load(COMP_WHK)["hours"]
		frappe.set_user(HOD_COMP)
		group = self._load(COMP_WHK)["modules"][0]["group"]
		detail = teaching_allocation.class_detail(group)
		self.assertEqual(next(i for i in detail["instructors"] if i["name"] == name)["hours"], hours)
		frappe.set_user("Administrator")
		self.assertIsNotNone(api.lecturer(name)["workload"])
