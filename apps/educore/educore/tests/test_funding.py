"""Funding routes on the application: the documents asked, the application fee (none for NSFAF and NTA), the fee by
nationality, and the students who named a sponsor (educore.admissions.funding)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.access.demo_users import new_user
from educore.admissions import application, fees, funding
from educore.api.v1 import admission_setup, apply, fee_settings
from educore.api.v1 import sponsors as sponsors_api
from educore.tests.test_apply import GOOD_RESULTS, PASSWORD, PERSONAL

REGISTRAR = "registrar@educore.localhost"
BURSAR = "bursar@educore.localhost"


class TestFundingRoutes(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Admission", "2027 Intake") or not frappe.db.exists("Funding Route", "NSFAF"):
			self.skipTest("run the demo setup first")
		self._mute, frappe.flags.mute_emails = frappe.flags.mute_emails, True
		frappe.db.savepoint("funding_test")

	def tearDown(self):
		frappe.flags.mute_emails = self._mute
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="funding_test")
		frappe.clear_cache(doctype="Funding Route")

	def _draft(self, international=False, **personal):
		email = f"funding.{self._testMethodName[5:40].replace('_', '.').strip('.')}@example.com"
		if not frappe.db.exists("User", email):
			frappe.flags.in_import = True
			try:
				new_user(email=email, first_name="Test", last_name="Funding", password=PASSWORD, positions=["Applicant"])
			finally:
				frappe.flags.in_import = False
		frappe.set_user(email)
		apply.save(
			{
				"intake": "2027 Intake",
				"international": international,
				"personal": {**PERSONAL, **personal},
				"school": {"name": frappe.db.get_value("Secondary School", {"centre_number": "DEMO-201"})},
				"results": GOOD_RESULTS,
				"choices": ["BCS-OSH-FT"],
			}
		)
		name = apply.my_application()["name"]
		frappe.set_user("Administrator")
		return frappe.get_doc("Student Applicant", name)

	def test_nsfaf_applicants_pay_no_application_fee_and_changing_route_makes_it_due(self):
		doc = self._draft(educore_fee_payer="NSFAF")
		self.assertEqual((doc.educore_fee_status, doc.educore_fee_amount), (fees.NOT_REQUIRED, 0))
		self.assertTrue(fees.settled(doc))
		self.assertIn("NSFAF", doc.educore_fee_note)
		doc.educore_fee_payer = "Self"
		doc.save(ignore_permissions=True)
		self.assertEqual(doc.educore_fee_status, "Unpaid")
		self.assertEqual(doc.educore_fee_amount, frappe.db.get_single_value("Admission Settings", "fee_namibian"))

	def test_a_route_asks_its_documents_and_who_pays(self):
		doc = self._draft(educore_fee_payer="Employer", educore_fee_payer_name="")
		self.assertIn("Employer sponsorship letter", application.required_documents(doc))
		self.assertIn("Document: Employer sponsorship letter", application.missing(doc))
		self.assertIn("NSFAF award or application letter", application.document_plan(self._draft(educore_fee_payer="NSFAF")))

	def test_regional_applicants_pay_the_regional_fee_else_the_international_one(self):
		frappe.db.set_single_value("Admission Settings", "fee_regional", 0)
		doc = self._draft(international=True, nationality="Zambia", educore_passport_number="ZN1234567")
		settings = frappe.get_single("Admission Settings")
		self.assertEqual(funding.region(doc), "regional")
		self.assertEqual(fees.fee_for(doc), settings.fee_international)
		frappe.db.set_single_value("Admission Settings", "fee_regional", 220)
		frappe.clear_document_cache("Admission Settings", "Admission Settings")
		self.assertEqual(fees.fee_for(doc), 220)

	def test_the_registrar_sets_routes_and_the_bursar_the_fee(self):
		frappe.set_user(REGISTRAR)
		page = admission_setup.save_funding_route({"route_name": "Regional council bursary", "kind": "Bursary or scholarship", "ask_who": 1})
		self.assertIn("Regional council bursary", [r["name"] for r in page["funding_routes"]])
		frappe.set_user(BURSAR)
		fee_settings.save({"fee_free_routes": ["NSFAF", "NTA", "Regional council bursary"]})
		self.assertFalse(frappe.db.get_value("Funding Route", "Regional council bursary", "pays_application_fee"))
		frappe.set_user(REGISTRAR)
		self.assertRaises(frappe.PermissionError, fee_settings.save, {"fee_free_routes": []})

	def test_finance_sees_students_who_named_the_sponsor(self):
		sponsor = frappe.db.get_value("Funding Route", "NSFAF", "sponsor")
		if not sponsor:
			self.skipTest("the demo sponsors are not set up")
		ndapewa = frappe.db.get_value("Student", {"user": "student1.whk@educore.localhost"})
		frappe.set_user("financial-aid-officer@educore.localhost")
		page = sponsors_api.sponsor(sponsor, "2026")
		named = {n["student"] for n in page["named"]}
		self.assertIn(ndapewa, named)  # chose NSFAF, no sponsorship recorded
		self.assertNotIn(frappe.db.get_value("Student", {"user": "student1.osh@educore.localhost"}), named)  # recorded
