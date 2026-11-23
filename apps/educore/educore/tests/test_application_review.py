import io
from unittest.mock import patch

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate
from werkzeug.datastructures import FileStorage

from educore.access.demo_users import new_user
from educore.admissions import fees
from educore.api.v1 import admissions, apply
from educore.tests.test_apply import GOOD_RESULTS, PERSONAL, _pdf

DOCUMENTS = ("National ID or Passport", "Birth Certificate", "NSSC Statement of Results or Certificate")


class TestApplicationReview(IntegrationTestCase):
	"""Phase 2: the fee (matched from the bank statement, or waived) and document verification"""

	def setUp(self):
		if not frappe.db.get_single_value("Admission Settings", "fee_bank_account"):
			self.skipTest("run educore.setup.demo.create_demo_university first")
		self._mute, frappe.flags.mute_emails = frappe.flags.mute_emails, True

	def tearDown(self):
		frappe.flags.mute_emails = self._mute
		frappe.set_user("Administrator")

	def _submitted(self) -> str:
		"""A complete online application for Oshakati, submitted by its own applicant"""
		email = f"review.{self._testMethodName.removeprefix('test_')[:30].replace('_', '.').strip('.')}@example.com"
		if not frappe.db.exists("User", email):
			frappe.flags.in_import = True
			try:
				new_user(email=email, first_name="Test", last_name="Review", password="Campus-Demo-2026", positions=["Applicant"])
			finally:
				frappe.flags.in_import = False
		frappe.set_user(email)
		apply.save(
			{
				"intake": "2027 Intake",
				"personal": PERSONAL,
				"school": {"name": frappe.db.get_value("Secondary School", {"centre_number": "DEMO-201"})},
				"results": GOOD_RESULTS,
				"choices": ["DIT-OSH-FT"],
			}
		)
		for document in DOCUMENTS:
			self._upload(document)
		name = apply.submit(declaration=True)["name"]
		frappe.set_user("Administrator")
		return name

	def _upload(self, document):
		upload = FileStorage(stream=io.BytesIO(_pdf()), filename="scan.pdf")
		with patch.object(frappe, "request", frappe._dict(files={"file": upload}), create=True):
			return apply.upload_document(document, add_days(nowdate(), -5))

	def _deposit(self, amount, text):
		txn = frappe.get_doc(
			{
				"doctype": "Bank Transaction",
				"date": nowdate(),
				"bank_account": frappe.db.get_single_value("Admission Settings", "fee_bank_account"),
				"company": "EduCore Demo University",
				"deposit": amount,
				"currency": "NAD",
				"description": text,
			}
		).insert(ignore_permissions=True)
		txn.submit()
		return txn.name

	def _as(self, login):
		frappe.set_user(f"{login}@educore.localhost")

	# --- the fee ---------------------------------------------------------------------------------------

	def test_the_fee_follows_the_applicant(self):
		name = self._submitted()
		self.assertEqual(frappe.db.get_value("Student Applicant", name, ["educore_fee_amount", "educore_fee_status"]), (150, "Unpaid"))

	def test_a_deposit_with_the_application_number_pays_the_fee(self):
		name = self._submitted()
		self.assertEqual(fees.match_bank_transactions(), 0)
		txn = self._deposit(150, f"application fee {name.lower()}")
		self.assertGreaterEqual(fees.match_bank_transactions(), 1)
		paid = frappe.db.get_value(
			"Student Applicant", name, ["educore_fee_status", "educore_fee_bank_transaction", "educore_fee_voucher"], as_dict=True
		)
		self.assertEqual((paid.educore_fee_status, paid.educore_fee_bank_transaction), ("Paid", txn))
		self.assertEqual(frappe.db.get_value("Bank Transaction", txn, "status"), "Reconciled")
		income = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": paid.educore_fee_voucher, "account": ("like", "Application Fees%"), "is_cancelled": 0},
			fields=["credit", "cost_center"],
		)
		self.assertEqual([(i.credit, i.cost_center) for i in income], [(150, "Oshakati Campus - EDU")])

	def test_a_short_payment_is_left_for_finance(self):
		name = self._submitted()
		txn = self._deposit(100, name)
		fees.match_bank_transactions()
		self.assertEqual(frappe.db.get_value("Student Applicant", name, "educore_fee_status"), "Unpaid")
		self.assertIn(txn, frappe.db.get_value("Student Applicant", name, "educore_fee_note"))

	def test_only_finance_waives_the_fee_with_a_reason(self):
		name = self._submitted()
		self._as("admissions-officer.osh")
		self.assertRaises(frappe.PermissionError, admissions.waive_fee, name, "Marginalised communities scheme")
		self._as("finance-officer")
		self.assertRaises(frappe.ValidationError, admissions.waive_fee, name, "")
		data = admissions.waive_fee(name, "Marginalised communities scheme")
		self.assertEqual(data["status"], "Waived")
		self.assertIn("Marginalised communities scheme", data["note"])

	# --- documents -------------------------------------------------------------------------------------

	def test_documents_are_checked_one_by_one_and_a_rejection_needs_a_reason(self):
		name = self._submitted()
		self._as("admissions-officer.osh")
		data = admissions.review(name)
		self.assertEqual(data["documents_verified"], 0)
		self.assertTrue(data["can_review"])
		data = admissions.verify_document(name, "National ID or Passport", "Verified")
		self.assertEqual(data["documents_verified"], 1)
		self.assertRaises(frappe.ValidationError, admissions.verify_document, name, "Birth Certificate", "Rejected")
		data = admissions.verify_document(name, "Birth Certificate", "Rejected", reason="The stamp is unreadable")
		row = next(d for d in data["documents"] if d["document_type"] == "Birth Certificate")
		self.assertEqual((row["status"], row["rejection_reason"]), ("Rejected", "The stamp is unreadable"))

	def test_the_applicant_replaces_only_a_rejected_document(self):
		name = self._submitted()
		self._as("admissions-officer.osh")
		admissions.verify_document(name, "Birth Certificate", "Rejected", reason="The stamp is unreadable")
		applicant = frappe.db.get_value("Student Applicant", name, "educore_applicant_user")
		frappe.set_user(applicant)
		self.assertRaises(frappe.ValidationError, self._upload, "National ID or Passport")
		data = self._upload("Birth Certificate")
		row = next(d for d in data["documents"] if d["document_type"] == "Birth Certificate")
		self.assertEqual((row["status"], row["rejection_reason"]), ("Pending", None))

	def test_staff_of_another_campus_and_other_staff_cannot_review(self):
		name = self._submitted()
		self._as("admissions-officer.whk")
		self.assertRaises(frappe.PermissionError, admissions.review, name)
		self._as("registry-officer.osh")
		self.assertFalse(admissions.review(name)["can_review"])
		self.assertRaises(frappe.PermissionError, admissions.verify_document, name, "Birth Certificate", "Verified")

	# --- deciding --------------------------------------------------------------------------------------

	def test_approval_waits_for_verified_documents_and_a_settled_fee(self):
		name = self._submitted()
		self._as("admissions-officer.osh")
		self.assertRaises(frappe.ValidationError, admissions.decide, name, "Approve")
		for document in DOCUMENTS:
			admissions.verify_document(name, document, "Verified")
		data = admissions.review(name)
		self.assertEqual(data["blockers"], ["Application fee outstanding"])
		self.assertRaises(frappe.ValidationError, admissions.decide, name, "Approve")
		# Finance waives it; admissions then decides
		self._as("finance-officer")
		admissions.waive_fee(name, "Staff dependant")
		self._as("admissions-officer.osh")
		self.assertTrue(admissions.review(name)["ready"])
		self.assertEqual(admissions.decide(name, "Approve")["status"], "Approved")

	def test_paper_applications_are_not_held_back(self):
		frappe.set_user("Administrator")
		paper = frappe.get_doc(
			{
				"doctype": "Student Applicant",
				"first_name": "Test",
				"last_name": "Paper",
				"educore_programme_offering": "DIT-OSH-FT",
				"academic_year": "2027",
			}
		).insert(ignore_permissions=True)
		apply_workflow(paper, "Submit")
		self._as("admissions-officer.osh")
		self.assertEqual(admissions.review(paper.name)["blockers"], [])
