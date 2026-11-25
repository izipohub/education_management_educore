"""Lecturers set up automatically from the Lecturer position (educore.academics.lecturers), and the Academic staff
screen (educore.api.v1.academic_staff)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.academics import lecturers
from educore.api.v1 import academic_staff as api

HOD_ACCF = "head-of-department.accf@educore.localhost"
DEAN_FST = "dean.fst@educore.localhost"
HR = "hr-manager@educore.localhost"
ACCF = "Department of Accounting and Finance - EDU"


class TestLecturers(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", HOD_ACCF) or not frappe.db.exists("Department", ACCF):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("lecturers_test")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="lecturers_test")

	def _new_login(self, email="new-lecturer.accf@educore.localhost"):
		user = frappe.new_doc("User")
		user.update({"email": email, "first_name": "Selma", "last_name": "Nghipondoka", "send_welcome_email": 0})
		user.append("roles", {"role": "Lecturer"})
		user.insert(ignore_permissions=True)
		for allow, value in (("Department", ACCF), ("Campus", "Windhoek Campus")):
			frappe.get_doc({"doctype": "User Permission", "user": email, "allow": allow, "for_value": value, "apply_to_all_doctypes": 1}).insert(
				ignore_permissions=True
			)
		return email

	def test_a_lecturer_login_gets_its_record_with_department_and_campus(self):
		email = self._new_login()
		name = frappe.db.get_value("Instructor", {"educore_user": email})
		self.assertTrue(name)
		doc = frappe.get_doc("Instructor", name)
		self.assertEqual(doc.department, ACCF)
		self.assertEqual([r.campus for r in doc.educore_campuses], ["Windhoek Campus"])
		self.assertEqual(doc.status, "Active")
		frappe.set_user(email)
		self.assertEqual(lecturers.instructors_of(email), [name])

	def test_losing_the_position_marks_the_lecturer_left_and_regaining_it_restores(self):
		email = self._new_login()
		user = frappe.get_doc("User", email)
		user.roles = [r for r in user.roles if r.role != "Lecturer"]
		user.save(ignore_permissions=True)
		name = frappe.db.get_value("Instructor", {"educore_user": email})
		self.assertEqual(frappe.db.get_value("Instructor", name, "status"), "Left")
		self.assertEqual(lecturers.instructors_of(email), [])
		user.reload()
		user.append("roles", {"role": "Lecturer"})
		user.save(ignore_permissions=True)
		self.assertEqual(frappe.db.get_value("Instructor", name, "status"), "Active")

	def test_the_head_of_department_sees_their_department_and_completes_it(self):
		email = self._new_login()
		name = frappe.db.get_value("Instructor", {"educore_user": email})
		frappe.set_user(HOD_ACCF)
		rows = {r["name"]: r for r in api.staff()["rows"]}
		self.assertIn(name, rows)
		self.assertEqual(rows[name]["state"], api.INCOMPLETE)
		self.assertEqual(rows[name]["missing"], ["HR staff record"])
		page = api.save(name, campuses=["Windhoek Campus", "Oshakati Campus"])
		self.assertEqual(page["campuses"], ["Windhoek Campus", "Oshakati Campus"])

		frappe.set_user(DEAN_FST)  # another faculty
		self.assertNotIn(name, {r["name"] for r in api.staff()["rows"]})
		self.assertRaises(frappe.PermissionError, api.lecturer, name)

	def test_hr_links_the_staff_record_and_gives_it_the_login(self):
		email = self._new_login()
		name = frappe.db.get_value("Instructor", {"educore_user": email})
		employee = frappe.get_doc(
			{
				"doctype": "Employee",
				"first_name": "Selma",
				"last_name": "Nghipondoka",
				"company": frappe.db.get_value("Campus", "Windhoek Campus", "company"),
				"gender": "Female",
				"date_of_birth": "1988-03-02",
				"date_of_joining": "2026-02-01",
				"status": "Active",
			}
		).insert(ignore_permissions=True)
		frappe.set_user(HOD_ACCF)
		self.assertRaises(frappe.PermissionError, api.link_staff_record, name, employee.name)
		frappe.set_user(HR)
		page = api.link_staff_record(name, employee.name)
		self.assertEqual(page["state"], api.READY)
		self.assertEqual(frappe.db.get_value("Employee", employee.name, "user_id"), email)
