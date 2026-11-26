"""Official transcripts (educore.academics.transcripts, educore.api.v1.transcripts): the student asks, the fee is
invoiced, the Registry issues once it is paid and the student is cleared"""

import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from frappe.tests import IntegrationTestCase
from frappe.utils import flt

from educore.academics import transcripts
from educore.api.v1 import transcripts as api
from educore.finance.student_fees import CENTRAL_BANK

NDAPEWA = "student1.whk@educore.localhost"  # paid up and cleared
LUKAS = "student2.whk@educore.localhost"  # owes fees: not cleared
REGISTRY_WHK = "registry-officer.whk@educore.localhost"
REGISTRY_OSH = "registry-officer.osh@educore.localhost"


def _set(**values):
	for field, value in values.items():
		frappe.db.set_single_value("Registration Settings", field, value)
	frappe.clear_document_cache("Registration Settings", "Registration Settings")


class TestTranscripts(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", NDAPEWA) or not frappe.db.exists("User", REGISTRY_WHK):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("transcripts_test")
		frappe.set_user("Administrator")
		_set(transcript_fee=150, transcript_needs_clearance=1)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="transcripts_test")
		frappe.clear_document_cache("Registration Settings", "Registration Settings")

	def _pending(self, user: str) -> dict:
		frappe.set_user(user)
		return next(r for r in api.mine()["requests"] if r["status"] == transcripts.REQUESTED)

	def test_the_fee_is_invoiced_and_the_registry_issues_once_paid(self):
		frappe.set_user(NDAPEWA)
		api.request(2, transcripts.COLLECT)
		row = self._pending(NDAPEWA)
		self.assertEqual(row["fee"], 300)
		self.assertFalse(row["paid"])
		invoice = frappe.get_doc("Sales Invoice", row["fee_invoice"])
		self.assertEqual((invoice.items[0].item_code, flt(invoice.items[0].qty)), ("Transcript Fee", 2))

		frappe.set_user(REGISTRY_WHK)
		queued = next(r for r in api.queue()["rows"] if r["name"] == row["name"])
		self.assertEqual(queued["blockers"], ["Transcript fee not paid"])
		self.assertRaises(frappe.ValidationError, api.issue, row["name"])

		frappe.set_user("Administrator")
		payment = get_payment_entry("Sales Invoice", invoice.name, bank_account=f"{CENTRAL_BANK} - EDU")
		payment.reference_no, payment.reference_date = "TEST-TRANSCRIPT", frappe.utils.nowdate()
		payment.insert(ignore_permissions=True)
		payment.submit()

		frappe.set_user(REGISTRY_WHK)
		page = api.issue(row["name"])
		self.assertNotIn(row["name"], {r["name"] for r in page["rows"]})
		self.assertEqual(frappe.db.get_value("Transcript Request", row["name"], "status"), transcripts.ISSUED)

	def test_not_issued_to_a_student_not_cleared_unless_the_university_allows_it(self):
		_set(transcript_fee=0)
		frappe.set_user(LUKAS)
		api.request(1, transcripts.COLLECT)
		row = self._pending(LUKAS)
		self.assertFalse(row["fee_invoice"])
		frappe.set_user(REGISTRY_WHK)
		queued = next(r for r in api.queue()["rows"] if r["name"] == row["name"])
		self.assertTrue(queued["blockers"][0].startswith("Fees owing"))
		self.assertRaises(frappe.ValidationError, api.issue, row["name"])
		frappe.set_user("Administrator")
		_set(transcript_needs_clearance=0)
		frappe.set_user(REGISTRY_WHK)
		api.issue(row["name"])

	def test_declined_with_the_reason_and_the_unpaid_fee_cancelled(self):
		frappe.set_user(NDAPEWA)
		api.request(1, transcripts.POST, recipient="Admissions, Another University", postal_address="PO Box 1\nWindhoek")
		row = self._pending(NDAPEWA)
		frappe.set_user(REGISTRY_WHK)
		self.assertRaises(frappe.ValidationError, api.decline, row["name"], " ")
		api.decline(row["name"], "Asked twice by mistake")
		self.assertEqual(frappe.db.get_value("Sales Invoice", row["fee_invoice"], "docstatus"), 2)
		frappe.set_user(NDAPEWA)
		self.assertEqual(api.mine()["requests"][0]["review_note"], "Asked twice by mistake")

	def test_what_the_student_must_say(self):
		frappe.set_user(NDAPEWA)
		self.assertRaises(frappe.ValidationError, api.request, 1, transcripts.EMAIL, "Demo Mining Ltd", "not-an-email")
		self.assertRaises(frappe.ValidationError, api.request, 1, transcripts.EMAIL, None, "hr@example.com")
		self.assertRaises(frappe.ValidationError, api.request, 1, transcripts.POST, "Demo Mining Ltd")
		self.assertRaises(frappe.ValidationError, api.request, 0, transcripts.COLLECT)
		self.assertRaises(frappe.ValidationError, api.request, 11, transcripts.COLLECT)
		api.request(3, transcripts.EMAIL, "Demo Mining Ltd", "hr@example.com")
		self.assertEqual(self._pending(NDAPEWA)["copies"], 1)  # one emailed copy
		self.assertRaises(frappe.ValidationError, api.request, 1, transcripts.EMAIL, "Demo Mining Ltd", "hr@example.com")

	def test_the_registry_of_the_students_campus_only(self):
		frappe.set_user(NDAPEWA)
		api.request(1, transcripts.COLLECT)
		row = self._pending(NDAPEWA)
		self.assertRaises(frappe.PermissionError, api.queue)
		frappe.set_user(REGISTRY_OSH)
		self.assertNotIn(row["name"], {r["name"] for r in api.queue()["rows"]})
		self.assertRaises(frappe.PermissionError, api.issue, row["name"])
		frappe.set_user("bursar@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.queue)
