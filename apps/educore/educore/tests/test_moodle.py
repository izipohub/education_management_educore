"""Keeping Moodle in step with the classes (educore.learning.moodle), against an in-memory stand-in for Moodle's
web services: no Moodle site is needed to run these."""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import integrations
from educore.learning import moodle

CLASS = "CMP1511 WHK 2026"


class FakeMoodle:
	"""The web service functions EduCore calls, kept in memory"""

	def __init__(self, fail: str | None = None):
		self.users, self.courses, self.categories, self.enrolments = {}, {}, {}, set()
		self.calls, self.fail = [], fail

	def _next(self, table):
		return len(table) + 100

	def call(self, function, **p):
		self.calls.append(function)
		if function == self.fail:
			raise moodle.MoodleError(f"{function}: refused")
		if function == "core_user_get_users_by_field":
			return [{"id": i, **u} for i, u in self.users.items() if u.get(p["field"]) in p["values"]]
		if function == "core_user_update_users":
			for u in p["users"]:
				self.users[u["id"]].update({k: v for k, v in u.items() if k != "id"})
			return None
		if function == "core_user_create_users":
			out = []
			for u in p["users"]:
				uid = self._next(self.users)
				self.users[uid] = u
				out.append({"id": uid, "username": u["username"]})
			return out
		if function == "core_course_get_categories":
			key = p["criteria"][0]["value"]
			return [{"id": i} for i, c in self.categories.items() if c["idnumber"] == key]
		if function == "core_course_create_categories":
			cid = self._next(self.categories)
			self.categories[cid] = p["categories"][0]
			return [{"id": cid}]
		if function == "core_course_get_courses_by_field":
			return {"courses": [{"id": i} for i, c in self.courses.items() if c["idnumber"] == p["value"]]}
		if function == "core_course_create_courses":
			cid = self._next(self.courses)
			self.courses[cid] = p["courses"][0]
			return [{"id": cid, "shortname": p["courses"][0]["shortname"]}]
		if function == "core_enrol_get_enrolled_users":
			return [{"id": u, "roles": [{"roleid": r}]} for (u, c, r) in self.enrolments if c == p["courseid"]]
		if function == "enrol_manual_enrol_users":
			for e in p["enrolments"]:
				self.enrolments.add((e["userid"], e["courseid"], e["roleid"]))
			return None
		if function == "enrol_manual_unenrol_users":
			for e in p["enrolments"]:
				self.enrolments = {x for x in self.enrolments if not (x[0] == e["userid"] and x[1] == e["courseid"])}
			return None
		if function == "core_webservice_get_site_info":
			return {"sitename": "Test Moodle", "release": "4.5", "username": "educore", "functions": [{"name": f} for f in moodle.FUNCTIONS[:-1]]}
		raise AssertionError(f"unexpected {function}")


class TestMoodleSync(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Group", CLASS):
			self.skipTest("run the demo setup first")
		frappe.set_user("Administrator")

	def test_a_class_becomes_a_moodle_course_with_its_students_and_lecturers(self):
		fake = FakeMoodle()
		result = moodle.sync_class(CLASS, fake)
		group = frappe.get_doc("Student Group", CLASS)
		students = [s for s in group.students if s.active]
		self.assertEqual(result["enrolled"], len(students) + len(group.instructors))
		course = fake.courses[result["course_id"]]
		self.assertEqual(course["idnumber"], CLASS)
		self.assertIn(students[0].student, [u["idnumber"] for u in fake.users.values()])
		self.assertEqual(frappe.db.get_value("Student Group", CLASS, "educore_moodle_course_id"), result["course_id"])
		# the campus has its own category
		self.assertEqual(list(fake.categories.values())[0]["name"], group.campus)

	def test_syncing_again_changes_nothing(self):
		fake = FakeMoodle()
		moodle.sync_class(CLASS, fake)
		created = (len(fake.users), len(fake.courses), len(fake.enrolments))
		again = moodle.sync_class(CLASS, fake)
		self.assertEqual((len(fake.users), len(fake.courses), len(fake.enrolments)), created)
		self.assertEqual((again["enrolled"], again["unenrolled"]), (0, 0))

	def test_a_student_who_leaves_the_class_is_unenrolled(self):
		fake = FakeMoodle()
		first = moodle.sync_class(CLASS, fake)
		group = frappe.get_doc("Student Group", CLASS)
		group.students[0].active = 0
		group.save(ignore_permissions=True)
		result = moodle.sync_class(CLASS, fake)
		self.assertEqual(result["unenrolled"], 1)
		self.assertEqual(len([e for e in fake.enrolments if e[1] == first["course_id"]]), first["enrolled"] - 1)

	def test_a_refusal_is_kept_on_the_class_and_tried_again_later(self):
		result = moodle.sync_class(CLASS, FakeMoodle(fail="core_course_create_courses"))
		self.assertIn("refused", result["error"])
		self.assertIn("refused", frappe.db.get_value("Student Group", CLASS, "educore_moodle_error"))
		moodle.sync_class(CLASS, FakeMoodle())
		self.assertFalse(frappe.db.get_value("Student Group", CLASS, "educore_moodle_error"))

	def test_nothing_happens_until_ict_connects_moodle(self):
		frappe.db.set_single_value("Learning Platform Settings", "moodle_enabled", 0)
		self.assertEqual(moodle.sync_all(), {"skipped": True})


class TestIntegrationsScreen(IntegrationTestCase):
	def test_only_ict_and_the_token_is_never_read_back(self):
		frappe.set_user("Administrator")
		data = integrations.save({"moodle_url": "https://moodle.example.edu.na", "moodle_token": "secret-token"})
		self.assertTrue(data["moodle"]["has_token"])
		self.assertNotIn("secret-token", frappe.as_json(data))
		self.assertRaises(frappe.ValidationError, integrations.save, {"moodle_enabled": 1, "moodle_url": ""})
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, integrations.settings)
		frappe.set_user("Administrator")


