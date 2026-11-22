"""The staff dashboard: sections by position, figures within the user's campus and faculty (educore.api.v1.dashboard)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import dashboard


def _as(login: str) -> dict:
	frappe.set_user(f"{login}@educore.localhost")
	try:
		return dashboard.stats()["sections"]
	finally:
		frappe.set_user("Administrator")


class TestDashboard(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "registrar@educore.localhost"):
			self.skipTest("run the demo setup first")

	def test_each_position_sees_its_own_sections(self):
		self.assertTrue({"students", "admissions", "enrolment", "registration"} <= set(_as("registrar")))
		self.assertEqual(set(_as("bursar")), {"fees"})
		lecturer = _as("lecturer.comp.whk")
		self.assertNotIn("admissions", lecturer)
		self.assertNotIn("fees", lecturer)

	def test_figures_stay_within_the_users_campus(self):
		everyone = _as("registrar")
		oshakati = _as("admissions-officer.osh")
		self.assertEqual([c["label"] for c in oshakati["students"]["by_campus"]], ["Oshakati Campus"])
		self.assertLess(oshakati["admissions"]["pipeline"][0]["value"], everyone["admissions"]["pipeline"][0]["value"])
		self.assertTrue(all(o["label"].split("-")[1] == "OSH" for o in oshakati["admissions"]["offerings"]))

	def test_fees_add_up(self):
		fees = _as("bursar")["fees"]
		self.assertAlmostEqual(fees["invoiced"], fees["collected"] + fees["outstanding"], places=2)
		self.assertAlmostEqual(fees["invoiced"], sum(c["invoiced"] for c in fees["by_campus"]), places=2)

	def test_full_offerings_come_first(self):
		offerings = _as("registrar")["admissions"]["offerings"]
		shares = [o["taken"] / o["capacity"] for o in offerings]
		self.assertEqual(shares, sorted(shares, reverse=True))
