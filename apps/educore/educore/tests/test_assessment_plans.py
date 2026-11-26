"""Assessment types kept by the Dean (educore.academics.assessment_types), the assessment plan approved by the
department before scores go in (educore.academics.gradebook), and online assessments' grades from Moodle
(educore.learning.moodle_grades, against an in-memory stand-in for Moodle)"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from educore.academics import assessment_types
from educore.api.v1 import assessment_types as types_api
from educore.api.v1 import examinations as api

GROUP = "CMP2521 WHK 2026"
LECTURER = "lecturer.comp.whk@educore.localhost"
CO_LECTURER_HOD = "hod-lecturer.comp@educore.localhost"
DEAN_FST = "dean.fst@educore.localhost"
HOD_ACCF = "head-of-department.accf@educore.localhost"
FST = "Faculty of Science and Technology - EDU"
PLAN = [
	{"title": "Test 1", "kind": "Test", "out_of": 50, "weight": 40},
	{"title": "Quiz", "kind": "Online quiz", "out_of": 20, "weight": 30},
	{"title": "Project", "kind": "Project", "out_of": 100, "weight": 30},
]


class FakeMoodle:
	"""A Moodle course with a quiz (cmid 55) and a reading (not graded); one student graded 15 out of 20"""

	def __init__(self, student: str):
		self.student = student

	def call(self, function, **p):
		if function == "core_course_get_contents":
			return [
				{
					"name": "Week 1",
					"modules": [
						{"id": 55, "name": "Quiz 1: networks", "modname": "quiz", "url": "https://moodle.example/mod/quiz/view.php?id=55"},
						{"id": 56, "name": "Reading", "modname": "resource", "url": "https://moodle.example/mod/resource/view.php?id=56"},
					],
				}
			]
		if function == "gradereport_user_get_grade_items":
			return {
				"usergrades": [
					{"userid": 9, "useridnumber": self.student, "gradeitems": [{"cmid": 55, "graderaw": 15, "grademax": 20}]},
					{"userid": 10, "useridnumber": "NOT-IN-CLASS", "gradeitems": [{"cmid": 55, "graderaw": 20, "grademax": 20}]},
				]
			}
		raise AssertionError(f"unexpected {function}")


class TestAssessmentPlans(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Group", GROUP) or not frappe.db.exists("Assessment Type", {"faculty": FST}):
			self.skipTest("run the demo setup first")
		if frappe.db.get_value("Mark Sheet", {"student_group": GROUP}, "status") not in (None, "Draft"):
			self.skipTest("the marks are no longer with the lecturer")
		frappe.db.savepoint("plans_test")
		frappe.set_user(LECTURER)
		self.page = api.my_sheet(GROUP)
		self.student = self.page["entries"][0]["student"]

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="plans_test")

	def _keys(self, page) -> dict:
		return {a["title"]: a["assessment_key"] for a in page["assessments"]}

	def test_scores_go_in_once_the_department_approves_the_plan(self):
		page = api.save_gradebook(GROUP, PLAN, {})
		keys = self._keys(page)
		with self.assertRaises(frappe.ValidationError) as caught:
			api.save_gradebook(GROUP, page["assessments"], {self.student: {keys["Test 1"]: 40}})
		self.assertIn("approves", str(caught.exception))
		page = api.propose_plan(GROUP)
		self.assertEqual(page["plan"]["status"], "Proposed")
		# with the department: the lecturer cannot change it
		changed = [dict(a, weight=w) for a, w in zip(page["assessments"], (50, 25, 25))]
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, changed, {})

		# another faculty's head of department, and a head of department who teaches the module, do not approve it
		frappe.set_user(HOD_ACCF)
		self.assertRaises(frappe.PermissionError, api.approve_plan, GROUP)
		frappe.set_user(CO_LECTURER_HOD)
		self.assertRaises(frappe.ValidationError, api.approve_plan, GROUP)
		frappe.set_user(DEAN_FST)
		self.assertTrue(api.sheet(GROUP)["can_approve_plan"])
		self.assertEqual(api.approve_plan(GROUP)["plan"]["status"], "Approved")

		frappe.set_user(LECTURER)
		page = api.save_gradebook(GROUP, page["assessments"], {self.student: {keys["Test 1"]: 40}})
		self.assertEqual(page["scores"][self.student][keys["Test 1"]], 40)
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, changed, {})

		# a change: returned with the reason, changed, the scores kept
		frappe.set_user(DEAN_FST)
		self.assertRaises(frappe.ValidationError, api.return_plan, GROUP, " ")
		api.return_plan(GROUP, "The project is worth more than the test")
		frappe.set_user(LECTURER)
		page = api.my_sheet(GROUP)
		self.assertEqual(page["plan"]["note"], "The project is worth more than the test")
		page = api.save_gradebook(GROUP, changed, {})
		self.assertEqual(page["scores"][self.student][keys["Test 1"]], 40)
		self.assertRaises(frappe.ValidationError, api.submit, GROUP)  # the plan is not approved again yet

	def test_the_plan_uses_the_facultys_types_within_their_shares(self):
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, [dict(PLAN[0], kind="Essay", weight=100)], {})
		frappe.set_user("Administrator")
		quiz = frappe.get_doc("Assessment Type", {"faculty": FST, "type_name": "Online quiz"})
		quiz.max_share = 20
		quiz.save()
		frappe.set_user(LECTURER)
		with self.assertRaises(frappe.ValidationError) as caught:
			api.save_gradebook(GROUP, PLAN, {})
		self.assertIn("20% at most", str(caught.exception))
		frappe.set_user("Administrator")
		frappe.db.set_value("Assessment Type", {"faculty": FST, "type_name": "Project"}, "disabled", 1)
		frappe.set_user(LECTURER)
		plan = [PLAN[0], dict(PLAN[1], weight=20), dict(PLAN[2], weight=40)]
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, plan, {})  # Project is not in use
		# only an online assessment is linked to Moodle
		linked = [dict(PLAN[0], weight=60, moodle_cmid=55), dict(PLAN[1], weight=20), dict(PLAN[0], title="Test 2", weight=20)]
		self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, linked, {})

	def test_an_online_assessment_takes_its_grades_from_its_moodle_activity(self):
		frappe.set_user("Administrator")
		frappe.db.set_single_value("Learning Platform Settings", "moodle_enabled", 1)
		frappe.db.set_value("Student Group", GROUP, "educore_moodle_course_id", 7)
		frappe.set_user(LECTURER)
		with patch("educore.learning.moodle_grades._client", return_value=FakeMoodle(self.student)):
			self.assertEqual([a["cmid"] for a in api.moodle_activities(GROUP)], [55])  # graded activities only
			self.assertRaises(frappe.ValidationError, api.save_gradebook, GROUP, [PLAN[0], dict(PLAN[1], moodle_cmid=99), PLAN[2]], {})
			page = api.save_gradebook(GROUP, [PLAN[0], dict(PLAN[1], moodle_cmid=55), PLAN[2]], {})
			quiz = next(a for a in page["assessments"] if a["title"] == "Quiz")
			self.assertEqual(quiz["moodle_activity"], "Quiz 1: networks")
			self.assertRaises(frappe.ValidationError, api.moodle_scores, GROUP, quiz["assessment_key"])  # not approved yet
			api.propose_plan(GROUP)
			frappe.db.set_value("Mark Sheet", {"student_group": GROUP}, "plan_status", "Approved")
			grades = api.moodle_scores(GROUP, quiz["assessment_key"])
		# 15 of 20 in Moodle, on an assessment out of 20; the student outside the class left out
		self.assertEqual(grades["scores"], {self.student: 15.0})
		self.assertEqual(grades["not_graded"], 0)
		# nothing is saved until the lecturer saves it
		self.assertNotIn(self.student, api.my_sheet(GROUP)["scores"])


class TestAssessmentTypes(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Assessment Type", {"faculty": FST}):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("types_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="types_test")

	def test_every_faculty_has_its_list_and_a_department_belongs_to_its_faculty(self):
		self.assertEqual(assessment_types.faculty_of("Department of Computing - EDU"), FST)
		self.assertEqual(assessment_types.faculty_of("School of Nursing - EDU"), "Faculty of Health Sciences - EDU")
		self.assertIsNone(assessment_types.faculty_of("Finance - EDU"))
		for faculty in assessment_types.faculties():
			self.assertTrue(assessment_types.of_faculty(faculty), faculty)

	def test_the_dean_keeps_the_facultys_list(self):
		frappe.set_user(DEAN_FST)
		page = types_api.types()
		self.assertEqual([f["faculty"] for f in page["faculties"]], [FST])
		rows = page["faculties"][0]["types"]
		rows.append({"type_name": "Lab report", "online": 0, "max_share": 40, "disabled": 0})
		page = types_api.save(FST, rows)
		self.assertIn("Lab report", [t["type_name"] for t in page["faculties"][0]["types"]])
		# two of a name, another faculty's list, and none in use are refused
		self.assertRaises(frappe.ValidationError, types_api.save, FST, [*rows, {"type_name": "lab report"}])
		self.assertRaises(frappe.PermissionError, types_api.save, "Faculty of Commerce and Management - EDU", rows)
		self.assertRaises(frappe.ValidationError, types_api.save, FST, [dict(r, disabled=1) for r in page["faculties"][0]["types"]])

	def test_a_type_used_in_plans_keeps_its_name(self):
		frappe.set_user(DEAN_FST)
		rows = types_api.types()["faculties"][0]["types"]
		test = next(r for r in rows if r["type_name"] == "Test")
		if not test["used"]:
			self.skipTest("no plan uses Test")
		test["type_name"] = "Class test"
		self.assertRaises(frappe.ValidationError, types_api.save, FST, rows)

	def test_the_head_of_department_reads_the_list_only(self):
		frappe.set_user(HOD_ACCF)
		page = types_api.types()
		self.assertFalse(page["can_edit"])
		self.assertRaises(frappe.PermissionError, types_api.save, page["faculties"][0]["faculty"], page["faculties"][0]["types"])
