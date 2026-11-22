"""Offers on online applications, the applicant's response, lapsing, and the emails (educore.admissions.offers,
educore.admissions.notify)"""

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from educore.admissions import notify, offers
from educore.api.v1 import admissions, apply, registry
from educore.tests import test_apply


class TestOffers(IntegrationTestCase):
	# the applicant helpers of the online-application tests
	_applicant = test_apply.TestOnlineApplication._applicant
	_draft = test_apply.TestOnlineApplication._draft
	_upload = test_apply.TestOnlineApplication._upload
	_complete = test_apply.TestOnlineApplication._complete

	def setUp(self):
		if not frappe.db.exists("Student Admission", "2027 Intake"):
			self.skipTest("run educore.setup.demo.create_demo_university first")
		self._mute, frappe.flags.mute_emails = frappe.flags.mute_emails, True
		self.sent = []
		patcher = patch.object(notify, "_deliver", lambda recipient, subject, body, doc: self.sent.append((recipient, subject, body)))
		patcher.start()
		self.addCleanup(patcher.stop)

	def tearDown(self):
		frappe.flags.mute_emails = self._mute
		frappe.set_user("Administrator")

	def _login(self):
		return "offer." + self._testMethodName.removeprefix("test_")[:40].replace("_", ".").strip(".")

	def _setting(self, field, value):
		settings = frappe.get_single("Admission Settings")
		old = settings.get(field)
		settings.set(field, value)
		settings.save(ignore_permissions=True)
		self.addCleanup(lambda: frappe.get_single("Admission Settings").update({field: old}).save(ignore_permissions=True))

	def _submitted(self) -> str:
		self._complete()
		name = apply.submit(declaration=True)["name"]
		frappe.set_user("Administrator")
		return name

	def _ready(self) -> str:
		"""Submitted online, documents verified and fee settled: ready for a decision (session: Administrator)"""
		name = self._submitted()
		doc = frappe.get_doc("Student Applicant", name)
		for row in doc.educore_documents:
			row.status = "Verified"
		doc.save(ignore_permissions=True)
		admissions.waive_fee(name, "Test")
		return name

	def _offered(self, conditions: str | None = None) -> str:
		"""Submitted online, checked by admissions and approved; the session is the applicant's again"""
		name = self._ready()
		applicant_user = frappe.db.get_value("Student Applicant", name, "educore_applicant_user")
		admissions.decide(name, "Approve", conditions=conditions)
		frappe.set_user(applicant_user)
		return name

	def _events(self):
		return [subject for _recipient, subject, _body in self.sent]

	# --- the offer -------------------------------------------------------------------------------------

	def test_approving_makes_an_offer_with_the_universitys_deadline(self):
		self._setting("offer_response_days", 10)
		name = self._offered(conditions="Final results by 31 January")
		offer = apply.my_application()["offer"]
		self.assertEqual(offer["status"], offers.AWAITING)
		self.assertEqual(getdate(offer["deadline"]), getdate(add_days(nowdate(), 10)))
		self.assertEqual(offer["conditions"], "Final results by 31 January")
		self.assertEqual(offer["programme"], "Bachelor of Computer Science")
		self.assertTrue(offer["annual_fees"])
		self.assertIn("Offer of a place: Bachelor of Computer Science", self._events())
		self.assertIn(name, self._events()[0])  # the acknowledgement on submission came first

	def test_accepting_the_offer_allows_enrolment(self):
		name = self._offered()
		self.assertTrue(offers.needs_acceptance(frappe.get_doc("Student Applicant", name)))
		data = apply.accept_offer()
		self.assertEqual((data["status"], data["offer"]["status"]), ("Approved", offers.ACCEPTED))
		self.assertFalse(offers.needs_acceptance(frappe.get_doc("Student Applicant", name)))
		self.assertRaises(frappe.ValidationError, apply.accept_offer)  # answered once

	def test_enrolment_waits_for_acceptance(self):
		name = self._offered()
		frappe.set_user("registrar@educore.localhost")
		with self.assertRaisesRegex(frappe.ValidationError, "has not accepted the offer"):
			registry.enrol(name)
		waiting = {r["name"]: r for r in registry.enrolments(academic_year="2027")["waiting"]}
		self.assertTrue(waiting[name]["needs_acceptance"])

	def test_the_university_can_enrol_without_acceptance(self):
		self._setting("enrolment_needs_acceptance", 0)
		name = self._offered()
		self.assertFalse(offers.needs_acceptance(frappe.get_doc("Student Applicant", name)))

	def test_declining_frees_the_place(self):
		name = self._offered()
		offering = frappe.db.get_value("Student Applicant", name, "educore_programme_offering")
		taken = lambda: frappe.db.count(  # noqa: E731
			"Student Applicant", {"educore_programme_offering": offering, "application_status": ("in", ("Approved", "Admitted"))}
		)
		before = taken()
		data = apply.decline_offer("Accepted elsewhere")
		self.assertEqual((data["status"], data["offer"]["status"]), ("Declined", offers.DECLINED))
		self.assertEqual(taken(), before - 1)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Student Applicant", name, "educore_offer_decline_reason"), "Accepted elsewhere")
		self.assertIn("Offer declined: Bachelor of Computer Science", self._events())

	def test_only_the_registrar_reconsiders_a_declined_offer(self):
		name = self._offered()
		apply.decline_offer()
		frappe.set_user("admissions-officer.osh@educore.localhost")
		self.assertRaises(frappe.ValidationError, admissions.decide, name, "Reconsider")
		frappe.set_user("registrar@educore.localhost")
		self.assertEqual(admissions.decide(name, "Reconsider")["status"], "Applied")
		frappe.set_user("Administrator")
		self.assertIsNone(frappe.db.get_value("Student Applicant", name, "educore_offer_status"))

	# --- offering another choice --------------------------------------------------------------------

	def test_admissions_can_offer_a_later_choice(self):
		# choices: BCS-OSH-FT, BNS-WHK-FT, DIT-OSH-FT
		name = self._ready()
		frappe.set_user("admissions-officer.osh@educore.localhost")
		row = admissions.decide(name, "Approve", offering="DIT-OSH-FT")
		self.assertEqual((row["status"], row["offering"]), ("Approved", "DIT-OSH-FT"))
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("Student Applicant", name, "program"), "Diploma in Information Technology")
		self.assertIn("Offer of a place: Diploma in Information Technology", self._events())

	def test_a_choice_at_another_campus_is_offered_by_its_own_officers(self):
		name = self._ready()
		frappe.set_user("admissions-officer.osh@educore.localhost")
		self.assertRaises(frappe.PermissionError, admissions.decide, name, "Approve", offering="BNS-WHK-FT")
		self.assertRaises(frappe.ValidationError, admissions.decide, name, "Approve", offering="BACC-KMP-PT")  # not a choice
		frappe.set_user("registrar@educore.localhost")
		self.assertEqual(admissions.decide(name, "Approve", offering="BNS-WHK-FT")["offering"], "BNS-WHK-FT")

	# --- the deadline ----------------------------------------------------------------------------------

	def test_a_reminder_goes_once_before_the_deadline(self):
		self._setting("offer_reminder_days", 3)
		name = self._offered()
		frappe.set_user("Administrator")
		frappe.db.set_value("Student Applicant", name, "educore_offer_deadline", add_days(nowdate(), 2))
		self.sent.clear()
		offers.remind()
		offers.remind()
		self.assertEqual(len([s for s in self._events() if s.startswith("Reminder")]), 1)

	def test_an_unanswered_offer_lapses_after_the_deadline(self):
		name = self._offered()
		frappe.set_user("Administrator")
		frappe.db.set_value("Student Applicant", name, "educore_offer_deadline", add_days(nowdate(), -1))
		offers.lapse()
		status, response = frappe.db.get_value("Student Applicant", name, ["application_status", "educore_offer_status"])
		self.assertEqual((status, response), ("Lapsed", offers.LAPSED))
		self.assertIn("Offer lapsed: Bachelor of Computer Science", self._events())

	def test_admissions_can_extend_the_deadline(self):
		name = self._offered()
		frappe.set_user("admissions-officer.osh@educore.localhost")
		# the second choice is at Windhoek: the application still belongs to its first choice's campus
		self.assertTrue(frappe.has_permission("Student Applicant", "write", frappe.get_doc("Student Applicant", name)))
		later = add_days(nowdate(), 30)
		self.assertEqual(getdate(admissions.extend_offer(name, later)["offer"]["deadline"]), getdate(later))
		self.assertRaises(frappe.ValidationError, admissions.extend_offer, name, add_days(nowdate(), -1))

	# --- emails ----------------------------------------------------------------------------------------

	def test_a_rejected_document_is_emailed_with_the_reason(self):
		name = self._submitted()
		admissions.verify_document(name, "Birth Certificate", "Rejected", "The certification stamp is not legible")
		recipient, subject, body = self.sent[-1]
		self.assertTrue(subject.startswith("Action required: Birth Certificate"))
		self.assertIn("The certification stamp is not legible", body)

	def test_no_emails_when_the_university_turns_them_off(self):
		self._setting("notify_applicants", 0)
		self._submitted()
		self.assertEqual(self.sent, [])

	def test_a_paper_application_gets_no_offer_or_email(self):
		frappe.set_user("Administrator")
		name = frappe.db.get_value("Student Applicant", {"application_status": "Approved", "educore_applicant_user": ("is", "not set")})
		if not name:
			self.skipTest("run educore.setup.demo_students.create first")
		self.assertIsNone(frappe.db.get_value("Student Applicant", name, "educore_offer_status"))
		self.assertFalse(offers.needs_acceptance(frappe.get_doc("Student Applicant", name)))
