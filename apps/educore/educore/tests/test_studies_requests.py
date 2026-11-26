"""Interrupting or cancelling studies (educore.api.v1.studies_requests)"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from educore.api.v1 import registration
from educore.api.v1 import studies_requests as api
from educore.registration import rules

NDAPEWA = "student1.whk@educore.localhost"  # Windhoek, registered for 2026, free to register for 2027
REGISTRY_WHK = "registry-officer.whk@educore.localhost"
REGISTRY_OSH = "registry-officer.osh@educore.localhost"
FACULTY = "faculty-officer.fst.whk@educore.localhost"


class TestStudiesRequests(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"user": NDAPEWA}, "name")
		if not self.student or not frappe.db.exists("User", REGISTRY_WHK):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("studies_request_test")
		frappe.set_user(NDAPEWA)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="studies_request_test")

	def _decide(self, user=REGISTRY_WHK):
		frappe.set_user(user)
		return api.queue()["rows"][0]["name"]

	def _enrolled(self):
		enrolment = frappe.db.get_value("Program Enrollment", {"student": self.student, "academic_year": "2026", "docstatus": 1})
		return frappe.db.count("Course Enrollment", {"program_enrollment": enrolment})

	def test_an_interruption_pauses_registration_until_the_return_year(self):
		state = api.mine()
		self.assertTrue(state["can_request"])
		self.assertIn("2027", state["return_years"])
		self.assertGreater(self._enrolled(), 0)
		api.request("Interruption", nowdate(), "Family responsibilities", "2027")
		self.assertFalse(api.mine()["can_request"])  # one at a time

		api.approve(self._decide())
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Student", self.student, "educore_interrupted_until"), "2027")
		self.assertEqual(self._enrolled(), 0)  # off this year's class lists
		self.assertEqual(frappe.db.get_value("Student", self.student, "enabled"), 1)
		# 2027 is the return year: registration is open to her again
		period = rules.current_period()
		self.assertFalse(any("interrupted" in b for b in rules.blockers(self.student, "BCS-WHK-FT", period)))

	def test_interrupted_for_longer_blocks_registration_and_returning_lifts_it(self):
		api.request("Interruption", nowdate(), "Medical", "2027")
		api.approve(self._decide())
		frappe.set_user("Administrator")
		frappe.db.set_value("Student", self.student, "educore_interrupted_until", "2028")
		frappe.set_user(NDAPEWA)
		self.assertTrue(any("interrupted" in b for b in registration.status()["blockers"]))
		frappe.set_user(REGISTRY_WHK)
		api.resume(self.student)
		frappe.set_user(NDAPEWA)
		self.assertFalse(any("interrupted" in b for b in registration.status()["blockers"]))

	def test_a_cancellation_ends_the_studies(self):
		api.request("Cancellation", add_days(nowdate(), -2), "Moving abroad")
		api.approve(self._decide())
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Student", self.student, "enabled"), 0)
		self.assertEqual(self._enrolled(), 0)
		frappe.set_user(NDAPEWA)
		self.assertTrue(any("cancelled" in b for b in registration.status()["blockers"]))
		self.assertFalse(api.mine()["can_request"])

	def test_the_request_needs_a_reason_a_past_date_and_a_return_year(self):
		self.assertRaises(frappe.ValidationError, api.request, "Cancellation", nowdate(), " ")
		self.assertRaises(frappe.ValidationError, api.request, "Cancellation", add_days(nowdate(), 5), "Moving")
		self.assertRaises(frappe.ValidationError, api.request, "Interruption", nowdate(), "Medical", "2026")
		self.assertRaises(frappe.ValidationError, api.request, "Holiday", nowdate(), "Medical")

	def test_declined_with_a_reason_by_the_students_campus_registry(self):
		api.request("Interruption", nowdate(), "Work", "2027")
		frappe.set_user(REGISTRY_OSH)
		self.assertEqual(api.queue()["rows"], [])
		name = self._decide()
		frappe.set_user(REGISTRY_OSH)
		self.assertRaises(frappe.PermissionError, api.approve, name)
		frappe.set_user(REGISTRY_WHK)
		self.assertRaises(frappe.ValidationError, api.decline, name, "")
		api.decline(name, "Come and see the Registry first")
		frappe.set_user(NDAPEWA)
		state = api.mine()
		self.assertEqual(state["requests"][0]["review_note"], "Come and see the Registry first")
		self.assertTrue(state["can_request"])

	def test_the_faculty_does_not_decide(self):
		frappe.set_user(FACULTY)
		self.assertRaises(frappe.PermissionError, api.queue)

	def test_a_campus_transfer_moves_the_student_and_their_next_registration(self):
		state = api.mine()
		if not state["transfer_offerings"]:
			self.skipTest("the programme is not offered at another campus")
		to = state["transfer_offerings"][0]
		self.assertNotEqual(to["campus"], state["campus"])
		self.assertIn("2027", state["transfer_years"])
		self.assertNotIn("2026", state["transfer_years"])  # registered for 2026 already
		self.assertRaises(frappe.ValidationError, api.request, "Campus transfer", None, "Moving", None, "BCS-WHK-FT", "2027")
		self.assertRaises(frappe.ValidationError, api.request, "Campus transfer", None, "Moving", None, to["name"], "2026")
		api.request("Campus transfer", None, "My family moved", None, to["name"], "2027")
		api.approve(self._decide())

		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Student", self.student, "campus"), to["campus"])
		self.assertEqual(rules.offering_for(self.student, "2027"), to["name"])
		self.assertEqual(rules.offering_for(self.student, "2026"), "BCS-WHK-FT")
		frappe.set_user(NDAPEWA)
		self.assertEqual(registration.status()["offering"], to["name"])

		from educore.academics import history

		events = history.of_student(self.student)
		self.assertEqual(events[0]["event"], f"Moved to {to['campus']}")
		self.assertTrue(any(e["event"].startswith("Registered for 2026") for e in events))
		self.assertTrue(any(e["event"] == "Admitted" for e in events))
