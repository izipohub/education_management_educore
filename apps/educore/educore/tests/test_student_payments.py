"""Student fees matched from the bank statement by student number (educore.finance.student_payments)"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from educore.api.v1 import student_payments as api
from educore.finance import student_payments
from educore.registration import rules


def _deposit(amount: float, description: str) -> str:
	line = frappe.get_doc(
		{
			"doctype": "Bank Transaction",
			"date": add_days(nowdate(), -1),
			"bank_account": frappe.db.get_single_value("Admission Settings", "fee_bank_account"),
			"company": frappe.db.get_value("Campus", {"is_main_campus": 1}, "company"),
			"deposit": amount,
			"currency": "NAD",
			"description": description,
		}
	).insert(ignore_permissions=True)
	line.submit()
	return line.name


class TestStudentPayments(IntegrationTestCase):
	def setUp(self):
		self.student = frappe.db.get_value("Student", {"student_name": "Tangeni Iiyambo"}, "name")
		if not self.student or not frappe.db.get_single_value("Admission Settings", "fee_bank_account"):
			self.skipTest("run the demo setup first")
		frappe.set_user("Administrator")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_a_deposit_with_the_student_number_pays_the_oldest_invoice_and_is_reconciled(self):
		owed = rules.outstanding(self.student)
		line = _deposit(5000, f"FNB EFT FEES {self.student.lower()} T IIYAMBO")
		self.assertEqual(student_payments.match_bank_transactions(), 1)
		self.assertEqual(rules.outstanding(self.student), owed - 5000)
		self.assertEqual(frappe.db.get_value("Bank Transaction", line, "status"), "Reconciled")

	def test_paying_more_than_is_owed_leaves_an_advance_towards_the_deposit(self):
		owed = rules.outstanding(self.student)
		_deposit(owed + 2000, f"DEPOSIT {self.student}")
		student_payments.match_bank_transactions()
		self.assertEqual(rules.outstanding(self.student), 0)
		self.assertEqual(rules.paid_in_advance(self.student), 2000)

	def test_a_deposit_without_a_number_waits_for_finance_to_assign_it(self):
		line = _deposit(1500, "CASH DEP OSHAKATI T IIYAMBO")
		student_payments.match_bank_transactions()
		frappe.set_user("student-fees-officer@educore.localhost")
		self.assertIn(line, [r["name"] for r in api.payments("waiting")["rows"]])
		api.assign(line, self.student)
		self.assertNotIn(line, [r["name"] for r in api.payments("waiting")["rows"]])
		self.assertRaises(frappe.ValidationError, api.assign, line, self.student)

	def test_a_line_naming_two_students_is_left_for_finance(self):
		other = frappe.db.get_value("Student", {"student_name": "Martha Shilongo"}, "name")
		line = _deposit(3000, f"FEES {self.student} AND {other}")
		student_payments.match_bank_transactions()
		self.assertEqual(frappe.db.get_value("Bank Transaction", line, "unallocated_amount"), 3000)

	def test_only_finance(self):
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.payments)
		self.assertRaises(frappe.PermissionError, api.match_now)
