import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.tests import IntegrationTestCase

from educore.finance.student_fees import CENTRAL_BANK, fee_structure_for, invoice_enrollment


def _skip_without_demo(test):
	if not fee_structure_for("BCS-OSH-FT", "2026"):
		test.skipTest("run the demo university (with fees) first")


class TestFeeStructure(IntegrationTestCase):
	def setUp(self):
		_skip_without_demo(self)

	def _structure(self, offering="BCS-OSH-FT", year="2027", **extra):
		return frappe.get_doc(
			{
				"doctype": "Fee Structure",
				"educore_programme_offering": offering,
				"academic_year": year,
				"components": [{"fees_category": "Tuition Fee", "amount": 1000}],
				**extra,
			}
		)

	def test_an_offering_sets_programme_campus_cost_center_and_student_debtors(self):
		structure = self._structure().insert(ignore_permissions=True)
		self.assertEqual(structure.program, frappe.db.get_value("Programme Offering", "BCS-OSH-FT", "program"))
		self.assertEqual(structure.campus, "Oshakati Campus")
		self.assertEqual(structure.cost_center, "Oshakati Campus - EDU")
		self.assertEqual(structure.receivable_account, "Student Debtors - EDU")

	def test_one_submitted_fee_structure_per_offering_and_year(self):
		# BCS-OSH-FT already has 2027 fees in the demo data
		structure = self._structure().insert(ignore_permissions=True)
		self.assertRaises(frappe.ValidationError, structure.submit)

	def test_fees_are_per_year_not_per_term(self):
		term = frappe.db.get_value("Academic Term", {"academic_year": "2027"})
		self.assertRaises(frappe.ValidationError, self._structure(academic_term=term).insert, ignore_permissions=True)


class TestEnrolmentInvoice(IntegrationTestCase):
	def setUp(self):
		_skip_without_demo(self)
		self.enrollment = frappe.get_doc(
			"Program Enrollment", frappe.db.get_value("Program Enrollment", {"student_name": "Tangeni Iiyambo", "academic_year": "2026", "docstatus": 1})
		)

	def test_the_enrolment_is_invoiced_to_the_campus_cost_center(self):
		invoice = frappe.get_doc("Sales Invoice", invoice_enrollment(self.enrollment))
		structure = frappe.get_doc("Fee Structure", fee_structure_for("BEDP-OSH-FT", "2026"))
		self.assertEqual(invoice.docstatus, 1)
		self.assertEqual(invoice.student, self.enrollment.student)
		self.assertEqual(invoice.campus, "Oshakati Campus")
		self.assertEqual(invoice.debit_to, "Student Debtors - EDU")
		self.assertEqual(invoice.grand_total, structure.total_amount)
		self.assertEqual({item.cost_center for item in invoice.items}, {"Oshakati Campus - EDU"})
		gl_cost_centers = set(
			frappe.get_all("GL Entry", filters={"voucher_no": invoice.name, "is_cancelled": 0}, pluck="cost_center")
		)
		self.assertEqual(gl_cost_centers, {"Oshakati Campus - EDU"})

	def test_an_enrolment_is_invoiced_once(self):
		self.assertEqual(invoice_enrollment(self.enrollment), invoice_enrollment(self.enrollment))

	def test_a_payment_goes_to_the_central_bank_under_the_campus(self):
		invoice = invoice_enrollment(self.enrollment)
		payment = get_payment_entry("Sales Invoice", invoice, bank_account=f"{CENTRAL_BANK} - EDU")
		payment.cost_center = None
		payment.reference_no, payment.reference_date = "TEST-EFT", "2026-03-01"
		payment.insert(ignore_permissions=True)
		self.assertEqual(payment.paid_to, f"{CENTRAL_BANK} - EDU")
		self.assertEqual(payment.campus, "Oshakati Campus")
		self.assertEqual(payment.cost_center, "Oshakati Campus - EDU")


class TestFeeAccess(IntegrationTestCase):
	def setUp(self):
		_skip_without_demo(self)
		if not frappe.db.exists("User", "student-fees-officer.osh@educore.localhost"):
			self.skipTest("run educore.access.test_users.create first")

	def _visible(self, login, group="Student"):
		frappe.set_user(f"{login}@educore.localhost")
		try:
			return set(frappe.get_list("Sales Invoice", filters={"docstatus": 1, "customer_group": group}, pluck="customer"))
		finally:
			frappe.set_user("Administrator")

	def test_students_see_only_their_own_invoices(self):
		self.assertEqual(self._visible("student1.whk"), {"Ndapewa Amukoto"})

	def test_fees_staff_see_their_campus_and_the_bursar_all(self):
		self.assertEqual(self._visible("student-fees-officer.osh"), {"Martha Shilongo", "Tangeni Iiyambo"})
		self.assertEqual(len(self._visible("bursar")), 6)
		# a sponsor's invoice for a student is on that student's campus (educore.finance.sponsors)
		if frappe.db.exists("Sponsor", {"sponsor_name": "Namibia Students Financial Assistance Fund"}):
			self.assertIn("Namibia Students Financial Assistance Fund", self._visible("student-fees-officer.osh", "Sponsor"))
			self.assertNotIn("Namibia Students Financial Assistance Fund", self._visible("student-fees-officer.whk", "Sponsor"))
