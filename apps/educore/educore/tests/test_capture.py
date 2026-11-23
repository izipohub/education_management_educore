"""Paper applications typed in by admissions officers (educore.api.v1.admissions.capture)"""

import frappe
from frappe.model.workflow import WorkflowPermissionError
from frappe.tests import IntegrationTestCase

from educore.academics.calendar import ensure_academic_year
from educore.api.v1 import admissions


class TestCapture(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "admissions-officer.whk@educore.localhost"):
			self.skipTest("run the demo university and educore.access.test_users.create first")
		ensure_academic_year(2027)
		self._mute, frappe.flags.mute_emails = frappe.flags.mute_emails, True

	def tearDown(self):
		frappe.flags.mute_emails = self._mute
		frappe.set_user("Administrator")

	def _as(self, login):
		frappe.set_user(f"{login}@educore.localhost")

	def _form(self, **changes):
		self._as("admissions-officer.whk")
		intake = admissions.capture_options()["intakes"][0]["name"]
		form = {
			"intake": intake,
			# each test its own address, so captures in one run never collide
			"email": f"paper.{frappe.generate_hash(length=8)}@example.com",
			"received_on": "2026-11-20",
			"personal": {"first_name": "Paper", "last_name": "Applicant", "date_of_birth": "2007-03-14", "gender": "Female"},
			"choices": ["BCS-WHK-FT"],
		}
		form.update(changes)
		return form

	def test_an_officer_captures_a_paper_application_and_it_is_submitted(self):
		form = self._form()
		name = admissions.capture(form)["name"]
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Student Applicant", name)
		self.assertEqual(doc.application_status, "Applied")
		self.assertEqual(doc.student_email_id, form["email"])
		self.assertFalse(doc.get("educore_applicant_user"))  # no login: a paper application
		self.assertEqual(doc.educore_programme_offering, "BCS-WHK-FT")
		self.assertEqual(str(doc.application_date), "2026-11-20")

	def test_the_email_is_required_and_once_per_year(self):
		self.assertRaises(frappe.ValidationError, admissions.capture, self._form(email=""))
		form = self._form()
		admissions.capture(form)
		self.assertRaises(frappe.ValidationError, admissions.capture, form)

	def test_the_officer_who_captured_it_does_not_decide_on_it(self):
		name = admissions.capture(self._form())["name"]
		self.assertRaises((WorkflowPermissionError, frappe.ValidationError), admissions.decide, name, "Approve")

	def test_only_admissions_captures(self):
		form = self._form()
		self._as("registry-officer.whk")
		self.assertRaises(frappe.PermissionError, admissions.capture, form)

	def test_the_paper_fee_and_the_cashiers_receipt_are_recorded(self):
		from educore.admissions.application import settings

		paid = admissions.capture(self._form(receipt_number="R-10234"))["name"]
		unpaid = admissions.capture(self._form())["name"]
		frappe.set_user("Administrator")
		paper_fee = settings().fee_paper_local
		paid_doc = frappe.get_doc("Student Applicant", paid)
		self.assertEqual((paid_doc.educore_fee_status, paid_doc.educore_fee_amount), ("Paid", paper_fee))
		self.assertIn("R-10234", paid_doc.educore_fee_note)
		self.assertEqual(frappe.db.get_value("Student Applicant", unpaid, "educore_fee_status"), "Unpaid")
