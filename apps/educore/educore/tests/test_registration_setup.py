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

	def test_the_registrar_changes_the_academic_rules_not_the_money(self):
		data = api.save_settings({"max_credits": 160, "approval_needed": 1})
		self.assertEqual(data["settings"]["max_credits"], 160)
		self.assertRaises(frappe.ValidationError, api.save_settings, {"max_credits": 999})
		# the deposit and the balance allowed are Finance's (educore.api.v1.fee_settings)
		self.assertRaises(frappe.PermissionError, api.save_settings, {"deposit_value": 50})
		self.assertRaises(frappe.PermissionError, api.save_settings, {"deposit_type": "Amount"})
		# unchanged values pass, as the screen sends them back
		api.save_settings(data["settings"])

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
		data = api.save_period({"academic_year": "2031", "opens_on": "2031-01-05", "closes_on": "2031-01-31", "late_until": "2031-02-07"})
		period = next(p for p in data["periods"] if p["academic_year"] == "2031")
		self.assertEqual(period["state"], "upcoming")
		# the late fee is Finance's
		self.assertRaises(frappe.PermissionError, api.save_period, {"late_fee": 300}, name=period["name"])
		self.assertNotIn("2031", data["academic_years"])
		self.assertRaises(frappe.ValidationError, api.save_period, {"academic_year": "2031", "opens_on": "2031-01-05", "closes_on": "2031-01-31"})

	def test_only_the_registrar(self):
		frappe.set_user("faculty-officer.fst.osh@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.setup)
