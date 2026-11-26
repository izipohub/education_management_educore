"""The staff dashboard: sections by position, figures within the user's campus and faculty (educore.api.v1.dashboard)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import dashboard


def _as(login: str) -> dict:
	frappe.set_user(f"{login}@educore.localhost")
	try:
		return dashboard.stats()["sections"]
	finally:
		frappe.set_user("Administrator")


class TestDashboard(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "registrar@educore.localhost"):
			self.skipTest("run the demo setup first")

	def test_each_position_sees_its_own_sections(self):
		self.assertTrue({"students", "admissions", "enrolment", "registration"} <= set(_as("registrar")))
		self.assertEqual(set(_as("bursar")), {"fees"})
		lecturer = _as("lecturer.comp.whk")
		self.assertNotIn("admissions", lecturer)
		self.assertNotIn("fees", lecturer)

	def test_figures_stay_within_the_users_campus(self):
		everyone = _as("registrar")
		oshakati = _as("admissions-officer.osh")
		self.assertEqual([c["label"] for c in oshakati["students"]["by_campus"]], ["Oshakati Campus"])
		self.assertLess(oshakati["admissions"]["pipeline"][0]["value"], everyone["admissions"]["pipeline"][0]["value"])
		self.assertTrue(all(o["label"].split("-")[1] == "OSH" for o in oshakati["admissions"]["offerings"]))

	def test_fees_add_up(self):
		fees = _as("bursar")["fees"]
		self.assertAlmostEqual(fees["invoiced"], fees["collected"] + fees["outstanding"], places=2)
		self.assertAlmostEqual(fees["invoiced"], sum(c["invoiced"] for c in fees["by_campus"]), places=2)

	def test_full_offerings_come_first(self):
		offerings = _as("registrar")["admissions"]["offerings"]
		shares = [o["taken"] / o["capacity"] for o in offerings]
		self.assertEqual(shares, sorted(shares, reverse=True))

	def test_the_registrar_narrows_to_one_campus_and_an_officer_cannot_leave_theirs(self):
		frappe.set_user("registrar@educore.localhost")
		try:
			everyone = dashboard.stats()
			oshakati = dashboard.stats(campus="Oshakati Campus")
		finally:
			frappe.set_user("Administrator")
		self.assertIn("Oshakati Campus", everyone["campuses"])
		self.assertEqual([c["label"] for c in oshakati["sections"]["students"]["by_campus"]], ["Oshakati Campus"])
		self.assertLessEqual(oshakati["sections"]["admissions"]["total"], everyone["sections"]["admissions"]["total"])
		months = everyone["sections"]["admissions"]["by_month"]
		self.assertEqual(len(months), 12)
		self.assertEqual(sum(c["value"] for c in everyone["sections"]["admissions"]["by_channel"]), everyone["sections"]["admissions"]["total"])

		frappe.set_user("admissions-officer.osh@educore.localhost")
		try:
			self.assertRaises(frappe.PermissionError, dashboard.stats, campus="Windhoek Campus")
		finally:
			frappe.set_user("Administrator")


class TestWaitingForYou(IntegrationTestCase):
	"""What is waiting for each person on their home (educore.api.v1.dashboard._work), from the queues themselves"""

	def setUp(self):
		if not frappe.db.exists("User", "dean.fst@educore.localhost"):
			self.skipTest("run the demo setup first")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _work(self, user: str) -> dict[str, dict]:
		frappe.set_user(user)
		return {w["label"]: w for w in dashboard.stats()["work"]}

	def test_the_department_sees_its_approvals_and_another_faculty_does_not(self):
		from educore.api.v1 import examinations

		frappe.set_user("dean.fst@educore.localhost")
		plans = sum(1 for r in examinations.sheets()["rows"] if r["status"] == "Draft" and r["plan_status"] == "Proposed")
		work = self._work("dean.fst@educore.localhost")
		if plans:
			self.assertEqual(work["Assessment plans to approve"]["count"], plans)
			self.assertEqual(work["Assessment plans to approve"]["to"]["path"], "/approvals")
		self.assertNotIn("Assessment plans to approve", self._work("head-of-department.accf@educore.localhost"))

	def test_each_position_sees_its_own_queues_only(self):
		hr = self._work("hr-manager@educore.localhost")
		self.assertIn("Lecturers without an HR staff record", hr)
		self.assertNotIn("Transcripts to issue", hr)
		for item in self._work("registrar@educore.localhost").values():
			self.assertGreater(item["count"], 0)  # nothing waiting is not listed

	def test_a_lecturer_sees_their_lessons_and_registers(self):
		frappe.set_user("lecturer.accf.kmp@educore.localhost")
		page = dashboard.stats()
		self.assertIsInstance(page["lessons"], list)
		for item in page["work"]:
			self.assertIn(item["to"]["path"], ("/attendance", "/gradebook", "/marks", "/my-timetable"))

	def test_a_student_sees_what_is_coming_up(self):
		from educore.api.v1 import student

		frappe.set_user("student1.kmp@educore.localhost")
		self.assertEqual(set(student.overview()["ahead"]), {"lessons", "due", "papers"})
