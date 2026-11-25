"""Marks to published results: lecturer, department, examination board, students (educore.api.v1.examinations)"""

import frappe
from frappe.tests import IntegrationTestCase

from unittest.mock import patch

from educore.academics import notify, results
from educore.api.v1 import examinations as api

CLASS = "CMP1511 WHK 2026"
LECTURER = "lecturer.comp.whk@educore.localhost"
HOD = "hod-lecturer.comp@educore.localhost"
EXAMS = "examinations-officer.whk@educore.localhost"


def _as(user):
	frappe.set_user(user)


class TestExaminations(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Group", CLASS) or not frappe.db.exists("User", EXAMS):
			self.skipTest("run the demo setup first")
		frappe.set_user("Administrator")
		results.ensure_defaults()
		if frappe.db.exists("Mark Sheet", CLASS):
			frappe.delete_doc("Mark Sheet", CLASS, force=True, ignore_permissions=True)
		self.addCleanup(frappe.set_user, "Administrator")
		# emails to students are captured, not queued
		self.sent = []
		patcher = patch.object(notify, "_deliver", lambda recipient, subject, body, doc: self.sent.append((recipient, subject)))
		patcher.start()
		self.addCleanup(patcher.stop)
		frappe.db.set_single_value("Registration Settings", "notify_students", 1)
		frappe.clear_document_cache("Registration Settings", "Registration Settings")

	def _marks(self, ca, exam):
		sheet = api.my_sheet(CLASS)
		return [{"student": e["student"], "ca_mark": ca, "exam_mark": exam} for e in sheet["entries"]]

	def test_the_final_mark_grade_and_result_follow_the_rules(self):
		rules = frappe._dict(ca_weight=50, exam_admission_ca=40, pass_mark=50, supplementary_from=45)
		bands = [("A+", 80), ("A", 70), ("B", 60), ("C", 50), ("D", 40), ("E", 0)]
		cases = [((70, 60), (65, "B", "Pass")), ((50, 44), (47, "D", "Supplementary")), ((45, 20), (32, "E", "Fail")), ((30, 90), (None, None, "Not admitted"))]
		for (ca, exam), (final, grade, result) in cases:
			e = frappe._dict(ca_mark=ca, exam_mark=exam, absent=0)
			results.work_out(e, rules, bands)
			self.assertEqual((e.final_mark, e.grade, e.result), (final, grade, result))
		absent = frappe._dict(ca_mark=60, exam_mark=None, absent=1)
		results.work_out(absent, rules, bands)
		self.assertEqual(absent.result, "Absent")

	def test_from_the_lecturer_to_the_students(self):
		_as(LECTURER)
		self.assertRaises(frappe.ValidationError, api.submit, CLASS)  # nothing entered yet
		api.save_marks(CLASS, self._marks(72, 64))
		self.assertEqual(api.submit(CLASS)["status"], "Submitted")
		self.assertRaises(frappe.ValidationError, api.save_marks, CLASS, self._marks(10, 10))  # locked once submitted

		_as(HOD)
		self.assertRaises(frappe.ValidationError, api.moderate, CLASS, [{"student": "x", "ca_mark": 1}], "")  # a change needs a reason
		self.assertEqual(api.moderate(CLASS)["status"], "Moderated")

		_as(EXAMS)
		self.assertRaises(frappe.ValidationError, api.approve, CLASS, "")
		self.assertEqual(api.approve(CLASS, "Faculty Examination Board, 20-11-2026")["status"], "Approved")
		self.assertEqual(api.publish([CLASS])["published"], 1)
		students = frappe.get_all("Mark Sheet Entry", filters={"parent": CLASS}, pluck="student")
		self.assertEqual([subject for _r, subject in self.sent], ["Results published"] * len(students))

		student = frappe.db.get_value("Mark Sheet Entry", {"parent": CLASS}, "student")
		frappe.set_user(frappe.db.get_value("Student", student, "user"))
		mine = [r for r in api.my_results()["results"] if r["student_group"] == CLASS]
		self.assertEqual((mine[0]["final_mark"], mine[0]["result"]), (68, "Pass"))

	def test_each_step_belongs_to_its_office(self):
		_as("lecturer.comp.osh@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.my_sheet, CLASS)  # not their class
		_as("examinations-officer.osh@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.sheet, CLASS)  # another campus
		_as(LECTURER)
		api.save_marks(CLASS, self._marks(70, 70))
		api.submit(CLASS)
		_as(EXAMS)
		self.assertRaises(frappe.PermissionError, api.moderate, CLASS)  # the department moderates
		_as("head-of-department.nurs@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.moderate, CLASS)  # another department
		_as(HOD)
		api.return_sheet(CLASS, "Check the examination marks")
		_as(LECTURER)
		sheet = api.my_sheet(CLASS)
		self.assertEqual((sheet["status"], sheet["return_note"]), ("Draft", "Check the examination marks"))
		_as("registrar@educore.localhost")
		self.assertTrue(api.rules()["can_edit"])
		_as(EXAMS)
		self.assertRaises(frappe.PermissionError, api.save_rules, {"pass_mark": 40})

	def test_failing_the_share_of_credits_set_by_the_university_means_probation(self):
		# the line low enough that this one failed course reaches it, whatever else the student passed
		frappe.db.set_single_value("Examination Settings", "probation_share", 1)
		frappe.clear_document_cache("Examination Settings", "Examination Settings")
		self.addCleanup(frappe.clear_document_cache, "Examination Settings", "Examination Settings")
		_as(LECTURER)
		api.save_marks(CLASS, self._marks(42, 20))
		api.submit(CLASS)
		_as(HOD)
		api.moderate(CLASS)
		_as(EXAMS)
		api.approve(CLASS, "Board")
		student = frappe.db.get_value("Mark Sheet Entry", {"parent": CLASS}, "student")
		api.publish([CLASS])
		frappe.set_user("Administrator")
		standing, note = frappe.db.get_value("Student", student, ["educore_academic_standing", "educore_standing_note"])
		self.assertEqual(standing, "Probation")
		self.assertIn("credits not passed", note)

	def test_a_supplementary_pass_is_capped_and_the_first_attempt_kept(self):
		_as(LECTURER)
		api.save_marks(CLASS, self._marks(50, 42))  # final 46: supplementary
		api.submit(CLASS)
		_as(HOD)
		api.moderate(CLASS)
		_as(EXAMS)
		api.approve(CLASS, "Board")
		api.publish([CLASS])

		_as(LECTURER)
		sheet = api.my_sheet(CLASS)
		self.assertEqual(sheet["supp_status"], "Open")
		self.assertTrue(all(e["writes_supplementary"] for e in sheet["entries"]))
		self.assertRaises(frappe.ValidationError, api.submit_supplementary, CLASS)  # marks still missing
		api.save_supplementary(CLASS, [{"student": e["student"], "supp_exam_mark": 70} for e in sheet["entries"]])
		self.assertEqual(api.submit_supplementary(CLASS)["supp_status"], "Submitted")

		_as(EXAMS)
		self.assertRaises(frappe.ValidationError, api.publish_supplementary, CLASS, "")
		done = api.publish_supplementary(CLASS, "Supplementary Examination Board, 20-01-2027")
		self.assertIn("Supplementary examination results published", [subject for _r, subject in self.sent])
		entry = done["entries"][0]
		# 50 x 50% + 70 x 50% = 60, recorded at the cap of 50
		self.assertEqual((entry["final_mark"], entry["result"], entry["grade"]), (50, "Pass", "C"))
		self.assertEqual((entry["first_result"], entry["first_final_mark"]), ("Supplementary", 46))

	def test_a_mark_not_entered_is_not_a_zero(self):
		_as(LECTURER)
		sheet = api.my_sheet(CLASS)
		saved = api.save_marks(CLASS, [{"student": e["student"], "ca_mark": 65, "exam_mark": None} for e in sheet["entries"]])
		entry = saved["entries"][0]
		self.assertEqual((entry["ca_mark"], entry["exam_mark"], entry["result"], entry["final_mark"]), (65, None, None, None))
		self.assertRaises(frappe.ValidationError, api.submit, CLASS)  # an examination mark is still missing
		# a real 0 is a mark
		zero = api.save_marks(CLASS, [{"student": e["student"], "ca_mark": 65, "exam_mark": 0} for e in sheet["entries"]])
		self.assertEqual(zero["entries"][0]["result"], "Fail")

	def test_a_special_examination_for_an_absence_counts_in_full(self):
		_as(LECTURER)
		sheet = api.my_sheet(CLASS)
		api.save_marks(CLASS, [{"student": e["student"], "ca_mark": 70, "absent": 1} for e in sheet["entries"]])
		api.submit(CLASS)
		_as(HOD)
		api.moderate(CLASS)
		_as(EXAMS)
		api.approve(CLASS, "Board")
		api.publish([CLASS])
		student = sheet["entries"][0]["student"]
		self.assertRaises(frappe.ValidationError, api.grant_special, CLASS, student, "")  # a reason is needed
		granted = api.grant_special(CLASS, student, "Hospitalised, medical certificate seen")
		self.assertEqual(next(e for e in granted["entries"] if e["student"] == student)["sitting"], "Special")

		_as(LECTURER)
		self.assertRaises(frappe.PermissionError, api.grant_special, CLASS, student, "x")  # the examinations office grants
		api.save_supplementary(CLASS, [{"student": e["student"], "supp_exam_mark": 70} for e in sheet["entries"]])
		api.submit_supplementary(CLASS)
		_as(EXAMS)
		done = api.publish_supplementary(CLASS, "Special Examination Board, 20-01-2027")
		entry = next(e for e in done["entries"] if e["student"] == student)
		# a special stands as the first attempt: 70, not capped
		self.assertEqual((entry["final_mark"], entry["result"], entry["first_result"]), (70, "Pass", "Absent"))

	def test_only_an_absent_student_gets_a_special(self):
		_as(LECTURER)
		api.save_marks(CLASS, self._marks(70, 70))
		api.submit(CLASS)
		_as(HOD)
		api.moderate(CLASS)
		_as(EXAMS)
		api.approve(CLASS, "Board")
		api.publish([CLASS])
		student = frappe.db.get_value("Mark Sheet Entry", {"parent": CLASS}, "student")
		self.assertRaises(frappe.ValidationError, api.grant_special, CLASS, student, "Ill")
