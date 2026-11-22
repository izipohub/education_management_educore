from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from educore.access import desk


def _skip_without_users(test):
	if not frappe.db.exists("User", "bursar@educore.localhost"):
		test.skipTest("run educore.access.demo_users.create first")


class TestDeskAccess(IntegrationTestCase):
	def setUp(self):
		_skip_without_users(self)

	def test_back_office_and_ict_use_the_desk_others_do_not(self):
		for login in ("bursar", "payroll-officer", "procurement-officer", "ict-administrator"):
			self.assertTrue(desk.has_desk_access(f"{login}@educore.localhost"), login)
		for login in ("registrar", "lecturer", "admissions-officer", "cashier", "student"):
			self.assertFalse(desk.has_desk_access(f"{login}@educore.localhost"), login)
		self.assertTrue(desk.has_desk_access("Administrator"))

	def _redirects(self, user, path) -> str | None:
		"""Where the Desk sends this user (None: the request is left alone)"""
		frappe.set_user(user)
		try:
			return desk.desk_redirect(path)
		finally:
			frappe.set_user("Administrator")

	def test_the_desk_sends_vue_app_users_to_the_app(self):
		with patch.dict(frappe.local.conf, {"educore_app_url": "https://app.example.edu"}):
			self.assertEqual(self._redirects("registrar@educore.localhost", "/desk/student"), "https://app.example.edu")
			# portal users too: Frappe's own Desk page would refuse them with an error
			self.assertEqual(self._redirects("applicant@educore.localhost", "/desk"), "https://app.example.edu")
			self.assertEqual(self._redirects("student1.whk@educore.localhost", "/app/home"), "https://app.example.edu")

	def test_desk_users_guests_and_other_pages_are_left_alone(self):
		self.assertIsNone(self._redirects("bursar@educore.localhost", "/desk"))
		self.assertIsNone(self._redirects("Guest", "/desk"))  # Frappe's own login redirect handles guests
		self.assertIsNone(self._redirects("registrar@educore.localhost", "/login"))
		self.assertIsNone(self._redirects("registrar@educore.localhost", "/desktop-guide"))


class TestBackOfficeModules(IntegrationTestCase):
	def setUp(self):
		_skip_without_users(self)

	def test_back_office_users_see_a_trimmed_desk_ict_sees_all(self):
		bursar = frappe.get_doc("User", "bursar@educore.localhost")
		self.assertEqual(bursar.module_profile, desk.BACK_OFFICE_PROFILE)
		blocked = {row.module for row in bursar.block_modules}
		self.assertIn("Manufacturing", blocked)
		self.assertNotIn("Accounts", blocked)
		self.assertNotIn("Selling", blocked, "student Customers live in Selling")
		self.assertFalse(frappe.db.get_value("User", "ict-administrator@educore.localhost", "module_profile"))
