"""Prerequisites and repeats from published results (educore.registration.rules, educore.api.v1.curriculum)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import curriculum
from educore.registration import rules

PROGRAMME = "Bachelor of Computer Science"
FAILED_CLASS = "CMP1521 WHK 2026"  # Computer Systems at Windhoek, 2026


class TestPrerequisites(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"user": "student1.whk@educore.localhost"}, "name")
		if not self.student or not frappe.db.exists("Mark Sheet", FAILED_CLASS):
			self.skipTest("run the demo setup first")
		frappe.set_user("Administrator")
		# the student failed Computer Systems in 2026 (published)
		sheet = frappe.get_doc("Mark Sheet", FAILED_CLASS)
		for e in sheet.entries:
			if e.student == self.student:
				e.ca_mark, e.exam_mark, e.final_mark, e.result = 40, 30, 35, "Fail"
		sheet.status = "Published"
		sheet.save(ignore_permissions=True)
		# and Databases needs Computer Systems first
		self.databases = frappe.get_doc("Course", "Databases")
		self.saved = [r.prerequisite for r in self.databases.educore_prerequisites]
		self.databases.set("educore_prerequisites", [{"prerequisite": "Computer Systems"}])
		self.databases.save(ignore_permissions=True)

	def test_passed_repeat_blocked_and_open(self):
		states = rules.course_states(self.student, PROGRAMME, 2)
		self.assertEqual(states["Programming Fundamentals"]["state"], rules.PASSED)
		self.assertEqual(states["Computer Systems"]["state"], rules.REPEAT)
		self.assertEqual(states["Databases"], {"state": rules.BLOCKED, "missing": ["Computer Systems"]})
		self.assertEqual(states["Data Structures and Algorithms"]["state"], rules.OPEN)

	def test_registration_takes_the_repeat_and_refuses_what_is_not_open(self):
		self.assertRaises(frappe.ValidationError, rules.check_courses, PROGRAMME, 2, ["Data Structures and Algorithms", "Databases", "Computer Systems"], self.student)
		self.assertRaises(frappe.ValidationError, rules.check_courses, PROGRAMME, 2, ["Data Structures and Algorithms", "Programming Fundamentals", "Computer Systems"], self.student)
		# the failed required course must be taken again
		self.assertRaises(frappe.ValidationError, rules.check_courses, PROGRAMME, 2, ["Data Structures and Algorithms"], self.student)
		rules.check_courses(PROGRAMME, 2, ["Data Structures and Algorithms", "Computer Systems"], self.student)

	def test_the_faculty_sets_prerequisites_without_circles(self):
		frappe.set_user("faculty-officer.fst.osh@educore.localhost")
		data = curriculum.programme(PROGRAMME)
		rows = [{**c, "prerequisites": ["Databases"] if c["course"] == "Computer Systems" else c["prerequisites"]} for c in data["courses"]]
		self.assertRaises(frappe.ValidationError, curriculum.save, PROGRAMME, rows)  # Databases already needs Computer Systems
		rows = [{**c, "prerequisites": ["Computer Systems"] if c["course"] == "Computer Systems" else c["prerequisites"]} for c in data["courses"]]
		self.assertRaises(frappe.ValidationError, curriculum.save, PROGRAMME, rows)  # its own prerequisite
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, curriculum.save, PROGRAMME, data["courses"])
