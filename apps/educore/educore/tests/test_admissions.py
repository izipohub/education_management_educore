import frappe
from frappe.model.workflow import WorkflowTransitionError, apply_workflow
from frappe.tests import IntegrationTestCase

from educore.tests.utils import submitted

from educore.academics.calendar import ensure_academic_year, term


class TestAdmissionDecisions(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "admissions-officer.osh@educore.localhost"):
			self.skipTest("run the demo university and educore.access.test_users.create first")
		ensure_academic_year(2027)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _applicant(self, offering="DIT-OSH-FT"):
		return submitted(frappe.get_doc(
			{
				"doctype": "Student Applicant",
				"first_name": "Test",
				"last_name": "Decision",
				"educore_programme_offering": offering,
				"academic_year": "2027",
				"academic_term": term(2027, "Semester 1"),
			}
		).insert(ignore_permissions=True))

	def _as(self, login, applicant, action):
		frappe.set_user(f"{login}@educore.localhost")
		try:
			return apply_workflow(frappe.get_doc("Student Applicant", applicant.name), action)
		finally:
			frappe.set_user("Administrator")

	def test_an_officer_approves_on_their_campus_and_the_decision_is_recorded(self):
		approved = self._as("admissions-officer.osh", self._applicant(), "Approve")
		self.assertEqual(approved.application_status, "Approved")
		self.assertEqual(approved.educore_decided_by, "admissions-officer.osh@educore.localhost")
		self.assertTrue(approved.educore_decided_on)

	def test_an_officer_cannot_decide_for_another_campus(self):
		self.assertRaises(frappe.PermissionError, self._as, "admissions-officer.whk", self._applicant(), "Approve")

	def test_only_admissions_staff_decide(self):
		self.assertRaises(WorkflowTransitionError, self._as, "registry-officer.osh", self._applicant(), "Approve")

	def test_a_rejection_needs_a_reason(self):
		applicant = self._applicant()
		self.assertRaises(frappe.ValidationError, self._as, "admissions-officer.osh", applicant, "Reject")
		frappe.db.set_value("Student Applicant", applicant.name, "educore_decision_reason", "Test reason")
		self.assertEqual(self._as("admissions-officer.osh", applicant, "Reject").application_status, "Rejected")

	def test_reconsidering_reopens_the_application(self):
		applicant = self._applicant()
		frappe.db.set_value("Student Applicant", applicant.name, "educore_decision_reason", "Test reason")
		self._as("admissions-officer.osh", applicant, "Reject")
		# only the registrar reopens a rejection
		self.assertRaises(WorkflowTransitionError, self._as, "admissions-officer.osh", applicant, "Reconsider")
		reopened = self._as("registrar", applicant, "Reconsider")
		self.assertEqual(reopened.application_status, "Applied")
		self.assertFalse(reopened.educore_decided_by or reopened.educore_decision_reason)

	def test_no_approval_beyond_the_intake_capacity(self):
		# one place left, whatever earlier tests in this class (rolled back together) already approved
		taken = frappe.db.count(
			"Student Applicant",
			{
				"educore_programme_offering": "DIT-OSH-FT",
				"academic_year": "2027",
				"application_status": ("in", ("Approved", "Admitted")),
			},
		)
		frappe.db.set_value("Programme Offering", "DIT-OSH-FT", "intake_capacity", taken + 1)
		frappe.clear_document_cache("Programme Offering", "DIT-OSH-FT")
		try:
			first, second = self._applicant(), self._applicant()
			self._as("admissions-officer.osh", first, "Approve")
			self.assertRaises(frappe.ValidationError, self._as, "admissions-officer.osh", second, "Approve")
			# withdrawing an offer frees the place
			frappe.db.set_value("Student Applicant", first.name, "educore_decision_reason", "Offer declined")
			self._as("admissions-officer.osh", first, "Withdraw Offer")
			self.assertEqual(self._as("admissions-officer.osh", second, "Approve").application_status, "Approved")
		finally:
			frappe.db.set_value("Programme Offering", "DIT-OSH-FT", "intake_capacity", 60)
			frappe.clear_document_cache("Programme Offering", "DIT-OSH-FT")
