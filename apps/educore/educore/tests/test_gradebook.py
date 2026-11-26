"""The gradebook (educore.academics.gradebook): the lecturer's assessments, the scores, and the CA worked out from them"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import examinations as api

GROUP = "CMP2521 WHK 2026"  # marks still with the lecturer
LECTURER = "lecturer.comp.whk@educore.localhost"
PLAN = [
	{"title": "Test 1", "kind": "Test", "out_of": 50, "weight": 25},
	{"title": "Test 2", "kind": "Test", "out_of": 50, "weight": 25},
	{"title": "Assignment", "kind": "Assignment", "out_of": 100, "weight": 50},
]


class TestGradebook(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Group", GROUP) or not frappe.db.exists("User", LECTURER):
			self.skipTest("run the demo setup first")
		if frappe.db.get_value("Mark Sheet", {"student_group": GROUP}, "status") not in (None, "Draft"):
			self.skipTest("the marks are no longer with the lecturer")
		frappe.db.savepoint("gradebook_test")
		frappe.set_user(LECTURER)
		self.sheet = api.my_sheet(GROUP)
		self.student = self.sheet["entries"][0]["student"]

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="gradebook_test")

	def _keys(self, page) -> dict:
		return {a["title"]: a["assessment_key"] for a in page["assessments"]}

	def test_the_ca_is_worked_out_from_the_lecturers_assessments(self):
		page = api.save_gradebook(GROUP, PLAN, {})
		self.assertTrue(page["ca_from_gradebook"])
		keys = self._keys(page)
		# partly scored: no CA yet
		page = api.save_gradebook(GROUP, page["assessments"], {self.student: {keys["Test 1"]: 40}})
		self.assertIsNone(page["entries"][0]["ca_mark"])
		# 40/50 of 25 + 30/50 of 25 + 70/100 of 50 = 20 + 15 + 35
		page = api.save_gradebook(GROUP, page["assessments"], {self.student: {keys["Test 2"]: 30, keys["Assignment"]: 70}})
		self.assertEqual(page["entries"][0]["ca_mark"], 70)
		# a CA typed over is ignored: it comes from the scores
		page = api.save_marks(GROUP, [{"student": self.student, "ca_mark": 99, "exam_mark": 60}])
		self.assertEqual(page["entries"][0]["ca_mark"], 70)
		self.assertEqual(page["entries"][0]["final_mark"], 65)

	def test_the_plan_adds_up_and_scores_stay_within_what_it_is_marked_out_of(self):
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, PLAN[:2], {})  # 50%
		twice = [dict(PLAN[0]), dict(PLAN[0], weight=75)]
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, twice, {})
		page = api.save_gradebook(GROUP, PLAN, {})
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, page["assessments"], {self.student: {self._keys(page)["Test 1"]: 51}})

	def test_an_assessment_removed_takes_its_scores_with_it(self):
		page = api.save_gradebook(GROUP, PLAN, {})
		keys = self._keys(page)
		page = api.save_gradebook(GROUP, page["assessments"], {self.student: {keys["Test 1"]: 40, keys["Test 2"]: 30, keys["Assignment"]: 70}})
		kept = [dict(a, weight=50) for a in page["assessments"] if a["title"] != "Assignment"]
		page = api.save_gradebook(GROUP, kept, {})
		self.assertNotIn(keys["Assignment"], page["scores"].get(self.student, {}))
		self.assertEqual(page["entries"][0]["ca_mark"], 70)  # 40/50 of 50 + 30/50 of 50

	def test_only_the_lecturer_while_the_marks_are_with_them(self):
		frappe.set_user("lecturer.accf.kmp@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.save_gradebook, GROUP, PLAN, {})
		frappe.set_user("Administrator")
		frappe.db.set_value("Mark Sheet", {"student_group": GROUP}, "status", "Submitted")
		frappe.set_user(LECTURER)
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, PLAN, {})
