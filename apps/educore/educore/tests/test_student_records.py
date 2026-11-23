"""Student records, application fees for Finance, and the PDFs (educore.api.v1.student_records, application_fees,
documents)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import application_fees, documents, student_records


def _as(login: str):
	frappe.set_user(f"{login}@educore.localhost")


class TestStudentRecords(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "registry-officer.osh@educore.localhost"):
			self.skipTest("run the demo setup first")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_each_office_sees_its_own_campus(self):
		_as("registrar")
		everyone = {r["student_name"] for r in student_records.students()["rows"]}
		_as("registry-officer.osh")
		oshakati = student_records.students()["rows"]
		self.assertTrue(oshakati)
		self.assertTrue(all(r["campus"] == "Oshakati Campus" for r in oshakati))
		self.assertLess(len(oshakati), len(everyone))

	def test_a_record_carries_the_next_of_kin_and_registrations(self):
		_as("registrar")
		row = next(r for r in student_records.students()["rows"] if r["student_name"] == "Martha Shilongo")
		record = student_records.student(row["name"])
		self.assertTrue(record["guardians"])
		self.assertTrue(any(e["status"] == "Registered" for e in record["enrolments"]))
		_as("registry-officer.whk")
		self.assertRaises(frappe.PermissionError, student_records.student, row["name"])

	def test_students_and_applicants_are_not_let_in(self):
		_as("student1.whk")
		self.assertRaises(frappe.PermissionError, student_records.students)
		self.assertRaises(frappe.PermissionError, application_fees.fees)

	def test_finance_lists_fees_admissions_does_not(self):
		_as("finance-officer")
		page = application_fees.fees("Unpaid")
		self.assertIn("Unpaid", page["counts"])
		_as("admissions-officer.osh")
		self.assertRaises(frappe.PermissionError, application_fees.fees)

	def test_proof_of_registration_for_the_student_and_the_registry_only(self):
		frappe.set_user("Administrator")
		student = frappe.db.get_value("Student", {"user": "student1.whk@educore.localhost"}, "name")
		enrollment = frappe.db.get_value("Program Enrollment", {"student": student, "docstatus": 1}, "name")
		_as("student1.whk")
		documents.proof_of_registration(enrollment)
		self.assertTrue(frappe.local.response.filecontent.startswith(b"%PDF"))
		_as("student1.osh")
		self.assertRaises(frappe.PermissionError, documents.proof_of_registration, enrollment)
