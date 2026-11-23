import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from educore.tests.utils import submitted

from educore.academics.calendar import ensure_academic_year, term
from educore.api.v1 import registry


class TestRegistryAPI(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "registry-officer.whk@educore.localhost"):
			self.skipTest("run the demo university and educore.access.test_users.create first")
		ensure_academic_year(2027)
		# Education creates the student's login and sends a welcome email: none from tests
		self._mute, frappe.flags.mute_emails = frappe.flags.mute_emails, True

	def tearDown(self):
		frappe.flags.mute_emails = self._mute
		frappe.set_user("Administrator")

	def _approved(self, offering="BCS-WHK-FT", email=None):
		applicant = submitted(frappe.get_doc(
			{
				"doctype": "Student Applicant",
				"first_name": "Test",
				"last_name": "Enrol",
				"educore_programme_offering": offering,
				"academic_year": "2027",
				"academic_term": term(2027, "Semester 1"),
				"student_email_id": email,
			}
		).insert(ignore_permissions=True))
		apply_workflow(applicant, "Approve")
		return applicant.name

	def _as(self, login):
		frappe.set_user(f"{login}@educore.localhost")

	def test_the_registry_officer_sees_their_campus_waiting_with_fees(self):
		name = self._approved()
		self._as("registry-officer.whk")
		page = registry.enrolments(academic_year="2027")
		self.assertTrue(page["can_enrol"])
		row = next(r for r in page["waiting"] if r["name"] == name)
		self.assertEqual(row["enrollment_date"], "2027-02-01")
		self.assertGreater(row["fees"], 0)
		self._as("registry-officer.osh")
		self.assertNotIn(name, [r["name"] for r in registry.enrolments(academic_year="2027")["waiting"]])

	def test_enrolling_makes_a_student_with_login_enrolment_and_invoice(self):
		name = self._approved()
		self._as("registry-officer.whk")
		row = registry.enrol(name, email="test.enrol.api@example.com")
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Student Applicant", name, "application_status"), "Admitted")
		self.assertEqual(row["student_login"], "test.enrol.api@example.com")
		self.assertEqual(row["enrollment_date"], "2027-02-01")
		invoice = frappe.get_doc("Sales Invoice", row["invoice"]["name"])
		self.assertEqual((invoice.docstatus, invoice.campus), (1, "Windhoek Campus"))
		self.assertIn("Enrolled by registry-officer.whk@educore.localhost", invoice.remarks)

	def test_the_email_on_the_application_becomes_the_login(self):
		name = self._approved(email="test.application.email@example.com")
		self._as("registry-officer.whk")
		row = registry.enrol(name)
		self.assertEqual(row["student_login"], "test.application.email@example.com")

	def test_an_email_is_required_and_must_be_new(self):
		name = self._approved()
		self._as("registry-officer.whk")
		self.assertRaises(frappe.ValidationError, registry.enrol, name)
		taken = frappe.db.get_value("Student", {"user": "student1.whk@educore.localhost"}, "student_email_id")
		if taken:
			self.assertRaises(frappe.ValidationError, registry.enrol, name, email=taken)

	def test_only_registry_staff_on_the_applicants_campus_enrol(self):
		name = self._approved()
		self._as("admissions-officer.whk")
		self.assertFalse(registry.enrolments(academic_year="2027")["can_enrol"])
		self.assertRaises(frappe.PermissionError, registry.enrol, name, email="x.enrol@example.com")
		self._as("registry-officer.osh")
		self.assertRaises(frappe.PermissionError, registry.enrol, name, email="x.enrol@example.com")
