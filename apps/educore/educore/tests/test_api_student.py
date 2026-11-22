import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import student


class TestStudentPortalAPI(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student", {"user": "student1.kmp@educore.localhost"}):
			self.skipTest("run the demo university, users and educore.setup.demo_students.create first")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _overview(self, login):
		frappe.set_user(f"{login}@educore.localhost")
		return student.overview()

	def test_a_student_sees_their_record_programme_and_courses(self):
		data = self._overview("student1.kmp")
		self.assertEqual(data["student"]["name"], "Anna Beukes")
		self.assertEqual(data["student"]["campus"], "Keetmanshoop Campus")
		current = data["enrolments"][0]
		self.assertEqual((current["offering"], current["nqf_level"]), ("BACC-KMP-PT", 7))
		self.assertEqual(len(current["courses"]), 5)
		self.assertIn("ACC1511", [c["code"] for c in current["courses"]])

	def test_the_fee_statement_runs_to_what_is_owed(self):
		fees = self._overview("student1.kmp")["fees"]
		self.assertEqual((fees["billed"], fees["paid"], fees["owing"]), (20300, 10150, 10150))
		self.assertEqual([e["kind"] for e in fees["entries"]], ["invoice", "payment"])
		self.assertEqual(fees["entries"][-1]["balance"], fees["owing"])

	def test_each_student_sees_only_their_own(self):
		anna = self._overview("student1.kmp")
		lukas = self._overview("student2.whk")
		self.assertNotEqual(anna["student"]["number"], lukas["student"]["number"])
		self.assertEqual(lukas["fees"]["paid"], 0)
		references = {e["reference"] for e in anna["fees"]["entries"]}
		self.assertFalse(references & {e["reference"] for e in lukas["fees"]["entries"]})

	def test_staff_are_refused(self):
		self.assertRaises(frappe.PermissionError, self._overview, "registrar")
