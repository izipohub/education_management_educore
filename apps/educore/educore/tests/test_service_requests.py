"""Service requests (educore.academics.service_requests, educore.api.v1.service_requests): the student asks and
follows; the office that handles the category answers, within its campus; fees; documents; the Registrar's categories"""

import base64

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

from educore.academics import service_requests as sr
from educore.api.v1 import service_requests as api

STUDENT = "student1.kmp@educore.localhost"
REGISTRY_KMP = "registry-officer.kmp@educore.localhost"
REGISTRY_OSH = "registry-officer.osh@educore.localhost"
EXAMS_KMP = "examinations-officer.kmp@educore.localhost"
#: a 1x1 PNG
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==")


class TestServiceRequests(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", STUDENT) or not frappe.db.exists("Service Request Category", "Letter of enrolment"):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("service_requests_test")
		self.student = frappe.db.get_value("Student", {"user": STUDENT})

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="service_requests_test")

	def _ask(self, category="Letter of enrolment", details="For the Namibian embassy, stating my year of study") -> dict:
		frappe.set_user(STUDENT)
		for name in frappe.get_all("Service Request", filters={"student": self.student, "category": category, "status": ("in", sr.OPEN)}, pluck="name"):
			frappe.db.set_value("Service Request", name, "status", sr.WITHDRAWN)
		return api.ask(category, details)

	def test_working_days_skip_the_weekend(self):
		self.assertEqual(sr.due_on("2026-11-27", 2), getdate("2026-12-01"))  # Friday + 2 working days: Tuesday
		self.assertEqual(sr.due_on("2026-11-23", 0), getdate("2026-11-23"))

	def test_the_office_takes_writes_and_resolves_and_the_student_follows(self):
		mine = self._ask()
		self.assertEqual((mine["status"], mine["office"]), (sr.SUBMITTED, "Registry"))
		self.assertEqual(getdate(mine["due_on"]), sr.due_on(mine["submitted_on"][:10], 2))
		# one open request per category: the student writes on it instead
		self.assertRaises(frappe.ValidationError, api.ask, "Letter of enrolment", "Again")

		# the campus's Registry sees it; another campus's Registry and the examinations office do not
		frappe.set_user(REGISTRY_OSH)
		self.assertNotIn(mine["name"], [r["name"] for r in api.queue()["rows"]])
		self.assertRaises(frappe.PermissionError, api.request, mine["name"])
		frappe.set_user(EXAMS_KMP)
		self.assertNotIn(mine["name"], [r["name"] for r in api.queue()["rows"]])
		frappe.set_user(REGISTRY_KMP)
		self.assertIn(mine["name"], [r["name"] for r in api.queue()["rows"]])
		page = api.write(mine["name"], "Which year of study must it state?")
		self.assertEqual(page["status"], sr.IN_PROGRESS)  # writing takes it
		self.assertEqual(page["messages"][0]["by"], frappe.utils.get_fullname(REGISTRY_KMP))  # staff see who wrote

		# the student sees the office, not the officer, and replies
		frappe.set_user(STUDENT)
		mine = next(r for r in api.mine()["requests"] if r["name"] == mine["name"])
		self.assertEqual(mine["messages"][0]["by"], "Registry")
		self.assertRaises(frappe.ValidationError, api.withdraw, mine["name"])  # taken already
		api.write_mine(mine["name"], "My second year, 2026")

		frappe.set_user(REGISTRY_KMP)
		page = api.resolve(mine["name"], "The letter is ready for collection at the Registry")
		self.assertEqual(page["status"], sr.RESOLVED)
		self.assertRaises(frappe.ValidationError, api.write, mine["name"], "More")  # closed

	def test_a_fee_is_invoiced_and_must_be_paid_before_resolving_and_a_decline_cancels_it(self):
		frappe.set_user("Administrator")
		frappe.db.set_value("Service Request Category", "ID card replacement", "fee", 150)
		mine = self._ask("ID card replacement", "Lost on the bus")
		invoice = frappe.db.get_value("Service Request", mine["name"], "fee_invoice")
		self.assertTrue(invoice)
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice, "grand_total"), 150)
		self.assertTrue(mine["fee_unpaid"])
		frappe.set_user("student-affairs-officer.kmp@educore.localhost")
		self.assertRaises(frappe.ValidationError, api.resolve, mine["name"], "")  # not paid
		self.assertRaises(frappe.ValidationError, api.decline, mine["name"], " ")  # the reason first
		api.decline(mine["name"], "Report the loss to the police first, then ask again with the case number")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice, "docstatus"), 2)

	def test_a_document_is_required_where_the_category_says_and_only_its_people_can_open_it(self):
		frappe.set_user(STUDENT)
		self.assertRaises(frappe.ValidationError, sr.ask, self.student, "Change of name", "Married in October")
		self.assertRaises(frappe.ValidationError, sr.ask, self.student, "Change of name", "Married", (b"MZ", "certificate.exe"))
		doc = sr.ask(self.student, "Change of name", "Married in October", (PNG, "certificate.png"))
		self.assertTrue(frappe.db.get_value("Service Request", doc.name, "attachment"))
		frappe.set_user("student1.osh@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.document, doc.name)

	def test_the_student_withdraws_before_it_is_taken(self):
		mine = self._ask()
		self.assertEqual(api.withdraw(mine["name"])["status"], sr.WITHDRAWN)

	def test_the_registrar_keeps_the_categories(self):
		frappe.set_user(REGISTRY_KMP)
		self.assertRaises(frappe.PermissionError, api.save_category, {"category_name": "Parking permit", "office": "Student Affairs"})
		frappe.set_user("registrar@educore.localhost")
		page = api.save_category({"category_name": "Parking permit", "office": "Student Affairs", "response_days": 3, "fee": 50})
		self.assertIn("Parking permit", [r["name"] for r in page["rows"]])
		self.assertRaises(frappe.ValidationError, api.save_category, {"category_name": "Bad", "office": "Nowhere"})
		self.assertRaises(frappe.ValidationError, api.save_category, {"name": "Parking permit", "category_name": "Parking", "office": "Student Affairs"})
		api.save_category({"name": "Parking permit", "office": "Student Affairs", "disabled": 1})
		frappe.set_user(STUDENT)
		self.assertNotIn("Parking permit", [c["name"] for c in api.mine()["categories"]])
