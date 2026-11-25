"""Every position that has a screen can open it: the role checks of educore.api.v1 and the upstream read permissions
they rely on agree (a screen in a position's menu that the server refuses is a bug), and campus scope holds."""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import academic_staff, curriculum, examinations, graduation, student_payments, student_records, teaching_allocation

#: demo login → the read screens its position must open
SCREENS = {
	"vice-chancellor": ("teaching", "examinations", "graduation", "staff", "curriculum", "records"),
	"campus-director.osh": ("teaching", "examinations", "graduation", "staff", "curriculum", "records"),
	"quality-assurance-officer": ("teaching", "examinations", "staff", "curriculum"),
	"timetable-officer": ("teaching", "staff", "curriculum"),
	"examinations-officer": ("teaching", "examinations", "graduation", "curriculum", "records"),
	"head-of-department.comp": ("graduation", "teaching", "examinations", "staff", "records"),
	"registry-officer": ("curriculum", "graduation", "records"),
	"student-affairs-officer": ("records",),
	"financial-aid-officer": ("records",),
	"accommodation-officer": ("records",),
	"cashier": ("payments",),
}

CALLS = {
	"teaching": lambda: teaching_allocation.classes(),
	"examinations": lambda: examinations.sheets(),
	"graduation": lambda: graduation.candidates(),
	"staff": lambda: academic_staff.staff(),
	"curriculum": lambda: curriculum.programmes(),
	"records": lambda: student_records.student(student_records.students()["rows"][0]["name"]),
	"payments": lambda: student_payments.payments(),
}


class TestRoleAccess(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", "campus-director.osh@educore.localhost"):
			self.skipTest("run the demo setup first")

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_each_position_opens_its_screens(self):
		for login, screens in SCREENS.items():
			frappe.set_user(f"{login}@educore.localhost")
			for screen in screens:
				with self.subTest(login=login, screen=screen):
					CALLS[screen]()

	def test_a_campus_sees_its_own_classes_only(self):
		frappe.set_user("campus-director.osh@educore.localhost")
		self.assertEqual({r["campus"] for r in teaching_allocation.classes()["rows"]}, {"Oshakati Campus"})
		self.assertRaises(frappe.PermissionError, teaching_allocation.class_detail, "CMP1511 WHK 2026")

	def test_reading_is_not_deciding(self):
		frappe.set_user("vice-chancellor@educore.localhost")
		self.assertFalse(teaching_allocation.classes()["can_edit"])
		self.assertFalse(graduation.candidates()["can_confirm"])
		frappe.set_user("cashier@educore.localhost")
		self.assertRaises(frappe.PermissionError, frappe.get_attr("educore.api.v1.fee_settings.save"), {})

	def test_a_head_of_department_who_lectures_on_one_campus_moderates_every_campus(self):
		frappe.set_user("hod-lecturer.comp@educore.localhost")
		campuses = {r.get("campus") for r in examinations.sheets()["rows"]}
		self.assertGreater(len(campuses), 1)
