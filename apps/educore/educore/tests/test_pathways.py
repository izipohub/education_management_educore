"""Application pathways and the admissions rules each university sets (educore.admissions.pathways)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.access.demo_users import new_user
from educore.admissions import application as rules
from educore.api.v1 import apply

PASSWORD = "Campus-Demo-2026"
ADULT = {
	"date_of_birth": "1990-05-01",
	"gender": "Male",
	"nationality": "Namibian",
	"educore_national_id": "90050100456",
	"student_mobile_number": "+264812223344",
	"educore_kin_relationship": "Spouse or partner",
	"educore_kin_name": "Test Partner",
	"educore_kin_phone": "+264812223345",
	"educore_fee_payer": "Self",
}
BACHELOR = {
	"qualification": "Bachelor of Commerce",
	"institution": "Demo Institution",
	"country": "Namibia",
	"nqf_level": 7,
	"year_completed": 2015,
	"average": 65,
}
REFEREES = [
	{"full_name": "Referee One", "email": "referee.one@example.com"},
	{"full_name": "Referee Two", "email": "referee.two@example.com"},
]


class TestPathways(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Programme Offering", "MBA-WHK-PT"):
			self.skipTest("run educore.setup.demo.create_demo_university first")
		self._mute, frappe.flags.mute_emails = frappe.flags.mute_emails, True

	def tearDown(self):
		frappe.flags.mute_emails = self._mute
		frappe.set_user("Administrator")

	def _as_new_applicant(self):
		"""Each test its own applicant (Frappe rolls back once per class)"""
		email = "pathway." + self._testMethodName.removeprefix("test_")[:40].replace("_", ".").strip(".") + "@example.com"
		if not frappe.db.exists("User", email):
			frappe.flags.in_import = True
			try:
				new_user(email=email, first_name="Test", last_name="Pathway", password=PASSWORD, positions=["Applicant"])
			finally:
				frappe.flags.in_import = False
		frappe.set_user(email)

	def _save(self, **data):
		return apply.save({"intake": "2027 Intake", "personal": ADULT, **data})

	def _choice(self, data, offering):
		return next(c for c in data["choices"] if c["offering"] == offering)

	def _setting(self, doctype, name, field, value):
		"""Change a university setting for one test, put back afterwards"""
		frappe.set_user("Administrator")
		doc = frappe.get_doc(doctype, name or doctype)
		old = doc.get(field)
		doc.set(field, value)
		doc.save(ignore_permissions=True)
		self.addCleanup(lambda: frappe.get_doc(doctype, name or doctype).update({field: old}).save(ignore_permissions=True))

	# --- the routes on offer ---------------------------------------------------------------------------

	def test_the_open_routes_are_listed_in_the_universitys_order(self):
		listed = [p["name"] for p in apply.options()["pathways"]]
		self.assertEqual(listed[0], "School leaver")
		for name in ("Mature Age Entry", "Recognition of Prior Learning", "Credit transfer", "Re-admission", "Postgraduate"):
			self.assertIn(name, listed)

	def test_a_new_draft_starts_on_the_first_route(self):
		self._as_new_applicant()
		self.assertEqual(self._save()["pathway"], "School leaver")

	def test_choices_must_be_at_the_routes_level(self):
		self._as_new_applicant()
		self._save()
		with self.assertRaisesRegex(frappe.ValidationError, "postgraduate programme"):
			self._save(choices=["MBA-WHK-PT"])

	def test_changing_route_drops_choices_at_the_other_level(self):
		self._as_new_applicant()
		self.assertEqual(len(self._save(choices=["BBA-WHK-FT"])["choices"]), 1)
		data = self._save(pathway="Postgraduate")
		self.assertEqual(data["choices"], [])
		self.assertEqual(self._save(choices=["MBA-WHK-PT"])["choices"][0]["offering"], "MBA-WHK-PT")

	# --- postgraduate: prior NQF level and average -----------------------------------------------------

	def test_postgraduate_meets_on_nqf_level_and_average(self):
		self._as_new_applicant()
		data = self._save(pathway="Postgraduate", prior_qualifications=[BACHELOR], choices=["MBA-WHK-PT"])
		self.assertEqual(self._choice(data, "MBA-WHK-PT")["eligibility"], rules.MEETS)

	def test_postgraduate_below_the_average_or_level_does_not_meet(self):
		self._as_new_applicant()
		low = {**BACHELOR, "average": 55}
		data = self._save(pathway="Postgraduate", prior_qualifications=[low], choices=["MBA-WHK-PT"])
		choice = self._choice(data, "MBA-WHK-PT")
		self.assertEqual(choice["eligibility"], rules.FAILS)
		self.assertEqual(choice["eligibility_note"], "Average 55%, 60% needed")

		diploma = {**BACHELOR, "qualification": "Diploma", "nqf_level": 6}
		data = self._save(prior_qualifications=[diploma])
		self.assertIn("NQF level 6, 7 needed", self._choice(data, "MBA-WHK-PT")["eligibility_note"])

	def test_a_foreign_or_incomplete_qualification_needs_review(self):
		self._as_new_applicant()
		foreign = {**BACHELOR, "country": "South Africa"}
		data = self._save(pathway="Postgraduate", prior_qualifications=[foreign], choices=["MBA-WHK-PT"])
		self.assertEqual(self._choice(data, "MBA-WHK-PT")["eligibility"], rules.REVIEW)

		studying = {**BACHELOR, "year_completed": None}
		data = self._save(prior_qualifications=[studying])
		self.assertEqual(self._choice(data, "MBA-WHK-PT")["eligibility"], rules.REVIEW)
		self.assertIn("A completed qualification (with the year completed)", data["missing"])

	def test_the_programmes_thresholds_are_the_universitys(self):
		mba = frappe.db.get_value("Programme Offering", "MBA-WHK-PT", "program")
		self._setting("Program", mba, "educore_min_prior_average", 70)
		self._as_new_applicant()
		data = self._save(pathway="Postgraduate", prior_qualifications=[BACHELOR], choices=["MBA-WHK-PT"])
		self.assertIn("70% needed", self._choice(data, "MBA-WHK-PT")["eligibility_note"])

	def test_postgraduate_asks_for_referees_and_its_documents(self):
		self._as_new_applicant()
		data = self._save(pathway="Postgraduate", prior_qualifications=[BACHELOR], choices=["MBA-WHK-PT"])
		self.assertIn("Details of 2 referees", data["missing"])
		required = {d["document_type"] for d in data["documents"] if d["required"]}
		self.assertTrue({"Degree or Diploma Certificate", "Academic Record", "Curriculum Vitae"} <= required)
		self.assertNotIn("NSSC Statement of Results or Certificate", required)
		self.assertNotIn("Your school results", data["missing"])

		data = self._save(referees=REFEREES)
		self.assertNotIn("Details of 2 referees", data["missing"])

	# --- mature age entry ------------------------------------------------------------------------------

	def test_mature_age_entry_needs_the_minimum_age(self):
		self._as_new_applicant()
		young = {**ADULT, "date_of_birth": "2006-06-01"}  # 20 on 1 January 2027
		data = apply.save({"intake": "2027 Intake", "personal": young, "pathway": "Mature Age Entry", "choices": ["BBA-WHK-FT"]})
		self.assertTrue(any("aged 25 or older" in gap for gap in data["missing"]))
		self.assertEqual(data["choices"][0]["eligibility"], rules.FAILS)

	def test_mature_age_entry_is_decided_by_a_person(self):
		self._as_new_applicant()
		data = self._save(
			pathway="Mature Age Entry",
			employment=[{"employer": "Demo Co", "position": "Supervisor", "from_date": "2015-01-01", "to_date": "2024-12-31"}],
			choices=["BBA-WHK-FT"],
		)
		self.assertEqual(data["choices"][0]["eligibility"], rules.REVIEW)
		self.assertEqual(data["work_years"], 10.0)
		self.assertFalse(any("aged" in gap for gap in data["missing"]))

	def test_mature_age_entry_needs_the_years_of_work(self):
		self._as_new_applicant()
		data = self._save(
			pathway="Mature Age Entry",
			employment=[{"employer": "Demo Co", "position": "Clerk", "from_date": "2023-01-01", "to_date": "2024-12-31"}],
			choices=["BBA-WHK-FT"],
		)
		self.assertEqual(data["choices"][0]["eligibility"], rules.FAILS)
		self.assertIn("requires 5", data["choices"][0]["eligibility_note"])

	def test_the_minimum_age_is_the_universitys(self):
		self._setting("Admission Pathway", "Mature Age Entry", "min_age", 40)
		self._as_new_applicant()
		data = self._save(pathway="Mature Age Entry", choices=["BBA-WHK-FT"])  # 36 on 1 January 2027
		self.assertTrue(any("aged 40 or older" in gap for gap in data["missing"]))

	# --- resumption and advanced standing --------------------------------------------------------------

	def test_resumption_finds_the_previous_student(self):
		student = frappe.get_all("Student", fields=["name", "student_name"], limit=1)[0]
		self._as_new_applicant()
		data = self._save(pathway="Re-admission", choices=["BBA-WHK-FT"])
		self.assertIn("Your previous student number", data["missing"])
		data = self._save(previous_student_number=student.name)
		self.assertEqual(data["choices"][0]["eligibility"], rules.REVIEW)
		self.assertIn(student.student_name, data["choices"][0]["eligibility_note"])

	def test_advanced_standing_needs_school_and_later_studies(self):
		self._as_new_applicant()
		data = self._save(pathway="Credit transfer", choices=["BBA-WHK-FT"])
		for gap in ("Your studies after school", "Your school results"):
			self.assertIn(gap, data["missing"])
		self.assertIn("Academic Record", {d["document_type"] for d in data["documents"] if d["required"]})

	# --- international is a status, on any route -------------------------------------------------------

	def test_international_changes_the_documents_and_fee_not_the_route(self):
		self._as_new_applicant()
		data = self._save(international=True)
		self.assertEqual(data["pathway"], "School leaver")
		required = {d["document_type"] for d in data["documents"] if d["required"]}
		self.assertIn("Foreign School Leaving Certificate", required)
		self.assertIn("Study Permit or Visa", required)
		self.assertNotIn("NSSC Statement of Results or Certificate", required)
		self.assertNotIn("Your school results", data["missing"])
		self.assertEqual(data["fee"]["amount"], rules.settings().fee_international)

	# --- what else the university decides --------------------------------------------------------------

	def test_the_number_of_choices_is_the_universitys(self):
		self._setting("Admission Settings", None, "max_choices", 1)
		self._as_new_applicant()
		with self.assertRaisesRegex(frappe.ValidationError, "at most 1"):
			self._save(choices=["BBA-WHK-FT", "BACC-WHK-FT"])
		self.assertEqual(apply.options()["max_choices"], 1)

	def test_approval_rules_can_be_switched_off(self):
		frappe.set_user("Administrator")
		name = frappe.db.get_value("Student Applicant", {"educore_applicant_user": "online.applicant@educore.localhost"})
		if not name:
			self.skipTest("run educore.setup.demo_students.create first")
		doc = frappe.get_doc("Student Applicant", name)
		self.assertTrue(rules.decision_blockers(doc))
		self._setting("Admission Settings", None, "approval_needs_fee", 0)
		self._setting("Admission Settings", None, "approval_needs_verified_documents", 0)
		self.assertEqual(rules.decision_blockers(doc), [])
