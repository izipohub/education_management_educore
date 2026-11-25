"""Emails to students about decisions on their studies (educore.academics.notify)"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from educore.academics import notify
from educore.api.v1 import registration
from educore.api.v1 import studies_requests

NDAPEWA = "student1.whk@educore.localhost"
REGISTRY_WHK = "registry-officer.whk@educore.localhost"
FST_WHK = "faculty-officer.fst.whk@educore.localhost"


class TestStudentNotify(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"user": NDAPEWA}, "name")
		if not self.student or not frappe.db.exists("User", REGISTRY_WHK):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("notify_test")
		self.sent = []
		patcher = patch.object(notify, "_deliver", lambda recipient, subject, body, doc: self.sent.append((recipient, subject, body, doc.doctype)))
		patcher.start()
		self.addCleanup(patcher.stop)
		self._setting(1)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="notify_test")
		frappe.clear_document_cache("Registration Settings", "Registration Settings")

	def _setting(self, value):
		frappe.db.set_single_value("Registration Settings", "notify_students", value)
		frappe.clear_document_cache("Registration Settings", "Registration Settings")

	def test_the_registration_decision_is_emailed(self):
		frappe.set_user(NDAPEWA)
		state = registration.status()
		registration.save([c["course"] for c in state["courses"] if c["year"] == state["year_of_study"]])
		registration.submit()
		frappe.set_user(FST_WHK)
		name = next(r for r in registration.queue()["rows"] if r["student_name"] == "Ndapewa Amukoto")["name"]
		registration.approve(name)
		recipient, subject, body, doctype = self.sent[-1]
		self.assertEqual((recipient, subject, doctype), (NDAPEWA, "Registration 2027 approved", "Program Enrollment"))
		self.assertIn("Dear Ndapewa", body)
		self.assertIn("/my-studies", body)

	def test_a_declined_request_carries_the_registrys_reason(self):
		frappe.set_user(NDAPEWA)
		studies_requests.request("Interruption", nowdate(), "Work", "2027")
		frappe.set_user(REGISTRY_WHK)
		studies_requests.decline(studies_requests.queue()["rows"][0]["name"], "Come & see us first")
		recipient, subject, body, doctype = self.sent[-1]
		self.assertEqual((subject, doctype), ("Request about your studies declined", "Studies Request"))
		self.assertIn("interrupt your studies is declined: Come &amp; see us first", body)

	def test_nothing_is_sent_when_the_university_does_not_email_students(self):
		self._setting(0)
		notify.send(self.student, "results_published", frappe.get_doc("Student", self.student), courses="Calculus I")
		self.assertEqual(self.sent, [])

	def test_several_courses_read_as_a_list(self):
		self.assertEqual(notify.courses(["Databases"]), "Databases")
		self.assertEqual(notify.courses(["B", "A", "C", "A"]), "A, B and C")
