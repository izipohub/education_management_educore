import frappe
from frappe.tests import IntegrationTestCase

from educore.setup import university

COMPANY = "EduCore Demo University"


def _root_department():
	return frappe.db.get_value("Department", {"is_group": 1, "parent_department": ("in", ("", None))})


class TestCampus(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Company", COMPANY):
			self.skipTest("run educore.setup.demo.create_demo_university first")

	def _campus(self, name, code, **extra):
		return frappe.get_doc(
			{"doctype": "Campus", "campus_name": name, "campus_code": code, "company": COMPANY, **extra}
		).insert(ignore_permissions=True)

	def test_a_new_campus_gets_its_own_cost_center_and_branch(self):
		campus = self._campus("Test Rundu Campus", "trd")
		self.assertEqual(campus.campus_code, "TRD")
		self.assertEqual(campus.cost_center, "Test Rundu Campus - EDU")
		cost_center = frappe.get_doc("Cost Center", campus.cost_center)
		self.assertEqual(cost_center.is_group, 0, "campus postings need a leaf cost center")
		self.assertEqual(cost_center.parent_cost_center, "EduCore Demo University - EDU")
		self.assertTrue(frappe.db.exists("Branch", "Test Rundu Campus"))

	def test_only_one_main_campus(self):
		self.assertRaises(frappe.ValidationError, self._campus, "Test Second Main", "TSM", is_main_campus=1)


class TestUniversityUnits(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Company", COMPANY):
			self.skipTest("run educore.setup.demo.create_demo_university first")

	def _unit(self, name, unit_type, parent, code=None, campuses=()):
		return frappe.get_doc(
			{
				"doctype": "Department",
				"department_name": name,
				"company": COMPANY,
				"parent_department": parent,
				"educore_unit_type": unit_type,
				"educore_unit_code": code,
				"educore_campuses": [{"campus": c} for c in campuses],
			}
		).insert(ignore_permissions=True)

	def test_a_faculty_holds_departments(self):
		faculty = self._unit("Test Faculty of Law", "Faculty", _root_department(), "tfl")
		self.assertEqual(faculty.is_group, 1)
		self.assertEqual(faculty.educore_unit_code, "TFL")
		department = self._unit("Test Department of Public Law", "Academic Department", faculty.name)
		self.assertEqual(department.parent_department, faculty.name)

	def test_an_academic_department_must_sit_under_a_faculty_or_school(self):
		self.assertRaises(
			frappe.ValidationError, self._unit, "Test Stray Department", "Academic Department", _root_department()
		)
		division = frappe.db.get_value("Department", {"educore_unit_code": "FINA"})
		self.assertRaises(frappe.ValidationError, self._unit, "Test Misplaced", "Academic Department", division)

	def test_a_campus_is_listed_once(self):
		self.assertRaises(
			frappe.ValidationError,
			self._unit,
			"Test Twice Faculty",
			"Faculty",
			_root_department(),
			campuses=("Windhoek Campus", "Windhoek Campus"),
		)

	def test_erpnexts_own_departments_are_left_alone(self):
		department = frappe.get_doc(
			{"doctype": "Department", "department_name": "Test Plain", "company": COMPANY, "parent_department": _root_department()}
		).insert(ignore_permissions=True)
		self.assertFalse(department.educore_unit_type)


class TestUniversitySetup(IntegrationTestCase):
	def test_running_setup_again_changes_nothing(self):
		if not frappe.db.exists("Company", COMPANY):
			self.skipTest("run educore.setup.demo.create_demo_university first")
		self.assertEqual(university.setup_university(COMPANY, "EDU", "2026-01-01", "2026-12-31"), COMPANY)
		self.assertEqual(frappe.db.get_value("Company", COMPANY, "cost_center"), "Central Administration - EDU")
		self.assertFalse(frappe.db.exists("Cost Center", "Main - EDU"))
		self.assertFalse(frappe.db.exists("Department", "Sales - EDU"))
