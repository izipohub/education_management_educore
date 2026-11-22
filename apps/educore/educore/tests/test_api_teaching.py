import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import teaching


class TestTeachingAPI(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Group", "CMP1511 WHK 2026"):
			self.skipTest("run the demo university, users and educore.setup.demo_students.create first")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _classes(self, login, **kwargs):
		frappe.set_user(f"{login}@educore.localhost")
		return teaching.my_classes(**kwargs)

	def test_a_lecturer_sees_the_classes_they_teach_with_their_students(self):
		data = self._classes("lecturer.accf.kmp")
		self.assertTrue(data["linked"])
		self.assertEqual(data["academic_year"], "2026")
		classes = {c["code"]: c for c in data["classes"]}
		self.assertEqual(set(classes), {"ACC1511", "ACC1521", "FIN2511"})
		self.assertEqual({s["student_name"] for s in classes["ACC1511"]["students"]}, {"Anna Beukes", "Petrus Kooper"})
		self.assertTrue(all(c["campus"] == "Keetmanshoop Campus" for c in data["classes"]))

	def test_co_lecturers_see_each_other(self):
		classes = self._classes("hod-lecturer.comp")["classes"]
		self.assertIn("Lecturer COMP Windhoek", classes[0]["co_lecturers"])

	def test_a_lecturer_sees_no_one_elses_classes(self):
		windhoek = {c["name"] for c in self._classes("lecturer.comp.whk")["classes"]}
		oshakati = {c["name"] for c in self._classes("lecturer.comp.osh")["classes"]}
		self.assertTrue(windhoek)
		self.assertFalse(windhoek & oshakati)

	def test_a_login_without_an_hr_record_is_told_so(self):
		self.assertEqual(self._classes("lecturer"), {"linked": False, "academic_year": None, "academic_years": [], "classes": []})

	def test_students_are_refused(self):
		self.assertRaises(frappe.PermissionError, self._classes, "student1.kmp")
