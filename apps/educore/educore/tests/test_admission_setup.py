"""The Registrar sets the university's admission rules (educore.api.v1.admission_setup)"""

import frappe
from frappe.tests import IntegrationTestCase

from educore.api.v1 import admission_setup as api

REGISTRAR = "registrar@educore.localhost"


class TestAdmissionSetup(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("User", REGISTRAR) or not frappe.db.exists("Admission Pathway", "School leaver"):
			self.skipTest("run the demo setup first")
		# put back whatever a test changes (Frappe rolls back once per class only)
		settings = frappe.get_single("Admission Settings")
		saved = {f: settings.get(f) for f in api.SETTINGS_FIELDS}
		scale = [{"level": r.level, "grade": r.grade, "points": r.points} for r in settings.points_scale]
		placeholder = settings.scale_is_placeholder

		def restore():
			doc = frappe.get_single("Admission Settings")
			doc.update(saved)
			doc.points_scale = []
			for row in scale:
				doc.append("points_scale", row)
			doc.scale_is_placeholder = placeholder
			doc.save(ignore_permissions=True)

		self.addCleanup(restore)
		frappe.set_user(REGISTRAR)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_only_the_registrar_or_ict(self):
		frappe.set_user("admissions-officer.whk@educore.localhost")
		self.assertRaises(frappe.PermissionError, api.setup)
		self.assertRaises(frappe.PermissionError, api.save_settings, {"max_choices": 2})
		frappe.set_user(REGISTRAR)
		data = api.setup()
		self.assertIn("School leaver", [p["name"] for p in data["pathways"]])
		self.assertTrue(any(p["code"] == "MBA" for p in data["programmes"]))

	def test_the_rules_are_saved_within_limits(self):
		data = api.save_settings({"max_choices": 2, "offer_response_days": 21, "approval_needs_fee": 0})
		self.assertEqual((data["settings"]["max_choices"], data["settings"]["offer_response_days"]), (2, 21))
		self.assertEqual(data["settings"]["approval_needs_fee"], 0)
		self.assertRaises(frappe.ValidationError, api.save_settings, {"max_choices": 0})
		self.assertRaises(frappe.ValidationError, api.save_settings, {"fee_namibian": -5})
		self.assertRaises(frappe.ValidationError, api.save_settings, {"home_country": "Atlantis"})

	def test_the_university_loads_its_own_points_scale(self):
		rows = [{"level": "NSSCO", "grade": g, "points": p} for g, p in (("A", 9), ("B", 7), ("C", 5))]
		api.save_points_scale(rows)
		settings = frappe.get_single("Admission Settings")
		self.assertEqual(len(settings.points_scale), 3)
		self.assertFalse(settings.scale_is_placeholder)
		self.assertRaises(frappe.ValidationError, api.save_points_scale, rows + [{"level": "NSSCO", "grade": "a", "points": 1}])

	def test_a_pathway_is_changed_and_a_new_one_added(self):
		data = api.save_pathway({"min_age": 25, "referees_required": 1}, name="Mature Age Entry")
		mature = next(p for p in data["pathways"] if p["name"] == "Mature Age Entry")
		self.assertEqual((mature["min_age"], mature["referees_required"]), (25, 1))

		data = api.save_pathway(
			{
				"pathway_name": "Foundation programme",
				"level": "Undergraduate",
				"evidence": "Work experience",
				"documents": [{"document_type": "Curriculum Vitae", "applies_to": "Everyone", "required": True}],
			}
		)
		rpl = next(p for p in data["pathways"] if p["name"] == "Foundation programme")
		self.assertEqual(rpl["documents"][0]["document_type"], "Curriculum Vitae")
		self.assertRaises(frappe.ValidationError, api.save_pathway, {"evidence": "Astrology"}, name="Postgraduate")

	def test_renaming_a_pathway_keeps_its_applications(self):
		frappe.set_user("Administrator")
		before = frappe.db.count("Student Applicant", {"educore_pathway": "School leaver"})
		frappe.set_user(REGISTRAR)
		data = api.save_pathway({"pathway_name": "Grade 12 school leaver"}, name="School leaver")
		self.assertIn("Grade 12 school leaver", [p["name"] for p in data["pathways"]])
		self.assertEqual(frappe.db.count("Student Applicant", {"educore_pathway": "Grade 12 school leaver"}), before)
		# only the capitals: the same record, renamed
		data = api.save_pathway({"pathway_name": "Grade 12 School Leaver"}, name="Grade 12 school leaver")
		names = [p["name"] for p in data["pathways"]]
		self.assertIn("Grade 12 School Leaver", names)
		self.assertNotIn("Grade 12 school leaver", names)
		self.assertEqual(frappe.db.count("Student Applicant", {"educore_pathway": "Grade 12 School Leaver"}), before)
		self.assertRaises(frappe.ValidationError, api.save_pathway, {"pathway_name": "Postgraduate"}, name="Grade 12 School Leaver")
		api.save_pathway({"pathway_name": "School leaver"}, name="Grade 12 School Leaver")  # the other tests use it

	def test_renaming_a_document_keeps_the_uploads_and_pathways(self):
		data = api.save_document_type({"document_name": "Curriculum vitae (CV)"}, name="Curriculum Vitae")
		self.assertIn("Curriculum vitae (CV)", [d["name"] for d in data["documents"]])
		mature = next(p for p in data["pathways"] if p["name"] == "Mature Age Entry")
		self.assertIn("Curriculum vitae (CV)", [d["document_type"] for d in mature["documents"]])
		api.save_document_type({"document_name": "Curriculum Vitae"}, name="Curriculum vitae (CV)")

	def test_a_new_document_can_be_asked_for(self):
		data = api.save_document_type({"document_name": "Police Clearance", "required_for": "Pathway only", "must_be_certified": 1})
		self.assertIn("Police Clearance", [d["name"] for d in data["documents"]])

	def test_a_programmes_entry_requirements(self):
		mba = frappe.db.get_value("Program", {"educore_programme_code": "MBA"})
		data = api.save_programme(mba, {"min_prior_average": 65, "min_prior_nqf": 8})
		row = next(p for p in data["programmes"] if p["code"] == "MBA")
		self.assertEqual((row["min_prior_nqf"], row["min_prior_average"]), (8, 65))

		bcs = frappe.db.get_value("Program", {"educore_programme_code": "BCS"})
		data = api.save_programme(bcs, {"min_points": 26, "subject_requirements": [{"subject": "Mathematics", "level": "NSSCO", "grade": "B"}]})
		row = next(p for p in data["programmes"] if p["code"] == "BCS")
		self.assertEqual(row["min_points"], 26)
		self.assertEqual(row["subject_requirements"], [{"subject": "Mathematics", "level": "NSSCO", "grade": "B"}])
		self.assertRaises(
			frappe.ValidationError,
			api.save_programme,
			bcs,
			{"subject_requirements": [{"subject": "Mathematics", "level": "NSSCO", "grade": "Z"}]},
		)


class TestFeeSettings(IntegrationTestCase):
	"""The fee account from ERPNext, and online and paper fees"""

	def setUp(self):
		if not frappe.db.exists("User", REGISTRAR):
			self.skipTest("run the demo setup first")
		frappe.set_user(REGISTRAR)
		saved = {f: frappe.db.get_single_value("Admission Settings", f) for f in api.SETTINGS_FIELDS}

		def restore():
			frappe.set_user("Administrator")
			doc = frappe.get_single("Admission Settings")
			doc.update(saved)
			doc.save(ignore_permissions=True)

		self.addCleanup(restore)

	def test_the_fee_account_comes_from_erpnext(self):
		data = api.setup()
		self.assertTrue(data["choices"]["bank_accounts"])
		self.assertRaises(frappe.ValidationError, api.save_settings, {"fee_bank_account": "No Such Account"})
		self.assertRaises(frappe.ValidationError, api.save_settings, {"fee_income_account": "No Such Account"})
		account = data["choices"]["bank_accounts"][0]
		saved = api.save_settings({"fee_bank_account": account["name"], "fee_paper_local": 220})["settings"]
		self.assertEqual((saved["fee_bank_account"], saved["fee_paper_local"]), (account["name"], 220))

