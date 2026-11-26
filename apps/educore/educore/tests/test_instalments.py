"""Instalment plans (educore.finance.instalments): the year's invoices carry them, and what is due follows them"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from educore.api.v1 import fee_settings
from educore.api.v1 import registration as api
from educore.api.v1 import student as student_api
from educore.finance import instalments

NDAPEWA = "student1.whk@educore.localhost"  # free to register for 2027
FST_WHK = "faculty-officer.fst.whk@educore.localhost"
BURSAR = "bursar@educore.localhost"
PLAN = [{"due_date": "2027-02-15", "share": 40}, {"due_date": "2027-05-15", "share": 30}, {"due_date": "2027-08-16", "share": 30}]


class TestInstalments(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Registration Period", "2027") or not frappe.db.exists("User", NDAPEWA):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("instalments_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="instalments_test")

	def _approve(self) -> str:
		frappe.set_user(NDAPEWA)
		state = api.status()
		api.save([c["course"] for c in state["courses"] if c["year"] == state["year_of_study"] and c["state"] == "open"])
		api.submit()
		frappe.set_user(FST_WHK)
		row = next(r for r in api.queue()["rows"] if r["student_name"] == "Ndapewa Amukoto")
		api.approve(row["name"])
		frappe.set_user("Administrator")
		return frappe.db.get_value("Sales Invoice", {"educore_program_enrollment": row["name"], "docstatus": 1}, "name")

	def test_the_bursar_sets_a_plan_that_adds_up(self):
		frappe.set_user(BURSAR)
		bad = [{"due_date": "2027-02-15", "share": 40}, {"due_date": "2027-05-15", "share": 40}]
		self.assertRaises(frappe.ValidationError, fee_settings.save, {"instalment_plans": {"2027": bad}})
		twice = [{"due_date": "2027-02-15", "share": 50}, {"due_date": "2027-02-15", "share": 50}]
		self.assertRaises(frappe.ValidationError, fee_settings.save, {"instalment_plans": {"2027": twice}})
		page = fee_settings.save({"instalment_plans": {"2027": PLAN}})
		self.assertEqual([r["share"] for r in page["instalment_plans"]["2027"]], [40, 30, 30])
		page = fee_settings.save({"instalment_plans": {"2027": []}})  # back to fees due in full
		self.assertNotIn("2027", page["instalment_plans"])
		frappe.set_user("registrar@educore.localhost")  # the Bursar's, not the Registrar's
		self.assertRaises(frappe.PermissionError, fee_settings.save, {"instalment_plans": {"2027": PLAN}})

	def test_the_years_invoice_carries_the_instalments_and_the_student_sees_the_next(self):
		frappe.set_user(BURSAR)
		fee_settings.save({"instalment_plans": {"2027": PLAN}})
		invoice = frappe.get_doc("Sales Invoice", self._approve())
		schedule = [(str(r.due_date), flt(r.payment_amount)) for r in invoice.payment_schedule]
		self.assertEqual(len(schedule), 3)
		self.assertEqual(sum(a for _, a in schedule), flt(invoice.rounded_total or invoice.grand_total))
		self.assertEqual(schedule[0][1], flt(invoice.grand_total * 0.4, 2))
		self.assertEqual(str(invoice.due_date), "2027-08-16")

		state = instalments.due(invoice.student)
		self.assertEqual(state["overdue"], 0)  # nothing due before February 2027
		frappe.set_user(NDAPEWA)
		fees = student_api.overview()["fees"]
		self.assertEqual(fees["next_due"], "2027-02-15")
		self.assertEqual(fees["next_amount"], schedule[0][1])

	def test_without_a_plan_the_year_is_due_at_once(self):
		if frappe.db.exists("Instalment Plan", "2027"):
			frappe.delete_doc("Instalment Plan", "2027", ignore_permissions=True)
		invoice = frappe.get_doc("Sales Invoice", self._approve())
		self.assertEqual(len(invoice.payment_schedule), 1)
