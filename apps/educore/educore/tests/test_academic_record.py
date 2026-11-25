"""The academic record (educore.api.v1.documents.academic_record): the student's own, or the registry's"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import documents

OWNER = "student1.osh@educore.localhost"
OTHER = "student2.osh@educore.localhost"
REGISTRAR = "registrar@educore.localhost"


class TestAcademicRecord(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"user": OWNER}, "name")
		if not self.student or not frappe.db.exists("User", OTHER):
			self.skipTest("run the demo setup first")
		self.addCleanup(frappe.set_user, "Administrator")

	def _record(self, user):
		frappe.set_user(user)
		frappe.local.response = frappe._dict()
		documents.academic_record(self.student)
		return frappe.local.response

	def test_the_student_downloads_their_own_record(self):
		response = self._record(OWNER)
		self.assertEqual(response.type, "pdf")
		self.assertTrue(response.filecontent.startswith(b"%PDF"))

	def test_the_registry_downloads_any_record(self):
		self.assertEqual(self._record(REGISTRAR).type, "pdf")

	def test_another_student_is_refused(self):
		self.assertRaises(frappe.PermissionError, self._record, OTHER)

	def test_the_verify_code_confirms_the_student(self):
		frappe.set_user("Guest")
		documents.verify(self.student, documents._code(self.student))
		self.assertEqual(frappe.local.message_title, "Academic record confirmed")
		documents.verify(self.student, "not-the-code")
		self.assertEqual(frappe.local.message_title, "Not confirmed")
