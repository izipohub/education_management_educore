"""Completing a programme (educore.academics.graduation, educore.api.v1.graduation)"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from educore.academics import graduation
from educore.api.v1 import graduation as api

#: a diploma student who has passed every course on the (demo) curriculum: 48 credits
FINISHER = "student2.kmp@educore.localhost"
PROGRAMME = "Diploma in Accounting and Finance"
REGISTRAR = "registrar@educore.localhost"
EXAMS = "examinations-officer@educore.localhost"
SENATE = "Senate, 05-12-2026"

CURRICULUM = [
	{"course": "A", "course_name": "A", "credits": 16, "required": True},
	{"course": "B", "course_name": "B", "credits": 16, "required": True},
	{"course": "C", "course_name": "C", "credits": 16, "required": False},
]


class TestGraduationRules(IntegrationTestCase):
	def test_every_required_course_and_the_credits(self):
		self.assertTrue(graduation.assess(CURRICULUM, {"A": "Pass", "B": "Pass"}, 32)["meets"])

	def test_a_required_course_not_passed(self):
		state = graduation.assess(CURRICULUM, {"A": "Pass", "B": "Fail", "C": "Pass"}, 32)
		self.assertFalse(state["meets"])
		self.assertEqual(state["outstanding"], ["B"])

	def test_too_few_credits(self):
		state = graduation.assess(CURRICULUM, {"A": "Pass", "B": "Pass"}, 48)
		self.assertFalse(state["meets"])
		self.assertEqual(state["credits_passed"], 32)

	def test_a_course_off_the_curriculum_does_not_count(self):
		self.assertEqual(graduation.assess(CURRICULUM, {"A": "Pass", "Z": "Pass"}, 0)["credits_passed"], 16)


class TestGraduation(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"user": FINISHER}, "name")
		if not self.student or not frappe.db.exists("User", EXAMS):
			self.skipTest("run the demo setup first")
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(self._restore, frappe.db.get_value("Program", PROGRAMME, "educore_credits"))
		frappe.db.set_value("Program", PROGRAMME, "educore_credits", 48)
		frappe.db.set_value(
			"Student", self.student,
			{"educore_completed_on": None, "educore_completed_programme": None, "educore_completion_reference": None, "educore_academic_standing": "Good standing"},
		)
		frappe.clear_document_cache("Program", PROGRAMME)

	def _restore(self, credits):
		frappe.set_user("Administrator")
		frappe.db.set_value("Program", PROGRAMME, "educore_credits", credits)
		frappe.db.set_value("Student", self.student, {"educore_completed_on": None, "educore_completed_programme": None, "educore_completion_reference": None})
		frappe.clear_document_cache("Program", PROGRAMME)

	def _row(self):
		return next(r for r in api.candidates()["rows"] if r["name"] == self.student)

	def test_the_registrar_confirms_an_eligible_student(self):
		frappe.set_user(REGISTRAR)
		self.assertEqual(self._row()["status"], graduation.ELIGIBLE)
		api.confirm([self.student], SENATE)
		row = self._row()
		self.assertEqual(row["status"], graduation.COMPLETED)
		self.assertEqual(row["reference"], SENATE)
		self.assertEqual(frappe.db.get_value("Student", self.student, "educore_completed_programme"), PROGRAMME)
		self.assertRaises(frappe.ValidationError, api.confirm, [self.student], SENATE)

	def test_not_yet_eligible_is_refused(self):
		frappe.db.set_value("Program", PROGRAMME, "educore_credits", 360)
		frappe.clear_document_cache("Program", PROGRAMME)
		frappe.set_user(REGISTRAR)
		self.assertEqual(self._row()["status"], graduation.NOT_YET)
		self.assertRaises(frappe.ValidationError, api.confirm, [self.student], SENATE)

	def test_a_student_on_hold_is_held_back(self):
		frappe.db.set_value("Student", self.student, "educore_academic_standing", "On hold")
		frappe.set_user(REGISTRAR)
		self.assertRaises(frappe.ValidationError, api.confirm, [self.student], SENATE)

	def test_the_senate_reference_and_a_past_date_are_needed(self):
		frappe.set_user(REGISTRAR)
		self.assertRaises(frappe.ValidationError, api.confirm, [self.student], "  ")
		self.assertRaises(frappe.ValidationError, api.confirm, [self.student], SENATE, add_days(nowdate(), 3))

	def test_the_examinations_office_reads_but_does_not_confirm(self):
		frappe.set_user(EXAMS)
		self.assertFalse(api.candidates()["can_confirm"])
		self.assertRaises(frappe.PermissionError, api.confirm, [self.student], SENATE)

	def test_students_have_no_graduation_list(self):
		frappe.set_user(FINISHER)
		self.assertRaises(frappe.PermissionError, api.candidates)
