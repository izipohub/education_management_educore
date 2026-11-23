"""The curriculum: courses by year of study and semester (educore.api.v1.curriculum)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import curriculum
from educore.registration import rules

PROGRAMME = "Bachelor of Computer Science"


class TestCurriculum(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Program", PROGRAMME) or not frappe.db.exists("User", "registrar@educore.localhost"):
			self.skipTest("run the demo setup first")
		saved = [
			{"course": c["course"], "year": c["year"], "semester": c["semester"], "required": c["required"]}
			for c in rules.curriculum(PROGRAMME)
		]

		def restore():
			frappe.set_user("registrar@educore.localhost")
			curriculum.save(PROGRAMME, saved)
			frappe.set_user("Administrator")

		self.addCleanup(restore)
		frappe.set_user("registrar@educore.localhost")

	def test_the_registrar_moves_a_course_to_the_second_semester(self):
		data = curriculum.programme(PROGRAMME)
		rows = [{**c, "semester": "Semester 2" if c["course"] == "Calculus I" else c["semester"]} for c in data["courses"]]
		saved = curriculum.save(PROGRAMME, rows)
		self.assertEqual(next(c["semester"] for c in saved["courses"] if c["course"] == "Calculus I"), "Semester 2")
		# registration and the proof of registration read the same curriculum
		self.assertEqual(rules.semesters(PROGRAMME)["Calculus I"], "Semester 2")

	def test_a_year_or_semester_that_does_not_exist_is_refused(self):
		rows = [{"course": c["course"], "year": c["year"], "semester": c["semester"], "required": True} for c in rules.curriculum(PROGRAMME)]
		rows[0]["semester"] = "Semester 3"
		self.assertRaises(frappe.ValidationError, curriculum.save, PROGRAMME, rows)
		rows[0]["semester"], rows[0]["year"] = "Year", 9
		self.assertRaises(frappe.ValidationError, curriculum.save, PROGRAMME, rows)
		rows[0]["year"] = 1
		self.assertRaises(frappe.ValidationError, curriculum.save, PROGRAMME, rows + [rows[0]])

	def test_students_do_not_change_the_curriculum(self):
		frappe.set_user("student1.whk@educore.localhost")
		self.assertRaises(frappe.PermissionError, curriculum.programmes)
		self.assertRaises(frappe.PermissionError, curriculum.save, PROGRAMME, [])
