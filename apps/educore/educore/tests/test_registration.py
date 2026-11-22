"""Re-registration of returning students (educore.registration, educore.api.v1.registration)"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from educore.api.v1 import registration as api
from educore.registration import rules

NDAPEWA = "student1.whk@educore.localhost"  # paid 2026 and her deposit: free to register
ANNA = "student1.kmp@educore.localhost"  # owes 2026 fees
TANGENI = "student2.osh@educore.localhost"  # on hold
FST_WHK = "faculty-officer.fst.whk@educore.localhost"
FCM_WHK = "faculty-officer.fcm.whk@educore.localhost"


class TestRegistration(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Registration Period", "2027") or not frappe.db.exists("User", NDAPEWA):
			self.skipTest("run educore.setup.demo_students.create first")
		# every test starts from the demo as it is
		frappe.db.savepoint("registration_test")
		frappe.set_user(NDAPEWA)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="registration_test")
		for doctype, name in (("Registration Period", "2027"), ("Registration Settings", "Registration Settings")):
			frappe.clear_document_cache(doctype, name)

	def _set(self, doctype, name, **values):
		frappe.set_user("Administrator")
		doc = frappe.get_doc(doctype, name)
		doc.update(values)
		doc.save(ignore_permissions=True)

	def _register(self):
		state = api.status()
		year_courses = [c["course"] for c in state["courses"] if c["year"] == state["year_of_study"]]
		api.save(year_courses)
		return api.submit()

	# --- the student -----------------------------------------------------------------------------------

	def test_a_returning_student_registers_for_the_next_year(self):
		state = api.status()
		self.assertEqual((state["period"]["academic_year"], state["period"]["state"], state["year_of_study"]), ("2027", "open", 2))
		self.assertEqual(state["blockers"], [])
		state = self._register()
		self.assertEqual(state["registration"]["status"], rules.SUBMITTED)
		self.assertFalse(state["registration"]["late"])
		self.assertRaises(frappe.ValidationError, api.save, [])  # submitted: no more changes

	def test_the_years_required_courses_must_be_chosen(self):
		state = api.status()
		one = [c["course"] for c in state["courses"] if c["year"] == 2][:1]
		api.save(one)
		self.assertRaisesRegex(frappe.ValidationError, "Required for year 2", api.submit)

	def test_outstanding_fees_and_standing_block_registration(self):
		frappe.set_user(ANNA)
		self.assertTrue(any("Outstanding fees: N$ 10,150.00" in b for b in api.status()["blockers"]))
		frappe.set_user(TANGENI)
		state = api.status()
		self.assertTrue(any(b.startswith("Academic standing: On hold") for b in state["blockers"]))
		api.save([c["course"] for c in state["courses"] if c["year"] == 2])
		self.assertRaisesRegex(frappe.ValidationError, "cannot register yet", api.submit)

	def test_the_deposit_is_the_universitys_to_set(self):
		self._set("Registration Settings", "Registration Settings", deposit_type="Amount", deposit_value=50000)
		frappe.set_user(NDAPEWA)
		self.assertTrue(any(b.startswith("Registration deposit: N$") for b in api.status()["blockers"]))

	def test_registration_outside_the_period(self):
		self._set("Registration Period", "2027", opens_on=add_days(nowdate(), -60), closes_on=add_days(nowdate(), -30), late_until=None)
		frappe.set_user(NDAPEWA)
		self.assertEqual(api.status()["period"]["state"], "closed")
		self.assertRaisesRegex(frappe.ValidationError, "not open", api.save, [])

	# --- the faculty officer ---------------------------------------------------------------------------

	def test_the_faculty_officer_approves_and_the_year_is_invoiced(self):
		self._register()
		frappe.set_user(FST_WHK)
		rows = api.queue()["rows"]
		row = next(r for r in rows if r["student_name"] == "Ndapewa Amukoto")
		api.approve(row["name"])
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Program Enrollment", row["name"], "docstatus"), 1)
		invoice = frappe.db.get_value("Sales Invoice", {"educore_program_enrollment": row["name"], "docstatus": 1}, "grand_total")
		self.assertEqual(invoice, rules.year_fees("BCS-WHK-FT", "2027"))
		frappe.set_user(NDAPEWA)
		self.assertEqual(api.status()["registration"]["status"], rules.APPROVED)

	def test_other_faculties_neither_see_nor_approve(self):
		self._register()
		frappe.set_user("Administrator")
		name = frappe.db.get_value("Program Enrollment", {"student_name": "Ndapewa Amukoto", "academic_year": "2027"})
		frappe.set_user(FCM_WHK)
		self.assertNotIn(name, [r["name"] for r in api.queue()["rows"]])
		self.assertRaises(frappe.PermissionError, api.approve, name)
		frappe.set_user(NDAPEWA)
		self.assertRaises(frappe.PermissionError, api.queue)

	def test_a_returned_registration_is_changed_and_submitted_again(self):
		self._register()
		frappe.set_user(FST_WHK)
		name = next(r["name"] for r in api.queue()["rows"] if r["student_name"] == "Ndapewa Amukoto")
		self.assertRaises(frappe.ValidationError, api.return_registration, name, "")
		api.return_registration(name, "Add Linear Algebra")
		frappe.set_user(NDAPEWA)
		state = api.status()
		self.assertEqual((state["registration"]["status"], state["registration"]["review_note"]), (rules.RETURNED, "Add Linear Algebra"))
		self.assertEqual(self._register()["registration"]["status"], rules.SUBMITTED)

	def test_late_registration_adds_the_late_fee(self):
		self._set("Registration Period", "2027", closes_on=add_days(nowdate(), -1), late_until=add_days(nowdate(), 10), late_fee=500)
		frappe.set_user(NDAPEWA)
		self.assertTrue(self._register()["registration"]["late"])
		frappe.set_user(FST_WHK)
		name = next(r["name"] for r in api.queue()["rows"] if r["student_name"] == "Ndapewa Amukoto")
		api.approve(name)
		frappe.set_user("Administrator")
		invoice = frappe.db.get_value("Sales Invoice", {"educore_program_enrollment": name, "docstatus": 1})
		late = frappe.db.get_value("Sales Invoice Item", {"parent": invoice, "item_code": "Late Registration Fee"}, "amount")
		self.assertEqual(late, 500)

	def test_without_approval_a_submitted_registration_is_approved_at_once(self):
		self._set("Registration Settings", "Registration Settings", approval_needed=0)
		frappe.set_user(NDAPEWA)
		self.assertEqual(self._register()["registration"]["status"], rules.APPROVED)