class TestConnectionCheck(IntegrationTestCase):
	def test_the_check_names_the_functions_the_token_lacks(self):
		with __import__("unittest.mock").mock.patch.object(moodle, "MoodleClient", return_value=FakeMoodle()):
			result = moodle.test_connection("https://moodle.example.edu.na", "token")
		self.assertEqual(result["site"], "Test Moodle")
		self.assertEqual(result["missing"], ["gradereport_user_get_grade_items"])


class TestSingleSignOn(IntegrationTestCase):
	"""Moodle signs people in with EduCore (educore.learning.moodle_sso)"""

	def setUp(self):
		frappe.set_user("Administrator")
		frappe.db.savepoint("sso_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="sso_test")

	def test_choosing_single_sign_on_makes_moodle_a_trusted_client(self):
		from unittest.mock import patch

		from educore.learning import moodle_sso

		with patch.dict(frappe.local.conf, {"educore_app_url": "https://app.example.edu"}):
			page = integrations.save({"moodle_url": "https://moodle.example.edu", "moodle_token": "t", "sign_in": "Single sign-on"})
		sso = page["sso"]
		self.assertEqual(sso["redirect_uri"], "https://moodle.example.edu/admin/oauth2callback.php")
		self.assertEqual(sso["authorization_endpoint"], "https://app.example.edu/api/method/frappe.integrations.oauth2.authorize")
		client = frappe.get_doc("OAuth Client", sso["client_id"])
		self.assertTrue(client.skip_authorization)  # the university's own Moodle: no "allow access?" screen
		self.assertIn("openid", client.scopes.split())
		self.assertEqual(sso["client_secret"], client.client_secret)
		# saving again keeps the same client (Moodle keeps its ID and secret)
		again = integrations.save({"sign_in": "Single sign-on"})
		self.assertEqual(again["sso"]["client_id"], sso["client_id"])
		# Moodle passwords instead: Moodle may no longer sign people in with EduCore
		self.assertIsNone(integrations.save({"sign_in": "Moodle password"})["sso"])
		self.assertIsNone(moodle_sso.client_name())

	def test_only_ict_sees_the_client_secret(self):
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, integrations.settings)


class TestSingleSignOnAccounts(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student Group", CLASS):
			self.skipTest("run the demo setup first")
		frappe.set_user("Administrator")
		frappe.db.savepoint("sso_accounts")

	def tearDown(self):
		frappe.db.rollback(save_point="sso_accounts")

	def test_accounts_made_with_a_moodle_password_sign_in_with_educore_once_single_sign_on_is_chosen(self):
		fake = FakeMoodle()
		frappe.db.set_single_value("Learning Platform Settings", "sign_in", "Moodle password")
		moodle.sync_class(CLASS, fake)
		self.assertEqual({u["auth"] for u in fake.users.values()}, {"manual"})
		frappe.db.set_single_value("Learning Platform Settings", "sign_in", "Single sign-on")
		moodle.sync_class(CLASS, fake)
		self.assertEqual({u["auth"] for u in fake.users.values()}, {"oauth2"})
		self.assertTrue(all(u["preferences"][0]["value"] == 0 for u in fake.users.values()))
		# and nothing more to change after that
		calls = len(fake.calls)
		moodle.sync_class(CLASS, fake)
		self.assertNotIn("core_user_update_users", fake.calls[calls:])
