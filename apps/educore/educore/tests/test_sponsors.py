"""Sponsors paying students' fees (educore.finance.sponsors, educore.api.v1.sponsors)"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from educore.api.v1 import sponsors as api
from educore.api.v1 import student_records
from educore.finance import sponsors, student_payments
from educore.registration import rules
from educore.tests.test_student_payments import _deposit

FINANCIAL_AID = "financial-aid-officer@educore.localhost"
NDAPEWA = "student1.whk@educore.localhost"  # Windhoek, registered for 2026, not yet for 2027


class TestSponsors(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"user": NDAPEWA}, "name")
		if not self.student or not frappe.db.exists("User", FINANCIAL_AID):
			self.skipTest("run the demo setup first")
		self.invoice = sponsors.year_invoice(self.student, "2026")
		frappe.db.savepoint("sponsors_test")
		frappe.set_user(FINANCIAL_AID)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="sponsors_test")

	def _sponsor(self, name="Test Students Fund", kind="Government fund"):
		return api.save_sponsor({"sponsor_name": name, "sponsor_type": kind, "payment_days": 60})["name"]

	def _fees(self):
		return flt(frappe.db.get_value("Sales Invoice", self.invoice, "grand_total"))

	def _owing(self):
		return flt(frappe.db.get_value("Sales Invoice", self.invoice, "outstanding_amount"))

	def test_a_full_sponsorship_moves_the_year_onto_the_sponsor(self):
		owing = self._owing()
		advance = rules.paid_in_advance(self.student)
		sponsor = self._sponsor()
		page = api.add_student(sponsor, self.student, "2026", sponsors.FULL, sponsor_reference="NSFAF-2026-0412")
		row = page["students"][0]
		self.assertEqual(row["status"], sponsors.INVOICED)
		self.assertEqual(row["amount"], self._fees())
		# what the student had paid towards the year is now a credit, towards next year's deposit
		credit = frappe.db.get_value("Sponsorship", row["name"], "credit_note")
		left = flt(frappe.db.get_value("Sales Invoice", credit, "outstanding_amount")) + self._owing()
		self.assertEqual(left, flt(owing - self._fees(), 2))
		if owing == 0:
			self.assertEqual(rules.paid_in_advance(self.student), flt(advance + self._fees(), 2))

		bill = frappe.get_doc("Sales Invoice", row["sponsor_invoice"])
		self.assertEqual(bill.customer, frappe.db.get_value("Sponsor", sponsor, "customer"))
		self.assertTrue(bill.debit_to.startswith(sponsors.SPONSOR_DEBTORS))
		self.assertFalse(bill.get("student"))  # not on the student's own statement
		self.assertEqual(bill.educore_sponsored_student, self.student)
		self.assertEqual(bill.cost_center, frappe.db.get_value("Sales Invoice", self.invoice, "cost_center"))

		frappe.set_user("Administrator")
		record = student_records.student(self.student)
		self.assertEqual(record["sponsors"][0]["cover"], "Full fees")

	def test_sponsors_together_never_pay_more_than_the_fees(self):
		fund, employer = self._sponsor(), self._sponsor("Test Employer Holdings", "Employer")
		api.add_student(fund, self.student, "2026", sponsors.PERCENT, 60)
		page = api.add_student(employer, self.student, "2026", sponsors.FULL)
		self.assertEqual(page["students"][0]["amount"], flt(self._fees() * 0.4, 2))
		self.assertRaises(frappe.ValidationError, api.add_student, fund, self.student, "2026", sponsors.AMOUNT, 100)

	def test_a_sponsorship_before_registration_lowers_the_deposit_and_applies_on_approval(self):
		offering = frappe.db.get_value("Program Enrollment", {"student": self.student, "academic_year": "2026"}, "educore_programme_offering")
		deposit = rules.deposit_required(offering, "2027", self.student)
		self.assertGreater(deposit, 0)
		sponsor = self._sponsor()
		page = api.add_student(sponsor, self.student, "2027", sponsors.PERCENT, 50)
		self.assertEqual(page["students"][0]["status"], sponsors.RECORDED)  # nothing to invoice yet
		self.assertEqual(rules.deposit_required(offering, "2027", self.student), flt(deposit / 2, 2))
		api.add_student(self._sponsor("Test Health Bursary", "Bursary"), self.student, "2027", sponsors.FULL)
		self.assertEqual(rules.deposit_required(offering, "2027", self.student), 0)

	def test_a_sponsor_payment_is_matched_by_its_number_not_the_students(self):
		sponsor = self._sponsor()
		bill = api.add_student(sponsor, self.student, "2026", sponsors.FULL)["students"][0]["sponsor_invoice"]
		owing = self._owing()
		frappe.set_user("Administrator")
		_deposit(5000, f"NSFAF PAYMENT {sponsor} STUDENTS {self.student}")
		self.assertEqual(student_payments.match_bank_transactions(), 0)
		self.assertEqual(sponsors.match_bank_transactions(), 1)
		total = flt(frappe.db.get_value("Sales Invoice", bill, "grand_total"))
		self.assertEqual(flt(frappe.db.get_value("Sales Invoice", bill, "outstanding_amount")), flt(total - 5000, 2))
		self.assertEqual(self._owing(), owing)  # the student's account is untouched

		# paid towards: it can no longer be withdrawn
		name = frappe.db.get_value("Sponsorship", {"sponsor_invoice": bill})
		frappe.set_user(FINANCIAL_AID)
		self.assertRaises(frappe.ValidationError, api.withdraw, name)

	def test_withdrawing_gives_the_fees_back_to_the_student(self):
		owing = self._owing()
		sponsor = self._sponsor()
		row = api.add_student(sponsor, self.student, "2026", sponsors.PERCENT, 25)["students"][0]
		page = api.withdraw(row["name"])
		self.assertEqual(page["students"][0]["status"], sponsors.WITHDRAWN)
		self.assertEqual(self._owing(), owing)
		self.assertEqual(frappe.db.get_value("Sales Invoice", row["sponsor_invoice"], "docstatus"), 2)

	def test_sponsors_are_finance_and_financial_aid_only(self):
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.sponsors)
		frappe.set_user("cashier@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.save_sponsor, {"sponsor_name": "X", "sponsor_type": "Other"})
