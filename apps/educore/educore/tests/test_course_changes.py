"""Course changes after registration (educore.api.v1.course_changes)"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from educore.api.v1 import course_changes as api
from educore.api.v1 import registration

NDAPEWA = "student1.whk@educore.localhost"  # free to register for 2027 (year 2, Computer Science, Windhoek)
FST_WHK = "faculty-officer.fst.whk@educore.localhost"
FCM_WHK = "faculty-officer.fcm.whk@educore.localhost"
#: a first-year course she has no result for yet: open to add
EXTRA = "Computer Systems"


class TestCourseChanges(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Registration Period", "2027") or not frappe.db.exists("User", NDAPEWA):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("course_change_test")
		self._period(changes_until=add_days(nowdate(), 30))
		# registered for 2027 and approved
		frappe.set_user(NDAPEWA)
		state = registration.status()
		registration.save([c["course"] for c in state["courses"] if c["year"] == state["year_of_study"]])
		registration.submit()
		frappe.set_user(FST_WHK)
		self.enrolment = next(r for r in registration.queue()["rows"] if r["student_name"] == "Ndapewa Amukoto")["name"]
		registration.approve(self.enrolment)
		frappe.set_user(NDAPEWA)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="course_change_test")
		frappe.clear_document_cache("Registration Period", "2027")

	def _period(self, **values):
		frappe.set_user("Administrator")
		doc = frappe.get_doc("Registration Period", "2027")
		doc.update(values)
		doc.save(ignore_permissions=True)
		frappe.clear_document_cache("Registration Period", "2027")

	def _courses(self):
		return {row.course for row in frappe.get_doc("Program Enrollment", self.enrolment).courses}

	def test_a_course_added_once_the_faculty_approves(self):
		state = api.mine()
		self.assertTrue(state["open"])
		self.assertIn(EXTRA, [c["course"] for c in state["registration"]["courses"] if not c["registered"]])
		state = api.request(add=[EXTRA], reason="Not taken in my first year")
		self.assertEqual(state["changes"][0]["status"], api.SUBMITTED)
		self.assertNotIn(EXTRA, self._courses())
		# one request at a time
		self.assertRaisesRegex(frappe.ValidationError, "still with the faculty", api.request, add=[EXTRA])

		frappe.set_user(FST_WHK)
		change = api.queue()["rows"][0]["name"]
		api.approve(change)
		frappe.set_user("Administrator")
		self.assertIn(EXTRA, self._courses())
		self.assertTrue(frappe.db.exists("Course Enrollment", {"program_enrollment": self.enrolment, "course": EXTRA}))

		# and dropped again, by a second request
		frappe.set_user(NDAPEWA)
		api.request(drop=[EXTRA])
		frappe.set_user(FST_WHK)
		api.approve(api.queue()["rows"][0]["name"])
		frappe.set_user("Administrator")
		self.assertNotIn(EXTRA, self._courses())
		self.assertFalse(frappe.db.exists("Course Enrollment", {"program_enrollment": self.enrolment, "course": EXTRA}))

	def test_the_years_required_courses_stay(self):
		required = next(c["course"] for c in api.mine()["registration"]["courses"] if c["registered"] and c["required"])
		self.assertRaisesRegex(frappe.ValidationError, "Required this year", api.request, drop=[required])

	def test_nothing_to_change_and_courses_not_registered(self):
		self.assertRaises(frappe.ValidationError, api.request)
		self.assertRaisesRegex(frappe.ValidationError, "not one of the registered", api.request, drop=[EXTRA])

	def test_closed_after_the_course_change_date(self):
		self._period(changes_until=add_days(nowdate(), -1))
		frappe.set_user(NDAPEWA)
		self.assertFalse(api.mine()["open"])
		self.assertRaisesRegex(frappe.ValidationError, "closed", api.request, add=[EXTRA])

	def test_declined_with_a_reason_and_only_by_the_students_faculty(self):
		api.request(add=[EXTRA])
		frappe.set_user(FCM_WHK)
		self.assertEqual(api.queue()["rows"], [])
		frappe.set_user(FST_WHK)
		change = api.queue()["rows"][0]["name"]
		frappe.set_user(FCM_WHK)
		self.assertRaises(frappe.PermissionError, api.approve, change)
		frappe.set_user(FST_WHK)
		self.assertRaises(frappe.ValidationError, api.decline, change, " ")
		api.decline(change, "Timetable clash with Databases")
		frappe.set_user(NDAPEWA)
		self.assertEqual(api.mine()["changes"][0]["review_note"], "Timetable clash with Databases")
		self.assertNotIn(EXTRA, self._courses())

	def test_staff_do_not_request_and_students_do_not_approve(self):
		self.assertRaises(frappe.PermissionError, api.queue)
		frappe.set_user(FST_WHK)
		self.assertRaises(frappe.PermissionError, api.mine)
