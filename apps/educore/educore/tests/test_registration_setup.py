"""The Registrar sets registration periods and rules (educore.api.v1.registration_setup)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.academics.calendar import ensure_academic_year
from educore.api.v1 import registration_setup as api

REGISTRAR = "registrar@educore.localhost"


class TestRegistrationSetup(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", REGISTRAR):
			self.skipTest("run the demo setup first")
		saved = {f: frappe.db.get_single_value("Registration Settings", f) for f in api.SETTINGS_FIELDS}

		def restore():
			frappe.set_user("Administrator")
			doc = frappe.get_single("Registration Settings")
			doc.update(saved)
			doc.save(ignore_permissions=True)

		self.addCleanup(restore)
		frappe.set_user(REGISTRAR)

	def test_the_registrar_changes_the_rules_within_limits(self):
		data = api.save_settings({"max_credits": 160, "deposit_type": "Percent of the year's fees", "deposit_value": 25})
		self.assertEqual((data["settings"]["max_credits"], data["settings"]["deposit_value"]), (160, 25))
		self.assertRaises(frappe.ValidationError, api.save_settings, {"deposit_value": 120})
		self.assertRaises(frappe.ValidationError, api.save_settings, {"deposit_type": "Barter"})
		self.assertRaises(frappe.ValidationError, api.save_settings, {"max_outstanding": -1})

	def test_a_period_needs_dates_in_order(self):
		frappe.set_user("Administrator")
		ensure_academic_year(2031)
		frappe.set_user(REGISTRAR)
		self.assertRaises(frappe.ValidationError, api.save_period, {"academic_year": "2031", "opens_on": "2031-01-20", "closes_on": "2031-01-10"})
		self.assertRaises(
			frappe.ValidationError,
			api.save_period,
			{"academic_year": "2031", "opens_on": "2031-01-05", "closes_on": "2031-01-31", "late_until": "2031-01-20"},
		)
		data = api.save_period({"academic_year": "2031", "opens_on": "2031-01-05", "closes_on": "2031-01-31", "late_until": "2031-02-07", "late_fee": 300})
		period = next(p for p in data["periods"] if p["academic_year"] == "2031")
		self.assertEqual((period["late_fee"], period["state"]), (300, "upcoming"))
		self.assertNotIn("2031", data["academic_years"])
		self.assertRaises(frappe.ValidationError, api.save_period, {"academic_year": "2031", "opens_on": "2031-01-05", "closes_on": "2031-01-31"})

	def test_only_the_registrar(self):
		frappe.set_user("faculty-officer.fst.osh@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.setup)
