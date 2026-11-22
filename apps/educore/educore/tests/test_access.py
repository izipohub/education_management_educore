import frappe
from frappe.tests import IntegrationTestCase

from educore.access import demo_users, roles


class TestRolesAndPositions(IntegrationTestCase):
	def test_every_role_a_position_uses_exists(self):
		roles.sync()
		for position, position_roles in roles.all_positions().items():
			for role in position_roles:
				self.assertTrue(frappe.db.exists("Role", role), f"{position}: role {role} missing")

	def test_creates_educores_roles_with_their_desk_access(self):
		roles.sync()
		self.assertEqual(frappe.db.get_value("Role", "Faculty Officer", "desk_access"), 1)
		self.assertEqual(frappe.db.get_value("Role", "Applicant", "desk_access"), 0)

	def test_a_position_is_put_back_as_defined(self):
		roles.sync()
		profile = frappe.get_doc("Role Profile", "Registrar")
		profile.roles = [r for r in profile.roles if r.role != "Education Manager"]
		profile.append("roles", {"role": "System Manager"})
		profile.save(ignore_permissions=True)
		roles.sync()
		synced = {r.role for r in frappe.get_doc("Role Profile", "Registrar").roles}
		self.assertEqual(synced, set(roles.all_positions()["Registrar"]))

	def test_a_user_with_two_positions_gets_both_sets_of_roles(self):
		roles.sync()
		email = "hod-lecturer-test@educore.localhost"
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True)
		# as the seed scripts do, so Frappe's 60-new-users-an-hour throttle cannot fail the test
		frappe.flags.in_import = True
		try:
			user = demo_users.new_user(
				email=email,
				first_name="Test",
				last_name="",
				password="Campus-Demo-2026",
				positions=["Head of Department", "Lecturer"],
			)
		finally:
			frappe.flags.in_import = False
		user_roles = set(frappe.get_roles(user.name))
		self.assertTrue({"Head of Department", "Lecturer", "Instructor", "University Staff"} <= user_roles)
		# ERPNext gives Employee and Employee Self Service only once HR links an Employee record
		self.assertNotIn("Employee", user_roles)
		self.assertEqual(user.user_type, "System User")
		frappe.delete_doc("User", email, force=True)

	def test_scoped_users_see_only_their_campus_and_unit(self):
		from educore.access import test_users

		if not frappe.db.exists("User", "registry-officer.osh@educore.localhost"):
			self.skipTest("run educore.access.test_users.create first")
		self.assertEqual(len(test_users.plan()), 77)
		cases = {
			("registry-officer.osh", "Campus"): {"Oshakati Campus"},
			("registry-officer.whk-osh", "Campus"): {"Oshakati Campus", "Windhoek Campus"},
			("head-of-department.comp", "Department"): {"Department of Computing - EDU"},
			(
				"dean.fst",
				"Department",
			): {
				"Faculty of Science and Technology - EDU",
				"Department of Computing - EDU",
				"Department of Mathematics and Statistics - EDU",
			},
		}
		try:
			for (login, doctype), expected in cases.items():
				frappe.set_user(f"{login}@educore.localhost")
				self.assertEqual(set(frappe.get_list(doctype, pluck="name")), expected, login)
		finally:
			frappe.set_user("Administrator")

	def test_demo_user_emails(self):
		self.assertEqual(demo_users.email_for("Faculty Officer"), "faculty-officer@educore.localhost")
		self.assertEqual(demo_users.email_for("Vice-Chancellor"), "vice-chancellor@educore.localhost")
