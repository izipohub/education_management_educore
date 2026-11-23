"""Teaching allocation: classes from approved registrations, lecturers allocated by the faculty
(educore.api.v1.teaching_allocation)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import teaching_allocation as api

HOD = "hod-lecturer.comp@educore.localhost"


class TestTeachingAllocation(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", HOD) or not frappe.db.exists("Student Group", "CMP1511 OSH 2026"):
			self.skipTest("run the demo setup first")
		self.addCleanup(frappe.set_user, "Administrator")

	def test_each_head_of_department_sees_their_own_courses(self):
		frappe.set_user(HOD)
		rows = api.classes("2026")["rows"]
		self.assertTrue(rows)
		self.assertTrue(all(r["department"] == "Department of Computing" for r in rows))
		frappe.set_user("registrar@educore.localhost")
		everyone = api.classes("2026")
		self.assertGreater(len(everyone["rows"]), len(rows))
		self.assertFalse(everyone["can_edit"])

	def test_class_lists_follow_approved_registrations_and_take_the_semester(self):
		frappe.set_user(HOD)
		result = api.update_class_lists("2026")
		row = next(r for r in result["rows"] if r["group"] == "CMP1521 OSH 2026")
		self.assertEqual((row["semester"], row["in_class"], row["registered"]), ("Semester 2", row["registered"], row["registered"]))
		self.assertEqual(frappe.db.get_value("Student Group", "CMP1521 OSH 2026", "academic_term"), "2026 (Semester 2)")

	def test_the_head_of_department_allocates_lecturers(self):
		frappe.set_user(HOD)
		detail = api.class_detail("CMP1511 OSH 2026")
		other = next(i["name"] for i in detail["instructors"] if i["name"] not in [l["instructor"] for l in detail["lecturers"]])
		saved = api.set_lecturers("CMP1511 OSH 2026", [l["instructor"] for l in detail["lecturers"]] + [other])
		self.assertIn(other, [l["instructor"] for l in saved["lecturers"]])
		self.assertRaises(frappe.ValidationError, api.set_lecturers, "CMP1511 OSH 2026", ["Nobody"])

	def test_others_cannot_allocate(self):
		frappe.set_user("registrar@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.set_lecturers, "CMP1511 OSH 2026", [])
		self.assertRaises(frappe.PermissionError, api.update_class_lists, "2026")
		frappe.set_user("head-of-department.nurs@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.set_lecturers, "CMP1511 OSH 2026", [])
		frappe.set_user("student1.whk@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.classes)
