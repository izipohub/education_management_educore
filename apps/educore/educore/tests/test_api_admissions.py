import frappe
from frappe.tests import IntegrationTestCase

from educore.academics.calendar import ensure_academic_year, term
from educore.api.v1 import admissions


class TestAdmissionsAPI(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "admissions-officer.osh@educore.localhost"):
			self.skipTest("run the demo university and educore.access.test_users.create first")
		ensure_academic_year(2027)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _applicant(self, offering="DIT-OSH-FT"):
		return frappe.get_doc(
			{
				"doctype": "Student Applicant",
				"first_name": "Test",
				"last_name": "API",
				"educore_programme_offering": offering,
				"academic_year": "2027",
				"academic_term": term(2027, "Semester 1"),
			}
		).insert(ignore_permissions=True)

	def _as(self, login):
		frappe.set_user(f"{login}@educore.localhost")

	def test_an_officer_lists_their_campus_with_the_actions_they_may_take(self):
		applicant = self._applicant()
		self._as("admissions-officer.osh")
		page = admissions.applications(status="Applied", academic_year="2027")
		self.assertEqual({row["campus"] for row in page["rows"]}, {"Oshakati Campus"})
		row = next(r for r in page["rows"] if r["name"] == applicant.name)
		self.assertEqual(row["actions"], ["Approve", "Reject"])
		self.assertEqual(row["applicant"], "Test API")
		self.assertIn("DIT-OSH-FT|2027", page["capacity"])

	def test_staff_without_admissions_rights_see_no_actions(self):
		self._applicant()
		self._as("registry-officer.osh")
		rows = admissions.applications(status="Applied", academic_year="2027")["rows"]
		self.assertTrue(rows)
		self.assertTrue(all(row["actions"] == [] for row in rows))

	def test_deciding_records_the_decision(self):
		applicant = self._applicant()
		self._as("admissions-officer.osh")
		row = admissions.decide(applicant.name, "Approve")
		self.assertEqual(row["status"], "Approved")
		self.assertEqual(row["decided_by"], "admissions-officer.osh@educore.localhost")
		self.assertEqual(row["actions"], ["Withdraw Offer"])

	def test_a_rejection_needs_a_reason_and_keeps_it(self):
		applicant = self._applicant()
		self._as("admissions-officer.osh")
		self.assertRaises(frappe.ValidationError, admissions.decide, applicant.name, "Reject")
		row = admissions.decide(applicant.name, "Reject", reason="Incomplete documents")
		self.assertEqual((row["status"], row["decision_reason"]), ("Rejected", "Incomplete documents"))

	def test_no_decision_for_another_campus_and_nothing_is_written(self):
		applicant = self._applicant()
		self._as("admissions-officer.whk")
		self.assertRaises(frappe.PermissionError, admissions.decide, applicant.name, "Reject", reason="x")
		frappe.set_user("Administrator")
		self.assertFalse(frappe.db.get_value("Student Applicant", applicant.name, "educore_decision_reason"))
