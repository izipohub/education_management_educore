import frappe
from education.education.api import enroll_student
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase

from educore.academics.calendar import ensure_academic_year, term
from educore.access import demo_users


class TestAdmissionsFlow(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Programme Offering", "BCS-OSH-FT"):
			self.skipTest("run educore.setup.demo.create_demo_university first")
		ensure_academic_year(2027)

	def _applicant(self, offering="BCS-OSH-FT", **extra):
		return frappe.get_doc(
			{
				"doctype": "Student Applicant",
				"first_name": "Test",
				"last_name": "Applicant",
				"educore_programme_offering": offering,
				"academic_year": "2027",
				"academic_term": term(2027, "Semester 1"),
				**extra,
			}
		).insert(ignore_permissions=True)

	def test_an_application_is_for_an_offering(self):
		applicant = self._applicant(program=frappe.db.get_value("Program", {"educore_programme_code": "BACC"}))
		# the offering decides the programme and campus, whatever was typed in
		self.assertEqual(applicant.program, frappe.db.get_value("Programme Offering", "BCS-OSH-FT", "program"))
		self.assertEqual(applicant.campus, "Oshakati Campus")
		self.assertEqual(applicant.educore_mode_of_study, "Full-time")
		self.assertRaises(frappe.ValidationError, self._applicant, offering=None)

	def test_an_inactive_offering_takes_no_applications(self):
		frappe.db.set_value("Programme Offering", "BCS-OSH-FT", "is_active", 0)
		frappe.clear_document_cache("Programme Offering", "BCS-OSH-FT")
		try:
			self.assertRaises(frappe.ValidationError, self._applicant)
		finally:
			frappe.db.set_value("Programme Offering", "BCS-OSH-FT", "is_active", 1)
			frappe.clear_document_cache("Programme Offering", "BCS-OSH-FT")

	def test_enrolling_an_applicant_carries_the_offering_through(self):
		# the student's login exists already, so Education does not create one: no welcome email (which
		# needs built assets) and no run-in with Frappe's new-users-per-hour throttle
		email = "test.enrol@educore.localhost"
		if not frappe.db.exists("User", email):
			frappe.flags.in_import = True
			try:
				demo_users.new_user(email=email, first_name="Test", last_name="Enrol", password="Campus-Demo-2026", positions=[])
			finally:
				frappe.flags.in_import = False
		applicant = self._applicant(student_email_id=email)
		apply_workflow(applicant, "Approve")
		enrollment = enroll_student(applicant.name)
		self.assertEqual(enrollment.educore_programme_offering, "BCS-OSH-FT")
		self.assertEqual(enrollment.campus, "Oshakati Campus")
		self.assertEqual(enrollment.department, frappe.db.get_value("Department", {"educore_unit_code": "COMP"}))
		enrollment.enrollment_date = "2027-02-01"
		enrollment.save(ignore_permissions=True)
		enrollment.submit()
		student = frappe.get_doc("Student", enrollment.student)
		self.assertEqual(student.campus, "Oshakati Campus")
		self.assertEqual(student.department, enrollment.department)

	def test_an_enrolment_matches_its_offering(self):
		student = frappe.db.get_value("Student", {"user": "student1.whk@educore.localhost"})
		if not student:
			self.skipTest("run educore.setup.demo_students.create first")
		enrollment = frappe.get_doc(
			{
				"doctype": "Program Enrollment",
				"student": student,
				"program": frappe.db.get_value("Program", {"educore_programme_code": "BACC"}),
				"educore_programme_offering": "BCS-WHK-FT",
				"academic_year": "2027",
				"enrollment_date": "2027-02-01",
			}
		)
		self.assertRaises(frappe.ValidationError, enrollment.insert, ignore_permissions=True)


class TestStudentRecordAccess(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Student", {"user": "student1.whk@educore.localhost"}):
			self.skipTest("run educore.access.test_users.create and educore.setup.demo_students.create first")

	def _visible(self, login, doctype, field="student_name"):
		frappe.set_user(f"{login}@educore.localhost")
		try:
			return set(frappe.get_list(doctype, pluck=field))
		finally:
			frappe.set_user("Administrator")

	def test_a_student_sees_only_their_own_enrolment(self):
		self.assertEqual(self._visible("student1.whk", "Program Enrollment"), {"Ndapewa Amukoto"})
		other = frappe.db.get_value("Program Enrollment", {"student_name": "Lukas Garoeb"})
		self.assertFalse(frappe.has_permission("Program Enrollment", "read", other, user="student1.whk@educore.localhost"))

	def test_staff_see_their_faculty_and_campus(self):
		self.assertEqual(self._visible("lecturer.comp.whk", "Student"), {"Ndapewa Amukoto"})
		self.assertEqual(self._visible("dean.fcm", "Student"), {"Anna Beukes", "Petrus Kooper"})
		self.assertEqual(self._visible("faculty-officer.fst.osh", "Program Enrollment"), {"Martha Shilongo"})
		self.assertEqual(
			self._visible("campus-director.osh", "Program Enrollment"), {"Martha Shilongo", "Tangeni Iiyambo"}
		)
