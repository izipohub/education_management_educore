import frappe
from frappe.tests import IntegrationTestCase


def _unit(code):
	return frappe.db.get_value("Department", {"educore_unit_code": code})


def _campus(code):
	return frappe.db.get_value("Campus", {"campus_code": code})


class TestCatalogue(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Program", {"educore_programme_code": "BCS"}):
			self.skipTest("run educore.setup.demo.create_demo_university first")

	def _program(self, **values):
		return frappe.get_doc({"doctype": "Program", "program_name": "Test Programme", **values}).insert(
			ignore_permissions=True
		)

	def test_a_programme_belongs_to_an_academic_unit(self):
		program = self._program(educore_programme_code="tpx", department=_unit("COMP"), educore_nqf_level=7)
		self.assertEqual(program.educore_programme_code, "TPX")
		self.assertRaises(frappe.ValidationError, self._program, program_name="Test Registry Programme", department=_unit("REG"))

	def test_nqf_level_is_between_1_and_10(self):
		self.assertRaises(frappe.ValidationError, self._program, educore_nqf_level=11)

	def test_a_course_belongs_to_an_academic_unit(self):
		course = frappe.get_doc(
			{"doctype": "Course", "course_name": "Test Course", "educore_course_code": "tst1511", "department": _unit("MATH")}
		).insert(ignore_permissions=True)
		self.assertEqual(course.educore_course_code, "TST1511")
		self.assertRaises(
			frappe.ValidationError,
			frappe.get_doc({"doctype": "Course", "course_name": "Test Finance Course", "department": _unit("FIN")}).insert,
			ignore_permissions=True,
		)


class TestProgrammeOffering(IntegrationTestCase):
	def setUp(self):
		self.program = frappe.db.get_value("Program", {"educore_programme_code": "BCS"})
		if not self.program:
			self.skipTest("run educore.setup.demo.create_demo_university first")

	def _offering(self, campus, mode):
		return frappe.get_doc(
			{"doctype": "Programme Offering", "program": self.program, "campus": _campus(campus), "mode_of_study": mode}
		).insert(ignore_permissions=True)

	def test_named_by_programme_campus_and_mode(self):
		offering = self._offering("OSH", "Part-time")
		self.assertEqual(offering.name, "BCS-OSH-PT")
		self.assertEqual(offering.department, _unit("COMP"))

	def test_a_campus_offers_a_programme_once_per_mode(self):
		# BCS-WHK-FT is in the demo data
		self.assertRaises(frappe.ValidationError, self._offering, "WHK", "Full-time")

	def test_only_on_a_campus_the_department_works_on(self):
		# Computing works on Windhoek and Oshakati, not Keetmanshoop
		self.assertRaises(frappe.ValidationError, self._offering, "KMP", "Full-time")


class TestCatalogueAccess(IntegrationTestCase):
	def test_lecturers_read_but_do_not_edit_the_catalogue(self):
		user = "lecturer.comp.osh@educore.localhost"
		if not frappe.db.exists("User", user):
			self.skipTest("run educore.access.test_users.create first")
		program = frappe.db.get_value("Program", {"educore_programme_code": "BCS"})
		self.assertTrue(frappe.has_permission("Program", "read", program, user=user))
		self.assertFalse(frappe.has_permission("Program", "write", program, user=user))
		self.assertFalse(frappe.has_permission("Course", "write", user=user))

	def test_campus_and_faculty_users_see_their_offerings(self):
		cases = {
			"registry-officer.osh": {"BACC-OSH-FT", "BCS-OSH-FT", "BEDP-OSH-FT", "DIT-OSH-FT"},
			"faculty-officer.fcm.kmp": {"BACC-KMP-PT", "BBA-KMP-PT", "DAF-KMP-FT"},
			"dean.fhs": {"BNS-WHK-FT"},
		}
		if not frappe.db.exists("User", "registry-officer.osh@educore.localhost"):
			self.skipTest("run educore.access.test_users.create first")
		try:
			for login, expected in cases.items():
				frappe.set_user(f"{login}@educore.localhost")
				self.assertEqual(set(frappe.get_list("Programme Offering", pluck="name")), expected, login)
		finally:
			frappe.set_user("Administrator")
