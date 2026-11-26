"""Fee waivers (educore.finance.waivers, educore.api.v1.waivers): requested by Finance, decided by the Bursar, a
credit note against the year's invoice"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from educore.api.v1 import registration as registration_api
from educore.api.v1 import waivers as api
from educore.finance import clearance, waivers
from educore.registration import rules

FEES_KMP = "student-fees-officer.kmp@educore.localhost"
FEES_OSH = "student-fees-officer.osh@educore.localhost"
FST_WHK = "faculty-officer.fst.whk@educore.localhost"
BURSAR = "bursar@educore.localhost"
STUDENT_KMP = "student1.kmp@educore.localhost"  # half of the 2026 fees paid
MARTHA = "student1.osh@educore.localhost"  # NSFAF pays her 2026 fees in full
NDAPEWA = "student1.whk@educore.localhost"  # free to register for 2027


def _year_lines(invoice: str) -> float:
	return flt(
		frappe.db.sql(
			"select sum(amount) from `tabSales Invoice Item` where parent = %s and item_code != 'Late Registration Fee'", invoice
		)[0][0],
		2,
	)


class TestWaivers(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"user": STUDENT_KMP}, "name")
		if not self.student or not frappe.db.exists("User", FEES_KMP):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("waivers_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="waivers_test")

	def test_requested_then_approved_by_the_bursar_takes_it_off_the_invoice(self):
		from educore.finance.sponsors import year_invoice

		invoice = year_invoice(self.student, "2026")
		owed = clearance.owing(self.student)
		frappe.set_user(FEES_KMP)
		row = api.request(self.student, "2026", waivers.PERCENT, 25, "Bereavement in the family")
		self.assertEqual(row["status"], waivers.REQUESTED)
		self.assertFalse(row["can_decide"])
		self.assertRaises(frappe.PermissionError, api.approve, row["name"])
		self.assertEqual(clearance.owing(self.student), owed)  # nothing changes until it is approved

		frappe.set_user(BURSAR)
		self.assertTrue(next(r for r in api.waivers_list()["rows"] if r["name"] == row["name"])["can_decide"])
		row = api.approve(row["name"], "Hardship confirmed")
		self.assertEqual(row["status"], waivers.APPROVED)
		self.assertEqual(row["amount"], flt(_year_lines(invoice) * 0.25, 2))
		self.assertEqual(frappe.db.get_value("Sales Invoice", row["credit_note"], "return_against"), invoice)
		self.assertAlmostEqual(clearance.owing(self.student), flt(owed - row["amount"], 2), places=2)

		# withdrawn: the student owes it again
		row = api.withdraw(row["name"], "Granted in error")
		self.assertEqual(row["status"], waivers.WITHDRAWN)
		self.assertEqual(frappe.db.get_value("Sales Invoice", row["credit_note"], "docstatus"), 2)
		self.assertAlmostEqual(clearance.owing(self.student), owed, places=2)

	def test_the_bursar_never_approves_their_own_request_and_a_rejection_says_why(self):
		frappe.set_user(BURSAR)
		row = api.request(self.student, "2026", waivers.AMOUNT, 1000, "Staff dependant")
		self.assertFalse(row["can_decide"])
		self.assertRaises(frappe.PermissionError, api.approve, row["name"])
		frappe.set_user("Administrator")
		self.assertRaises(frappe.ValidationError, api.reject, row["name"], " ")
		row = api.reject(row["name"], "Not covered by the policy")
		self.assertEqual(row["status"], waivers.REJECTED)
		self.assertRaises(frappe.ValidationError, api.approve, row["name"])

	def test_never_more_than_is_still_charged(self):
		martha = frappe.db.get_value("Student", {"user": MARTHA}, "name")
		frappe.set_user(BURSAR)
		row = api.request(martha, "2026", waivers.PERCENT, 50, "Top achiever")
		frappe.set_user("Administrator")
		row = api.approve(row["name"])
		self.assertEqual(flt(row["amount"]), 0)  # her sponsor pays it all already
		self.assertFalse(row["credit_note"])

	def test_each_campus_its_own_and_finance_only(self):
		frappe.set_user(FEES_OSH)
		self.assertRaises(frappe.PermissionError, api.request, self.student, "2026", waivers.PERCENT, 10, "Not ours")
		self.assertNotIn(self.student, {r["student"] for r in api.waivers_list()["rows"]})
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.waivers_list)
		frappe.set_user(FEES_KMP)
		self.assertRaises(frappe.ValidationError, api.request, self.student, "2026", waivers.PERCENT, 120, "Too much")
		self.assertRaises(frappe.ValidationError, api.request, self.student, "1999", waivers.PERCENT, 10, "Not a year of theirs")

	def test_approved_before_the_year_is_invoiced_lowers_the_deposit_and_applies_on_approval(self):
		ndapewa = frappe.db.get_value("Student", {"user": NDAPEWA}, "name")
		if not frappe.db.exists("Registration Period", "2027"):
			self.skipTest("run the demo setup first")
		offering = frappe.db.get_value("Program Enrollment", {"student": ndapewa, "docstatus": 1}, "educore_programme_offering")
		before = rules.deposit_required(offering, "2027", ndapewa)
		frappe.set_user(BURSAR)
		row = api.request(ndapewa, "2027", waivers.PERCENT, 50, "Merit award")
		frappe.set_user("Administrator")
		row = api.approve(row["name"])
		self.assertFalse(row["credit_note"])  # not invoiced yet
		if before:
			self.assertLess(rules.deposit_required(offering, "2027", ndapewa), before)

		frappe.set_user(NDAPEWA)
		state = registration_api.status()
		registration_api.save([c["course"] for c in state["courses"] if c["year"] == state["year_of_study"] and c["state"] == "open"])
		registration_api.submit()
		frappe.set_user(FST_WHK)
		queued = next(r for r in registration_api.queue()["rows"] if r["student_name"] == "Ndapewa Amukoto")
		registration_api.approve(queued["name"])
		frappe.set_user("Administrator")
		waiver = frappe.get_doc("Fee Waiver", row["name"])
		self.assertTrue(waiver.credit_note)
		invoice = frappe.db.get_value("Sales Invoice", waiver.credit_note, "return_against")
		self.assertEqual(flt(waiver.amount), flt(_year_lines(invoice) * 0.5, 2))
