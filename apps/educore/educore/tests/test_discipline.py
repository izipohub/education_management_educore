"""Disciplinary cases (educore.academics.discipline, educore.api.v1.discipline): reported by staff who know the
student, handled by Student Affairs of the student's campus, minor ones decided by Student Affairs, serious ones after
a hearing; sanctions act (registration stopped, fines invoiced); the student appeals; the Registrar decides"""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from educore.academics import discipline as d
from educore.academics import history
from educore.api.v1 import discipline as api

STUDENT = "student1.kmp@educore.localhost"
LECTURER_KMP = "lecturer.accf.kmp@educore.localhost"  # teaches the student
LECTURER_WHK = "lecturer.comp.whk@educore.localhost"  # does not
AFFAIRS_KMP = "student-affairs-officer.kmp@educore.localhost"
AFFAIRS_OSH = "student-affairs-officer.osh@educore.localhost"
REGISTRAR = "registrar@educore.localhost"


class TestDiscipline(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", AFFAIRS_KMP) or not frappe.db.exists("User", STUDENT):
			self.skipTest("run the demo setup first")
		frappe.db.savepoint("discipline_test")
		self.student = frappe.db.get_value("Student", {"user": STUDENT})

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="discipline_test")

	def _report(self) -> str:
		frappe.set_user(LECTURER_KMP)
		return api.report(self.student, nowdate(), "Copied answers from a phone during the Test 2 of FIN2511")["name"]

	def test_only_staff_who_know_the_student_report_and_only_their_campus_sees_it(self):
		frappe.set_user(LECTURER_WHK)
		self.assertRaises(frappe.PermissionError, api.report, self.student, nowdate(), "Something")
		frappe.set_user(LECTURER_KMP)
		self.assertRaises(frappe.ValidationError, api.report, self.student, add_days(nowdate(), 1), "Tomorrow")
		name = self._report()
		self.assertRaises(frappe.PermissionError, api.case, name)  # the reporter does not follow the case
		frappe.set_user(AFFAIRS_OSH)
		self.assertNotIn(name, [r["name"] for r in api.cases()["rows"]])
		self.assertRaises(frappe.PermissionError, api.case, name)
		frappe.set_user(AFFAIRS_KMP)
		self.assertEqual(api.case(name)["status"], d.REPORTED)
		# the student does not see a case under investigation
		frappe.set_user(STUDENT)
		self.assertEqual(api.mine(), [])

	def test_a_minor_case_decided_by_student_affairs_and_overturned_on_appeal(self):
		name = self._report()
		frappe.set_user(AFFAIRS_KMP)
		api.investigate(name)
		# a suspension is the committee's, after a hearing
		self.assertRaises(frappe.ValidationError, api.decide, name, d.RESPONSIBLE, "Copying", d.SUSPENSION, 0, nowdate(), add_days(nowdate(), 30))
		case = api.decide(name, d.RESPONSIBLE, "Seen by the invigilator; admitted it", d.WRITTEN_WARNING)
		self.assertEqual(case["status"], d.DECIDED)
		self.assertEqual(case["appeal_until"], str(add_days(nowdate(), d.appeal_days())))

		frappe.set_user(STUDENT)
		mine = api.mine()[0]
		self.assertTrue(mine["can_appeal"])
		self.assertNotIn("incident", mine)  # the report and investigation stay with Student Affairs
		self.assertRaises(frappe.ValidationError, api.appeal, name, " ")
		api.appeal(name, "The phone was a calculator app the invigilator allowed")

		frappe.set_user(AFFAIRS_KMP)
		self.assertRaises(frappe.PermissionError, api.decide_appeal, name, d.OVERTURNED, "Allowed calculator")
		frappe.set_user(REGISTRAR)
		case = api.decide_appeal(name, d.OVERTURNED, "The invigilator confirms the calculator was allowed")
		self.assertEqual((case["status"], case["finding"], case["sanction"]), (d.CLOSED, d.NOT_RESPONSIBLE, None))
		events = [e["event"] for e in history.of_student(self.student)]
		self.assertIn("Disciplinary appeal overturned", events)

	def test_a_serious_case_heard_suspends_the_student_from_registering(self):
		name = self._report()
		frappe.set_user(AFFAIRS_KMP)
		api.investigate(name)
		self.assertRaises(frappe.ValidationError, api.schedule_hearing, name, "Cheating", str(add_days(nowdate(), -1)) + " 10:00:00", "Boardroom")
		api.schedule_hearing(name, "Cheating in a test (rule 4.2)", str(add_days(nowdate(), 3)) + " 10:00:00", "Boardroom, Block A", "Dean of Students, two lecturers, SRC")
		frappe.set_user(STUDENT)
		self.assertEqual(api.mine()[0]["status"], d.HEARING)  # told of the hearing
		frappe.set_user(AFFAIRS_KMP)
		self.assertRaises(frappe.ValidationError, api.decide, name, d.RESPONSIBLE, "Proven", d.SUSPENSION, 0, nowdate(), add_days(nowdate(), -5))
		api.decide(name, d.RESPONSIBLE, "Proven at the hearing", d.SUSPENSION, 0, nowdate(), str(add_days(nowdate(), 180)), "The student attended and admitted it")
		self.assertTrue(any("Suspended until" in b for b in d.barring(self.student)))
		from educore.registration import rules

		period = rules.current_period()
		if period:
			offering = frappe.db.get_value("Program Enrollment", {"student": self.student, "docstatus": 1}, "educore_programme_offering")
			self.assertTrue(any("Suspended until" in b for b in rules.blockers(self.student, offering, period)))
		self.assertIn("Disciplinary decision", [e["event"] for e in history.of_student(self.student)])

	def test_a_fine_is_invoiced_and_cancelled_when_the_appeal_changes_it(self):
		name = self._report()
		frappe.set_user(AFFAIRS_KMP)
		api.investigate(name)
		api.decide(name, d.RESPONSIBLE, "Damaged a lab computer", d.FINE, 800)
		invoice = frappe.db.get_value("Disciplinary Case", name, "fine_invoice")
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice, "grand_total"), 800)
		frappe.set_user(STUDENT)
		api.appeal(name, "The computer was already broken")
		frappe.set_user(REGISTRAR)
		case = api.decide_appeal(name, d.CHANGED, "Partly broken already: a warning", d.WARNING)
		self.assertEqual(frappe.db.get_value("Sales Invoice", invoice, "docstatus"), 2)
		self.assertEqual(case["sanction"], d.WARNING)

	def test_a_case_with_nothing_to_answer_is_dismissed_quietly(self):
		name = self._report()
		frappe.set_user(AFFAIRS_KMP)
		self.assertRaises(frappe.ValidationError, api.dismiss, name, "")
		self.assertEqual(api.dismiss(name, "Another student; the lecturer confirms")["status"], d.DISMISSED)
		frappe.set_user(STUDENT)
		self.assertEqual(api.mine(), [])

	def test_the_registrar_sets_the_days_to_appeal(self):
		frappe.set_user(AFFAIRS_KMP)
		self.assertRaises(frappe.PermissionError, api.save_rules, 14)
		frappe.set_user(REGISTRAR)
		self.assertEqual(api.save_rules(14)["appeal_days"], 14)
		self.assertRaises(frappe.ValidationError, api.save_rules, 0)
