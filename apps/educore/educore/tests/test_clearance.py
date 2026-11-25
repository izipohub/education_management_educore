"""Financial holds and clearance (educore.finance.clearance, educore.api.v1.clearance)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import clearance as api
from educore.api.v1 import graduation as graduation_api
from educore.api.v1 import registration
from educore.tests.test_graduation import FINISHER, PROGRAMME, SENATE

FEES_KMP = "student-fees-officer.kmp@educore.localhost"
FEES_OSH = "student-fees-officer.osh@educore.localhost"
BURSAR = "bursar@educore.localhost"
REGISTRAR = "registrar@educore.localhost"
NDAPEWA = "student1.whk@educore.localhost"


class TestClearance(IntegrationTestCase):
	def setUp(self):
		self.finisher = frappe.db.get_value("Student", {"user": FINISHER}, "name")
		self.ndapewa = frappe.db.get_value("Student", {"user": NDAPEWA}, "name")
		if not self.finisher or not frappe.db.exists("User", FEES_KMP):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("clearance_test")
		frappe.set_user("Administrator")
		frappe.db.set_value("Program", PROGRAMME, "educore_credits", 48)
		frappe.db.set_value("Student", self.finisher, {"educore_completed_on": None, "educore_academic_standing": "Good standing"})
		frappe.clear_document_cache("Program", PROGRAMME)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="clearance_test")
		frappe.clear_document_cache("Program", PROGRAMME)
		frappe.clear_document_cache("Registration Settings", "Registration Settings")

	def test_a_hold_blocks_registration_until_it_is_lifted(self):
		frappe.set_user(BURSAR)
		page = api.place_hold(self.ndapewa, "Cheque payment returned unpaid")
		self.assertFalse(page["cleared"])
		frappe.set_user(NDAPEWA)
		self.assertTrue(any("Financial hold: Cheque payment returned unpaid" in b for b in registration.status()["blockers"]))
		frappe.set_user(BURSAR)
		page = api.lift_hold(page["holds"][0]["name"], "Paid in cash at the cashier")
		self.assertTrue(page["cleared"])
		self.assertEqual(page["history"][0]["status"], "Lifted")
		frappe.set_user(NDAPEWA)
		self.assertFalse(any("Financial hold" in b for b in registration.status()["blockers"]))

	def test_graduation_and_the_certificate_need_clearance(self):
		frappe.set_user(FEES_KMP)
		api.place_hold(self.finisher, "Library fine unpaid")
		frappe.set_user(REGISTRAR)
		row = next(r for r in graduation_api.candidates()["rows"] if r["name"] == self.finisher)
		self.assertFalse(row["clearance"]["cleared"])
		self.assertRaises(frappe.ValidationError, graduation_api.confirm, [self.finisher], SENATE)
		# the university may graduate without clearance
		frappe.db.set_single_value("Registration Settings", "graduation_needs_clearance", 0)
		frappe.clear_document_cache("Registration Settings", "Registration Settings")
		graduation_api.confirm([self.finisher], SENATE)

	def test_owing_more_than_allowed_is_not_cleared(self):
		from educore.finance import clearance

		lukas = frappe.db.get_value("Student", {"user": "student2.whk@educore.localhost"}, "name")
		state = clearance.status(lukas)
		self.assertFalse(state["cleared"])
		self.assertTrue(state["reasons"][0].startswith("Fees owing"))
		frappe.db.set_single_value("Registration Settings", "clearance_max_owing", state["owing"])
		frappe.clear_document_cache("Registration Settings", "Registration Settings")
		self.assertTrue(clearance.status(lukas)["cleared"])

	def test_finance_only_and_each_campus_its_own(self):
		frappe.set_user(FEES_OSH)
		self.assertNotIn(self.finisher, {r["name"] for r in api.students()["rows"]})
		self.assertRaises(frappe.PermissionError, api.place_hold, self.finisher, "Not ours")
		frappe.set_user(REGISTRAR)
		self.assertRaises(frappe.PermissionError, api.students)
		frappe.set_user(FEES_KMP)
		self.assertRaises(frappe.ValidationError, api.place_hold, self.finisher, "  ")
